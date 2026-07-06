"""Scope discovery service for dashboard memory creation."""

from tortoise.expressions import Q

from app.models.identity import Organization, User
from app.models.repository import Repository
from app.schemas.context import ActorContext
from app.schemas.enums import ScopeType
from app.schemas.scope import ScopeOptionResponse, ScopeOptionsResponse
from app.services.rbac_service import RbacService


class ScopeService:
    """Provides human-readable scope options while keeping write RBAC authoritative."""

    @classmethod
    async def list_scope_options(cls, actor: ActorContext) -> ScopeOptionsResponse:
        current_user = await cls._current_user_option(actor)
        organizations = await cls.list_organizations(actor)
        repositories = await cls.list_repositories(actor)

        return ScopeOptionsResponse(
            current_user=current_user,
            organizations=organizations,
            repositories=repositories,
        )

    @classmethod
    async def search_scopes(
        cls,
        actor: ActorContext,
        *,
        query: str | None = None,
        scope_type: ScopeType | None = None,
        limit: int = 50,
    ) -> list[ScopeOptionResponse]:
        normalized_query = cls._normalize_query(query)
        options: list[ScopeOptionResponse] = []

        if scope_type in {None, ScopeType.USER}:
            options.extend(
                await cls.search_users(actor, query=normalized_query, limit=limit)
            )
        if scope_type in {None, ScopeType.ORG}:
            options.extend(
                await cls.list_organizations(actor, query=normalized_query, limit=limit)
            )
        if scope_type in {None, ScopeType.REPO}:
            options.extend(
                await cls.list_repositories(actor, query=normalized_query, limit=limit)
            )

        return options[:limit]

    @classmethod
    async def search_users(
        cls,
        actor: ActorContext,
        *,
        query: str | None = None,
        limit: int = 50,
    ) -> list[ScopeOptionResponse]:
        normalized_query = cls._normalize_query(query)

        # Non-admin users can only discover themselves for memory creation.
        if not RbacService.is_admin(actor):
            current_user = await cls._current_user_option(actor)
            if normalized_query and not cls._matches_user_option(
                current_user, normalized_query
            ):
                return []
            return [current_user]

        user_query = User.filter(is_active=True)
        if normalized_query:
            user_query = user_query.filter(
                Q(email__icontains=normalized_query)
                | Q(display_name__icontains=normalized_query)
            )
        users = await user_query.order_by("email").limit(limit)
        return [cls._user_option(user, actor) for user in users]

    @classmethod
    async def list_organizations(
        cls,
        actor: ActorContext,
        *,
        query: str | None = None,
        limit: int = 100,
    ) -> list[ScopeOptionResponse]:
        normalized_query = cls._normalize_query(query)
        org_query = Organization.filter(id=actor.org_id, is_active=True)
        if normalized_query:
            org_query = org_query.filter(
                Q(name__icontains=normalized_query)
                | Q(slug__icontains=normalized_query)
            )
        organizations = await org_query.order_by("slug").limit(limit)
        return [
            cls._organization_option(organization) for organization in organizations
        ]

    @classmethod
    async def list_repositories(
        cls,
        actor: ActorContext,
        *,
        query: str | None = None,
        limit: int = 100,
    ) -> list[ScopeOptionResponse]:
        normalized_query = cls._normalize_query(query)
        repo_query = Repository.filter(org_id=actor.org_id, is_active=True)
        if normalized_query:
            repo_query = repo_query.filter(
                Q(display_name__icontains=normalized_query)
                | Q(repository_key__icontains=normalized_query)
                | Q(repo_slug__icontains=normalized_query)
                | Q(canonical_remote_url__icontains=normalized_query)
            )
        repositories = await repo_query.order_by("workspace", "repo_slug").limit(limit)
        return [cls._repository_option(repository) for repository in repositories]

    @classmethod
    async def _current_user_option(cls, actor: ActorContext) -> ScopeOptionResponse:
        user = await User.get_or_none(id=actor.actor_user_id)
        if user:
            return cls._user_option(user, actor)

        return ScopeOptionResponse(
            scope_type=ScopeType.USER,
            scope_id=actor.actor_user_id,
            label=actor.email,
            detail="Current user",
            metadata={"email": actor.email, "is_current_actor": True},
        )

    @classmethod
    def _user_option(cls, user: User, actor: ActorContext) -> ScopeOptionResponse:
        return ScopeOptionResponse(
            scope_type=ScopeType.USER,
            scope_id=user.id,
            label=user.display_name or user.email,
            detail=user.email,
            metadata={
                "email": user.email,
                "display_name": user.display_name,
                "is_current_actor": user.id == actor.actor_user_id,
            },
        )

    @classmethod
    def _organization_option(cls, organization: Organization) -> ScopeOptionResponse:
        return ScopeOptionResponse(
            scope_type=ScopeType.ORG,
            scope_id=organization.id,
            label=organization.name,
            detail=organization.slug,
            metadata={"slug": organization.slug},
        )

    @classmethod
    def _repository_option(cls, repository: Repository) -> ScopeOptionResponse:
        return ScopeOptionResponse(
            scope_type=ScopeType.REPO,
            scope_id=repository.id,
            label=repository.display_name or repository.repo_slug,
            detail=repository.repository_key,
            metadata={
                "provider": repository.provider,
                "host": repository.host,
                "workspace": repository.workspace,
                "repo_slug": repository.repo_slug,
                "repository_key": repository.repository_key,
                "canonical_remote_url": repository.canonical_remote_url,
            },
        )

    @classmethod
    def _matches_user_option(cls, option: ScopeOptionResponse, query: str) -> bool:
        searchable_values = [
            option.label,
            option.detail,
            str(option.metadata.get("email") or ""),
        ]
        return any(query in value.lower() for value in searchable_values if value)

    @classmethod
    def _normalize_query(cls, query: str | None) -> str | None:
        normalized_query = " ".join((query or "").strip().split()).lower()
        return normalized_query or None
