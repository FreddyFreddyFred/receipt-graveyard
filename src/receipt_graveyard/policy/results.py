"""Shared structured policy findings."""

from dataclasses import dataclass
from decimal import Decimal

from receipt_graveyard.models.verdict import VerdictStatus


@dataclass(frozen=True, slots=True)
class PolicyViolation:
    """A policy finding linked to the rule that produced it."""

    rule_id: str
    rule_type: str
    message: str
    status: VerdictStatus
    amount: Decimal | None = None
    limit: Decimal | None = None
    item_description: str | None = None
