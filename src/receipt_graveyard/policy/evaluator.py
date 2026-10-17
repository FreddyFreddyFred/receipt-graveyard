"""Evaluate per-receipt policy rules that do not require submission history."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from receipt_graveyard.models.policy import PolicyRule
from receipt_graveyard.models.receipt import LineItem, Receipt
from receipt_graveyard.models.verdict import Verdict, VerdictStatus
from receipt_graveyard.policy.context import (
    ExpenseContext,
    evaluate_context_violations,
)
from receipt_graveyard.policy.parser import ExpensePolicy
from receipt_graveyard.policy.results import PolicyViolation


class PolicyEvaluationError(ValueError):
    """Raised when an evaluator input cannot be interpreted safely."""


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    """The per-receipt result and its structured policy findings."""

    receipt_id: UUID
    violations: tuple[PolicyViolation, ...]

    @property
    def passed(self) -> bool:
        """Whether no rule found a violation or unresolved policy check."""
        return not self.violations

    @property
    def status(self) -> VerdictStatus:
        """Map findings to the shared receipt verdict status."""
        if any(v.status is VerdictStatus.DENIED for v in self.violations):
            return VerdictStatus.DENIED
        if self.violations:
            return VerdictStatus.FLAGGED_FOR_REVIEW
        return VerdictStatus.APPROVED

    def to_verdict(self) -> Verdict:
        """Build the project-wide verdict model while preserving rule references."""
        return Verdict(
            receipt_id=self.receipt_id,
            status=self.status,
            reasons=[violation.message for violation in self.violations]
            or ["No applicable per-receipt policy rules were violated."],
            rule_ids=list(dict.fromkeys(v.rule_id for v in self.violations)),
        )


def _decimal(value: Any, *, rule: PolicyRule, parameter: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise PolicyEvaluationError(
            f"rule '{rule.rule_id}' has an invalid {parameter} amount"
        ) from exc
    if not result.is_finite():
        raise PolicyEvaluationError(
            f"rule '{rule.rule_id}' has a non-finite {parameter} amount"
        )
    return result


def _line_amount(item: LineItem) -> Decimal | None:
    if item.amount is not None:
        return item.amount
    if item.quantity is not None and item.unit_price is not None:
        return item.quantity * item.unit_price
    return None


def _normalise_phrase(text: str) -> str:
    return " ".join(text.split()).casefold()


def _contains_item(description: str, banned_item: str) -> bool:
    phrase = _normalise_phrase(banned_item)
    candidate = _normalise_phrase(description)
    if not phrase:
        return False
    pattern = rf"(?<!\w){re.escape(phrase)}(?!\w)"
    return re.search(pattern, candidate) is not None


def _category_cap_violations(
    receipt: Receipt, policy: ExpensePolicy, rule: PolicyRule
) -> list[PolicyViolation]:
    category = (rule.category or "").strip().casefold()
    items = [
        item
        for item in receipt.line_items
        if item.category is not None and item.category.strip().casefold() == category
    ]
    if not items:
        return []

    rule_currency = str(rule.parameters.get("currency", policy.base_currency)).upper()
    receipt_currency = str(receipt.currency or policy.base_currency).upper()
    if rule_currency != receipt_currency:
        return [
            PolicyViolation(
                rule_id=rule.rule_id,
                rule_type=rule.type,
                message=(
                    f"Cannot compare {category} receipt amount in {receipt_currency} "
                    f"with the {rule_currency} limit until currency conversion is available."
                ),
                status=VerdictStatus.FLAGGED_FOR_REVIEW,
            )
        ]

    limit = _decimal(rule.parameters.get("limit"), rule=rule, parameter="limit")
    known_amounts = [(item, _line_amount(item)) for item in items]
    total = sum(
        (amount for _, amount in known_amounts if amount is not None),
        start=Decimal(0),
    )
    violations: list[PolicyViolation] = []
    for item, amount in known_amounts:
        if amount is None:
            violations.append(
                PolicyViolation(
                    rule_id=rule.rule_id,
                    rule_type=rule.type,
                    message=(
                        f"Cannot verify the {category} cap because line item "
                        f"'{item.description}' has no amount."
                    ),
                    status=VerdictStatus.FLAGGED_FOR_REVIEW,
                    limit=limit,
                    item_description=item.description,
                )
            )

    if total > limit:
        period = str(rule.parameters.get("period", "receipt"))
        violations.append(
            PolicyViolation(
                rule_id=rule.rule_id,
                rule_type=rule.type,
                message=(
                    f"{category.title()} spending on this receipt is {total} "
                    f"{receipt_currency}, above the {period} cap of {limit} "
                    f"{rule_currency}."
                ),
                status=VerdictStatus.FLAGGED_FOR_REVIEW,
                amount=total,
                limit=limit,
            )
        )
    return violations


def _non_reimbursable_violations(rule: PolicyRule, receipt: Receipt) -> list[PolicyViolation]:
    banned_items = rule.parameters.get("items", [])
    return [
        PolicyViolation(
            rule_id=rule.rule_id,
            rule_type=rule.type,
            message=(
                f"Line item '{item.description}' matches non-reimbursable item "
                f"'{banned_item}'."
            ),
            status=VerdictStatus.DENIED,
            amount=_line_amount(item),
            item_description=item.description,
        )
        for item in receipt.line_items
        for banned_item in banned_items
        if _contains_item(item.description, str(banned_item))
    ]


def evaluate_receipt(
    receipt: Receipt,
    policy: ExpensePolicy,
    *,
    context: ExpenseContext | None = None,
) -> PolicyEvaluation:
    """Evaluate category caps and item exclusions for one receipt.

    Cumulative daily, monthly, and trip totals require other submissions and are
    intentionally outside this per-receipt API. Trip/office and city limits are
    included when optional context metadata is supplied; missing metadata uses
    the most restrictive configured limit.
    """
    violations: list[PolicyViolation] = []
    for rule in policy.rules:
        if rule.type == "category_cap":
            violations.extend(_category_cap_violations(receipt, policy, rule))
        elif rule.type == "non_reimbursable":
            violations.extend(_non_reimbursable_violations(rule, receipt))
    violations.extend(evaluate_context_violations(receipt, policy, context))
    return PolicyEvaluation(receipt_id=receipt.id, violations=tuple(violations))
