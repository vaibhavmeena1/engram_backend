"""Basic secret and sensitivity guardrails for memory content."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SafetyCheckResult:
    """Structured result for lightweight content safety checks."""

    contains_possible_secret: bool
    reasons: list[str] = field(default_factory=list)
    matched_patterns: list[str] = field(default_factory=list)

    def to_metadata(self) -> dict:
        """Return safe, non-secret metadata that reviewers can inspect."""
        return {
            "contains_possible_secret": self.contains_possible_secret,
            "reasons": self.reasons,
            "matched_patterns": self.matched_patterns,
        }


class SafetyService:
    """Detects obvious secrets before content becomes approved memory."""

    PRIVATE_KEY_PATTERN = re.compile(
        r"-----BEGIN\s+(?:RSA\s+|DSA\s+|EC\s+|OPENSSH\s+|PGP\s+)?PRIVATE\s+KEY-----",
        re.IGNORECASE,
    )
    JWT_PATTERN = re.compile(
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
    )
    ENV_SECRET_ASSIGNMENT_PATTERN = re.compile(
        r"(?im)^\s*(?:export\s+)?[A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|PASS|API[_-]?KEY|PRIVATE[_-]?KEY|ACCESS[_-]?KEY)[A-Z0-9_]*\s*=\s*['\"]?[^'\"\s#]{8,}",
    )
    SECRET_FIELD_PATTERN = re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?key|secret|token|password|passwd|pwd|private[_-]?key)\b\s*[:=]\s*['\"]?[A-Za-z0-9_./+=:-]{8,}",
    )
    API_KEY_VALUE_PATTERN = re.compile(
        r"(?i)\b(?:sk|pk|api|key|token|secret)[_-]?(?:live|test|prod)?[_-][A-Za-z0-9]{20,}\b",
    )
    HIGH_ENTROPY_CANDIDATE_PATTERN = re.compile(r"\b[A-Za-z0-9+/=_-]{32,}\b")

    MIN_HIGH_ENTROPY_LENGTH = 32
    MIN_HIGH_ENTROPY_SCORE = 4.0

    @classmethod
    def analyze_memory_payload(
        cls,
        content: str,
        summary: str | None = None,
        metadata: dict | None = None,
        rationale: str | None = None,
    ) -> SafetyCheckResult:
        """Analyze memory content, rationale, and metadata for obvious secret-like values."""
        payload_parts = [content or "", summary or "", rationale or ""]
        if metadata:
            payload_parts.append(
                json.dumps(metadata, ensure_ascii=False, sort_keys=True, default=str)
            )
        return cls.analyze_text("\n".join(payload_parts))

    @classmethod
    def analyze_text(cls, text: str) -> SafetyCheckResult:
        """Run deterministic, dependency-free secret heuristics over text."""
        reasons: list[str] = []
        matched_patterns: list[str] = []

        cls._record_regex_match(
            text,
            cls.PRIVATE_KEY_PATTERN,
            "private_key_block",
            "Contains a private-key block marker",
            reasons,
            matched_patterns,
        )
        cls._record_regex_match(
            text,
            cls.JWT_PATTERN,
            "jwt_token",
            "Contains a JWT-looking token",
            reasons,
            matched_patterns,
        )
        cls._record_regex_match(
            text,
            cls.ENV_SECRET_ASSIGNMENT_PATTERN,
            "env_secret_assignment",
            "Contains a .env-style secret assignment",
            reasons,
            matched_patterns,
        )
        cls._record_regex_match(
            text,
            cls.SECRET_FIELD_PATTERN,
            "secret_field_value",
            "Contains a password/secret/token field with a value",
            reasons,
            matched_patterns,
        )
        cls._record_regex_match(
            text,
            cls.API_KEY_VALUE_PATTERN,
            "api_key_value",
            "Contains an API-key-looking value",
            reasons,
            matched_patterns,
        )

        if cls._contains_high_entropy_string(text):
            reasons.append("Contains a long high-entropy string")
            matched_patterns.append("high_entropy_string")

        return SafetyCheckResult(
            contains_possible_secret=bool(reasons),
            reasons=cls._dedupe_preserving_order(reasons),
            matched_patterns=cls._dedupe_preserving_order(matched_patterns),
        )

    @classmethod
    def _record_regex_match(
        cls,
        text: str,
        pattern: re.Pattern[str],
        pattern_name: str,
        reason: str,
        reasons: list[str],
        matched_patterns: list[str],
    ) -> None:
        if pattern.search(text):
            reasons.append(reason)
            matched_patterns.append(pattern_name)

    @classmethod
    def _contains_high_entropy_string(cls, text: str) -> bool:
        for candidate_match in cls.HIGH_ENTROPY_CANDIDATE_PATTERN.finditer(text):
            candidate = candidate_match.group(0).strip("'\"")
            if len(candidate) < cls.MIN_HIGH_ENTROPY_LENGTH:
                continue
            if not cls._has_mixed_secret_like_charset(candidate):
                continue
            if cls._shannon_entropy(candidate) >= cls.MIN_HIGH_ENTROPY_SCORE:
                return True
        return False

    @classmethod
    def _has_mixed_secret_like_charset(cls, value: str) -> bool:
        character_groups = 0
        character_groups += any(character.islower() for character in value)
        character_groups += any(character.isupper() for character in value)
        character_groups += any(character.isdigit() for character in value)
        character_groups += any(character in "+/=_-" for character in value)
        return character_groups >= 3

    @classmethod
    def _shannon_entropy(cls, value: str) -> float:
        if not value:
            return 0.0
        entropy = 0.0
        value_length = len(value)
        for character in set(value):
            probability = value.count(character) / value_length
            entropy -= probability * math.log2(probability)
        return entropy

    @classmethod
    def _dedupe_preserving_order(cls, values: list[str]) -> list[str]:
        deduped_values = []
        seen_values = set()
        for value in values:
            if value not in seen_values:
                seen_values.add(value)
                deduped_values.append(value)
        return deduped_values
