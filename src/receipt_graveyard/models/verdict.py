"""Pydantic models for compliance verdicts."""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class VerdictStatus(str, Enum):
    """Human-readable compliance result labels used by the MVP."""

    APPROVED = "Approved"
    FLAGGED_FOR_REVIEW = "Flagged for Review"
    DENIED = "Denied"


class Verdict(BaseModel):
    """A receipt decision with human-readable reasons and rule references."""

    receipt_id: UUID
    status: VerdictStatus
    reasons: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
