"""Dashboard tag management service."""

import re
from uuid import UUID

from app.models.memory import Tag
from app.schemas.context import ActorContext
from app.schemas.tag import TagCreateRequest, TagResponse, TagUpdateRequest
from app.services.rbac_service import RbacService
from app.services.vortex_http import bad_request, conflict, forbidden, not_found

_TAG_SLUG_PATTERN = re.compile(r"[^a-z0-9-]+")


class TagService:
    """Manages organization tags without exposing ORM details to routers."""

    @classmethod
    async def list_tags(cls, actor: ActorContext) -> list[TagResponse]:
        tags = await Tag.filter(org_id=actor.org_id).order_by("slug")
        return [cls._tag_response(tag) for tag in tags]

    @classmethod
    async def create_tag(
        cls, actor: ActorContext, request: TagCreateRequest
    ) -> TagResponse:
        cls._ensure_can_manage_tags(actor)
        slug = cls._normalize_slug(request.slug or request.label)
        existing_tag = await Tag.get_or_none(org_id=actor.org_id, slug=slug)
        if existing_tag:
            raise conflict("Tag slug already exists")

        tag = await Tag.create(
            org_id=actor.org_id,
            slug=slug,
            label=request.label,
            description=request.description,
            color=request.color,
            metadata=request.metadata,
        )
        return cls._tag_response(tag)

    @classmethod
    async def update_tag(
        cls, actor: ActorContext, tag_id: UUID, request: TagUpdateRequest
    ) -> TagResponse:
        cls._ensure_can_manage_tags(actor)
        tag = await cls._get_tag(actor, tag_id)

        if request.slug is not None:
            next_slug = cls._normalize_slug(request.slug)
            existing_tag = await Tag.get_or_none(org_id=actor.org_id, slug=next_slug)
            if existing_tag and existing_tag.id != tag.id:
                raise conflict("Tag slug already exists")
            tag.slug = next_slug
        if request.label is not None:
            tag.label = request.label
        if "description" in request.model_fields_set:
            tag.description = request.description
        if "color" in request.model_fields_set:
            tag.color = request.color
        if request.metadata is not None:
            tag.metadata = request.metadata

        await tag.save()
        return cls._tag_response(tag)

    @classmethod
    async def delete_tag(cls, actor: ActorContext, tag_id: UUID) -> TagResponse:
        cls._ensure_can_manage_tags(actor)
        tag = await cls._get_tag(actor, tag_id)
        response = cls._tag_response(tag)
        await tag.delete()
        return response

    @classmethod
    async def _get_tag(cls, actor: ActorContext, tag_id: UUID) -> Tag:
        tag = await Tag.get_or_none(id=tag_id, org_id=actor.org_id)
        if not tag:
            raise not_found("Tag not found")
        return tag

    @classmethod
    def _ensure_can_manage_tags(cls, actor: ActorContext) -> None:
        if not RbacService.can_manage_tags(actor, actor.org_id):
            raise forbidden("Actor cannot manage tags")

    @classmethod
    def _normalize_slug(cls, value: str) -> str:
        slug = _TAG_SLUG_PATTERN.sub("-", value.strip().lower()).strip("-")
        if not slug:
            raise bad_request("Tag slug cannot be empty")
        return slug[:120]

    @classmethod
    def _tag_response(cls, tag: Tag) -> TagResponse:
        return TagResponse(
            id=tag.id,
            org_id=tag.org_id,
            slug=tag.slug,
            label=tag.label,
            description=tag.description,
            color=tag.color,
            metadata=tag.metadata or {},
            created_at=tag.created_at,
            updated_at=tag.updated_at,
        )
