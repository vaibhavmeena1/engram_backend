"""Shared Tortoise model primitives for Engram tables."""

import uuid

from tortoise import fields, models


class EngramModel(models.Model):
    """Common UUID/timestamp fields for all Engram ORM models."""

    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True
