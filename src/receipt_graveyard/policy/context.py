"""Evaluate policy rules that depend on an employee's expense context."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal

from receipt_graveyard.models.receipt import Receipt
from receipt_graveyard.models.verdict import VerdictStatus
from receipt_graveyard.policy.parser import ExpensePolicy
from receipt_graveyard.policy.results import PolicyViolation

ExpenseType = Literal["trip", "office"]


@dataclass(frozen=True, slots=True)
class ExpenseContext:
    """Optional trip/office and city metadata supplied alongside a receipt."""

    expense_type: ExpenseType | None = None
    city: str | None = None


class ContextEvaluationError(ValueError):
    """Raised when a contextual policy amount cannot be compared safely."""


def _amount(receipt: Receipt) -> Decimal | None:
    if receipt.total is not None:
        return receipt.total
    if not receipt.line_items or any(
        item.amount is None and (item.quantity is None or item.unit_price is None)
        for item in receipt.line_items
    ):
        return None
    return sum(
        (
            item.amount
            if item.amount is not None
            else item.quantity * item.unit_price
            for item in receipt.line_items
        ),
        start=Decimal(0),
    )


def _decimal(value: object, rule_id: str) -> Decimal:
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ContextEvaluationError(
            f"rule '{rule_id}' has an invalid limit amount"
        ) from exc
    if not amount.is_finite() or amount <= 0:
        raise ContextEvaluationError(
            f"rule '{rule_id}' has an invalid limit amount"
        )
    return amount


def _context_rules(policy: ExpensePolicy, expense_type: ExpenseType | None):
    rules = [rule for rule in policy.rules if rule.type == "context_limit"]
    if expense_type is None:
        candidates = [
            (rule, _decimal(rule.parameters["limit"], rule.rule_id)) for rule in rules
        ]
        if not candidates:
            return []
        lowest = min(limit for _, limit in candidates)
        return [(rule, limit) for rule, limit in candidates if limit == lowest]

    matching = [
        rule
        for rule in rules
        if str(rule.parameters["context"]).casefold() == expense_type.casefold()
    ]
    # An absent configuration for the requested context must not grant an
    # unlimited allowance. Fall back to the most restrictive configured rule.
    if not matching:
        return _context_rules(policy, None)
    return [
        (rule, _decimal(rule.parameters["limit"], rule.rule_id))
        for rule in matching
    ]


def _city_limit(rule, city: str | None) -> Decimal:
    limits = rule.parameters["limits"]
    if city is not None and city.strip():
        normalised_city = city.strip().casefold()
        matching = next(
            (
                value
                for name, value in limits.items()
                if str(name).strip().casefold() == normalised_city
            ),
            None,
        )
        if matching is not None:
            return _decimal(matching, rule.rule_id)
        fallback = next(
            (
                value
                for name, value in limits.items()
                if str(name).strip().casefold() == "other"
            ),
            None,
        )
        if fallback is not None:
            return _decimal(fallback, rule.rule_id)
    values = [_decimal(value, rule.rule_id) for value in limits.values()]
    return min(values)


def evaluate_context_violations(
    receipt: Receipt,
    policy: ExpensePolicy,
    context: ExpenseContext | None = None,
) -> list[PolicyViolation]:
    """Return findings from trip/office and city limit rules.

    Context-specific limits above their threshold are denied. City daily limits
    are flagged for review because a single-receipt evaluation cannot account
    for the employee's other spending that day.
    """
    if context is None:
        context = ExpenseContext()
    if context.expense_type not in (None, "trip", "office"):
        raise ContextEvaluationError(
            "expense_type must be 'trip', 'office', or None"
        )

    contextual_rules = _context_rules(policy, context.expense_type)
    city_rules = [rule for rule in policy.rules if rule.type == "city_daily_limit"]
    checks = [
        (rule, limit, "context_limit", VerdictStatus.DENIED)
        for rule, limit in contextual_rules
    ]
    checks.extend(
        (
            rule,
            _city_limit(rule, context.city),
            "city_daily_limit",
            VerdictStatus.FLAGGED_FOR_REVIEW,
        )
        for rule in city_rules
    )
    if not checks:
        return []

    amount = _amount(receipt)
    violations: list[PolicyViolation] = []
    for rule, limit, rule_type, breach_status in checks:
        rule_currency = str(
            rule.parameters.get("currency", policy.base_currency)
        ).upper()
        receipt_currency = str(
            receipt.currency or policy.base_currency
        ).upper()
        if rule_currency != receipt_currency:
            violations.append(
                PolicyViolation(
                    rule_id=rule.rule_id,
                    rule_type=rule_type,
                    message=(
                        f"Cannot compare receipt amount in {receipt_currency} with "
                        f"the {rule_currency} limit until currency conversion is available."
                    ),
                    status=VerdictStatus.FLAGGED_FOR_REVIEW,
                    limit=limit,
                )
            )
            continue
        if amount is None:
            violations.append(
                PolicyViolation(
                    rule_id=rule.rule_id,
                    rule_type=rule_type,
                    message=(
                        f"Cannot verify rule '{rule.rule_id}' because the receipt "
                        "has no complete amount."
                    ),
                    status=VerdictStatus.FLAGGED_FOR_REVIEW,
                    limit=limit,
                )
            )
            continue
        if amount > limit:
            if rule_type == "context_limit":
                applies_to = context.expense_type or "the most restrictive context"
                message = (
                    f"Receipt amount {amount} {receipt_currency} exceeds the "
                    f"{applies_to} limit of {limit} {rule_currency}."
                )
            else:
                applies_to = context.city or "an unspecified city"
                message = (
                    f"Receipt amount {amount} {receipt_currency} exceeds the "
                    f"daily limit for {applies_to} of {limit} {rule_currency}; "
                    "other same-day expenses still need review."
                )
            violations.append(
                PolicyViolation(
                    rule_id=rule.rule_id,
                    rule_type=rule_type,
                    message=message,
                    status=breach_status,
                    amount=amount,
                    limit=limit,
                )
            )
    return violations
