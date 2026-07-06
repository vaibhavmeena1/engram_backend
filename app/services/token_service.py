"""Backend-owned web-session JWT issuing and verification."""

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.schemas.enums import AuthClientType
from app.services.config_service import EngramConfigService
from app.services.vortex_http import internal_server_error, unauthorized


@dataclass(frozen=True)
class IssuedWebSessionToken:
    token: str
    jwt_id: str
    expires_at: datetime


@dataclass(frozen=True)
class VerifiedWebSessionToken:
    user_id: UUID
    org_id: UUID
    client_type: AuthClientType
    jwt_id: str
    expires_at: datetime


class TokenService:
    """Owns compact HS256 JWT handling without involving PAT generation/storage."""

    SUPPORTED_ALGORITHM = "HS256"

    @classmethod
    def issue_web_session_token(
        cls,
        *,
        user_id: UUID,
        org_id: UUID,
        client_type: AuthClientType = AuthClientType.WEB,
    ) -> IssuedWebSessionToken:
        settings = EngramConfigService.auth()
        cls._ensure_supported_algorithm(settings.jwt_signing_algorithm)
        signing_key = cls._signing_key()

        issued_at = datetime.now(UTC)
        expires_at = issued_at + timedelta(seconds=settings.web_session_ttl_seconds)
        jwt_id = str(uuid4())
        claims = {
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "sub": str(user_id),
            "org_id": str(org_id),
            "client_type": client_type.value,
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": jwt_id,
        }
        header = {"alg": cls.SUPPORTED_ALGORITHM, "typ": "JWT"}
        signing_input = f"{cls._json_part(header)}.{cls._json_part(claims)}"
        signature = cls._sign(signing_input.encode(), signing_key)
        return IssuedWebSessionToken(
            token=f"{signing_input}.{signature}",
            jwt_id=jwt_id,
            expires_at=expires_at,
        )

    @classmethod
    def verify_web_session_token(cls, token: str) -> VerifiedWebSessionToken:
        settings = EngramConfigService.auth()
        cls._ensure_supported_algorithm(settings.jwt_signing_algorithm)
        signing_key = cls._signing_key()

        parts = token.split(".")
        if len(parts) != 3:
            raise unauthorized("Invalid session token")

        signing_input = f"{parts[0]}.{parts[1]}"
        expected_signature = cls._sign(signing_input.encode(), signing_key)
        if not hmac.compare_digest(expected_signature, parts[2]):
            raise unauthorized("Invalid session token")

        header = cls._decode_json_part(parts[0])
        claims = cls._decode_json_part(parts[1])
        if header.get("alg") != cls.SUPPORTED_ALGORITHM:
            raise unauthorized("Invalid session token")
        if (
            claims.get("iss") != settings.jwt_issuer
            or claims.get("aud") != settings.jwt_audience
        ):
            raise unauthorized("Invalid session token")

        try:
            expires_at = datetime.fromtimestamp(int(claims["exp"]), UTC)
            user_id = UUID(str(claims["sub"]))
            org_id = UUID(str(claims["org_id"]))
            jwt_id = str(claims["jti"])
            client_type = AuthClientType(
                str(claims.get("client_type") or AuthClientType.WEB.value)
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise unauthorized("Invalid session token") from exc

        if expires_at <= datetime.now(UTC):
            raise unauthorized("Session token has expired")

        return VerifiedWebSessionToken(
            user_id=user_id,
            org_id=org_id,
            client_type=client_type,
            jwt_id=jwt_id,
            expires_at=expires_at,
        )

    @classmethod
    def hash_jwt_id(cls, jwt_id: str) -> str:
        return hmac.new(cls._signing_key(), jwt_id.encode(), hashlib.sha256).hexdigest()

    @classmethod
    def _json_part(cls, payload: dict) -> str:
        return cls._base64_url_encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        )

    @classmethod
    def _decode_json_part(cls, payload: str) -> dict:
        try:
            decoded_payload = cls._base64_url_decode(payload)
            value = json.loads(decoded_payload.decode())
        except (ValueError, json.JSONDecodeError) as exc:
            raise unauthorized("Invalid session token") from exc
        if not isinstance(value, dict):
            raise unauthorized("Invalid session token")
        return value

    @classmethod
    def _sign(cls, signing_input: bytes, signing_key: bytes) -> str:
        signature = hmac.new(signing_key, signing_input, hashlib.sha256).digest()
        return cls._base64_url_encode(signature)

    @classmethod
    def _base64_url_encode(cls, value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

    @classmethod
    def _base64_url_decode(cls, value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(f"{value}{padding}".encode())

    @classmethod
    def _signing_key(cls) -> bytes:
        signing_key = EngramConfigService.auth().jwt_signing_key.strip()
        if not signing_key:
            raise internal_server_error("JWT signing key is not configured")
        return signing_key.encode()

    @classmethod
    def _ensure_supported_algorithm(cls, algorithm: str) -> None:
        if algorithm != cls.SUPPORTED_ALGORITHM:
            raise internal_server_error("Only HS256 JWT signing is supported")
