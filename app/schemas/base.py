"""Shared Pydantic schema primitives for Engram contracts."""

from pydantic import BaseModel, ConfigDict


class EngramBaseSchema(BaseModel):
    """Base schema that keeps API contracts strict enough without being brittle."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )
