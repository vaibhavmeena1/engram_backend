"""Repository identity normalization and persistence."""

from urllib.parse import urlparse, urlunparse
from uuid import UUID

from app.models.repository import Repository
from app.schemas.repository import (
    RepositoryContext,
    RepositoryIdentity,
    RepositoryRemoteInput,
)
from app.services.vortex_http import bad_request


class RepositoryResolver:
    """Resolves repository identity from Git metadata without relying on local paths."""

    BITBUCKET_HOST = "bitbucket.org"
    BITBUCKET_PROVIDER = "bitbucket"

    @classmethod
    async def resolve_repository_context(
        cls,
        org_id: UUID,
        repository_input: RepositoryRemoteInput,
    ) -> RepositoryContext | None:
        explicit_repository = await cls._get_explicit_repository(
            repository_input.explicit_repo_id, org_id
        )
        identity = cls.normalize_origin_url(repository_input.origin_url)

        if explicit_repository and identity:
            if explicit_repository.repository_key != identity.repository_key:
                raise bad_request("Explicit repository id does not match origin URL")
            return cls._context_from_model(
                repository=explicit_repository,
                branch=repository_input.branch,
                commit_sha=repository_input.commit_sha,
                metadata={"source": "explicit_repo_id_with_origin_url"},
            )

        if explicit_repository:
            return cls._context_from_model(
                repository=explicit_repository,
                branch=repository_input.branch,
                commit_sha=repository_input.commit_sha,
                metadata={"source": "explicit_repo_id"},
            )

        if identity:
            repository = await cls.upsert_repository(org_id, identity)
            return cls._context_from_model(
                repository=repository,
                branch=repository_input.branch,
                commit_sha=repository_input.commit_sha,
                metadata={"source": identity.resolver_source},
            )

        fallback_identity = cls.basename_fallback(repository_input.git_root_basename)
        if fallback_identity:
            repository = await cls.upsert_repository(org_id, fallback_identity)
            return cls._context_from_model(
                repository=repository,
                branch=repository_input.branch,
                commit_sha=repository_input.commit_sha,
                metadata={
                    "source": fallback_identity.resolver_source,
                    "low_confidence": True,
                },
            )

        return None

    @classmethod
    def normalize_origin_url(cls, origin_url: str | None) -> RepositoryIdentity | None:
        normalized_url = (origin_url or "").strip()
        if not normalized_url:
            return None

        parsed_url = cls._parse_git_remote(normalized_url)
        if not parsed_url:
            return None

        host = (parsed_url.hostname or "").lower()
        path_parts = [part for part in parsed_url.path.strip("/").split("/") if part]
        if len(path_parts) < 2:
            return None

        workspace = path_parts[0].lower()
        repo_slug = cls._strip_git_suffix(path_parts[1]).lower()
        if not host or not workspace or not repo_slug:
            return None

        provider = cls.provider_from_host(host)
        repository_key = f"{host}/{workspace}/{repo_slug}"
        canonical_remote_url = f"https://{host}/{workspace}/{repo_slug}.git"

        return RepositoryIdentity(
            provider=provider,
            host=host,
            workspace=workspace,
            repo_slug=repo_slug,
            repository_key=repository_key,
            canonical_remote_url=canonical_remote_url,
            resolver_source="origin_url",
            resolver_confidence=1.0,
        )

    @classmethod
    def basename_fallback(
        cls, git_root_basename: str | None
    ) -> RepositoryIdentity | None:
        repo_slug = cls._strip_git_suffix((git_root_basename or "").strip()).lower()
        if not repo_slug:
            return None

        # Low-confidence fallback is intentionally namespaced away from real Git remotes.
        host = "local-fallback"
        workspace = "unknown"
        repository_key = f"{host}/{workspace}/{repo_slug}"
        return RepositoryIdentity(
            provider="unknown",
            host=host,
            workspace=workspace,
            repo_slug=repo_slug,
            repository_key=repository_key,
            canonical_remote_url=None,
            resolver_source="basename_fallback",
            resolver_confidence=0.25,
        )

    @classmethod
    async def upsert_repository(
        cls, org_id: UUID, identity: RepositoryIdentity
    ) -> Repository:
        repository, created = await Repository.get_or_create(
            org_id=org_id,
            repository_key=identity.repository_key,
            defaults={
                "provider": identity.provider,
                "host": identity.host,
                "workspace": identity.workspace,
                "repo_slug": identity.repo_slug,
                "display_name": identity.repo_slug,
                "canonical_remote_url": identity.canonical_remote_url,
                "resolver_source": identity.resolver_source,
                "resolver_confidence": identity.resolver_confidence,
                "metadata": {"created_from_resolver": True},
            },
        )

        if created:
            return repository

        repository.provider = identity.provider
        repository.host = identity.host
        repository.workspace = identity.workspace
        repository.repo_slug = identity.repo_slug
        repository.canonical_remote_url = (
            identity.canonical_remote_url or repository.canonical_remote_url
        )
        repository.resolver_source = identity.resolver_source
        repository.resolver_confidence = max(
            repository.resolver_confidence or 0.0, identity.resolver_confidence
        )
        await repository.save()
        return repository

    @classmethod
    async def _get_explicit_repository(
        cls, repository_id: UUID | None, org_id: UUID
    ) -> Repository | None:
        if not repository_id:
            return None
        repository = await Repository.get_or_none(
            id=repository_id, org_id=org_id, is_active=True
        )
        if not repository:
            raise bad_request("Repository id is invalid for this organization")
        return repository

    @classmethod
    def _context_from_model(
        cls,
        repository: Repository,
        branch: str | None,
        commit_sha: str | None,
        metadata: dict,
    ) -> RepositoryContext:
        return RepositoryContext(
            repo_id=repository.id,
            org_id=repository.org_id,
            provider=repository.provider,
            host=repository.host,
            workspace=repository.workspace,
            repo_slug=repository.repo_slug,
            repository_key=repository.repository_key,
            canonical_remote_url=repository.canonical_remote_url,
            resolver_source=repository.resolver_source,
            resolver_confidence=repository.resolver_confidence,
            branch=branch,
            commit_sha=commit_sha,
            metadata=metadata,
        )

    @classmethod
    def _parse_git_remote(cls, origin_url: str):
        if origin_url.startswith("git@") and ":" in origin_url:
            user_host, path = origin_url.split(":", 1)
            _, host = user_host.split("@", 1)
            return urlparse(f"ssh://git@{host}/{path}")

        parsed_url = urlparse(origin_url)
        if parsed_url.scheme in {"http", "https"} and parsed_url.username:
            netloc = parsed_url.hostname or ""
            if parsed_url.port:
                netloc = f"{netloc}:{parsed_url.port}"
            parsed_url = urlparse(
                urlunparse((parsed_url.scheme, netloc, parsed_url.path, "", "", ""))
            )

        if parsed_url.scheme in {"ssh", "http", "https"}:
            return parsed_url
        return None

    @classmethod
    def _strip_git_suffix(cls, value: str) -> str:
        if value.endswith(".git"):
            return value[:-4]
        return value

    @classmethod
    def provider_from_host(cls, host: str) -> str:
        if host == cls.BITBUCKET_HOST:
            return cls.BITBUCKET_PROVIDER
        return "git"
