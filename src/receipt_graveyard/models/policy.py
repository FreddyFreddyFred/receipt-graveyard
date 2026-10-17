"""Pydantic model for a policy rule and its rule-specific parameters."""

from typing import Any

from pydantic import BaseModel, Field


class PolicyRule(BaseModel):
    """A named policy rule; T3.1 validates type-specific parameters."""

    rule_id: str
    type: str
    category: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None
