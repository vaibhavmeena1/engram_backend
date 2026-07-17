"""Review workflow schemas."""

from uuid import UUID

from pydantic import Field

from app.schemas.base import EngramBaseSchema


class ProposalReviewRequest(EngramBaseSchema):
    review_notes: str | None = None
    metadata: dict = Field(default_factory=dict)


class ProposalApplyEditedRequest(ProposalReviewRequest):
    edited_content: str = Field(min_length=1)
    edited_rationale: str | None = None
    edited_summary: str | None = None
    edited_metadata: dict = Field(default_factory=dict)


class ProposalReviewResult(EngramBaseSchema):
    proposal_id: UUID
    memory_fact_id: UUID | None = None
    status: str
    applied: bool = False
