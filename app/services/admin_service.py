"""Admin dashboard service for users, roles, and role assignments."""

from uuid import UUID

from app.models.identity import Role, RoleAssignment, User
from app.schemas.admin import (
    RoleAssignmentCreateRequest,
    RoleAssignmentResponse,
    RoleResponse,
    UserResponse,
)
from app.schemas.context import ActorContext
from app.services.rbac_service import RbacService
from app.services.vortex_http import bad_request, forbidden, not_found


class AdminService:
    """Keeps admin authorization and identity ORM access behind one service boundary."""

    @classmethod
    async def list_users(
        cls, actor: ActorContext, limit: int = 100, offset: int = 0
    ) -> list[UserResponse]:
        cls._ensure_admin(actor)
        users = await User.all().order_by("email").offset(offset).limit(limit)
        return [cls._user_response(user) for user in users]

    @classmethod
    async def list_roles(cls, actor: ActorContext) -> list[RoleResponse]:
        cls._ensure_admin(actor)
        roles = await Role.filter(org_id=actor.org_id).order_by("slug")
        return [cls._role_response(role) for role in roles]

    @classmethod
    async def list_role_assignments(
        cls,
        actor: ActorContext,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RoleAssignmentResponse]:
        cls._ensure_admin(actor)
        assignments = await (
            RoleAssignment.filter(org_id=actor.org_id)
            .select_related("user", "role")
            .order_by("-created_at")
            .offset(offset)
            .limit(limit)
        )
        return [cls._role_assignment_response(assignment) for assignment in assignments]

    @classmethod
    async def create_role_assignment(
        cls,
        actor: ActorContext,
        request: RoleAssignmentCreateRequest,
    ) -> RoleAssignmentResponse:
        cls._ensure_admin(actor)
        user = await User.get_or_none(id=request.user_id, is_active=True)
        if not user:
            raise bad_request("User is invalid or inactive")

        role = await Role.get_or_none(id=request.role_id, org_id=actor.org_id)
        if not role:
            raise bad_request("Role is invalid for this organization")

        assignment, created = await RoleAssignment.get_or_create(
            org_id=actor.org_id,
            user_id=user.id,
            role_id=role.id,
            scope_type=request.scope_type,
            scope_id=request.scope_id,
            defaults={
                "assigned_by_id": actor.actor_user_id,
                "metadata": request.metadata,
            },
        )
        if not created:
            assignment.metadata = {**(assignment.metadata or {}), **request.metadata}
            assignment.assigned_by_id = actor.actor_user_id
            await assignment.save()

        assignment.user = user
        assignment.role = role
        return cls._role_assignment_response(assignment)

    @classmethod
    async def delete_role_assignment(
        cls, actor: ActorContext, assignment_id: UUID
    ) -> RoleAssignmentResponse:
        cls._ensure_admin(actor)
        assignment = await (
            RoleAssignment.filter(id=assignment_id, org_id=actor.org_id)
            .select_related("user", "role")
            .first()
        )
        if not assignment:
            raise not_found("Role assignment not found")

        response = cls._role_assignment_response(assignment)
        await assignment.delete()
        return response

    @classmethod
    def _ensure_admin(cls, actor: ActorContext) -> None:
        if not RbacService.is_admin(actor):
            raise forbidden("Admin access is required")

    @classmethod
    def _user_response(cls, user: User) -> UserResponse:
        return UserResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            metadata=user.metadata or {},
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @classmethod
    def _role_response(cls, role: Role) -> RoleResponse:
        return RoleResponse(
            id=role.id,
            org_id=role.org_id,
            slug=role.slug,
            name=role.name,
            description=role.description,
            permissions=role.permissions or [],
            is_system=role.is_system,
            metadata=role.metadata or {},
            created_at=role.created_at,
            updated_at=role.updated_at,
        )

    @classmethod
    def _role_assignment_response(
        cls, assignment: RoleAssignment
    ) -> RoleAssignmentResponse:
        user = getattr(assignment, "user", None)
        role = getattr(assignment, "role", None)
        return RoleAssignmentResponse(
            id=assignment.id,
            org_id=assignment.org_id,
            user_id=assignment.user_id,
            role_id=assignment.role_id,
            assigned_by_id=assignment.assigned_by_id,
            scope_type=assignment.scope_type,
            scope_id=assignment.scope_id,
            metadata=assignment.metadata or {},
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
            user_email=user.email if user else None,
            role_slug=role.slug if role else None,
            role_name=role.name if role else None,
        )
