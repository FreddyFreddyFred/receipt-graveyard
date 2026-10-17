"""Track per-employee daily and monthly category spending against policy caps."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from receipt_graveyard.models.policy import PolicyRule
from receipt_graveyard.models.receipt import LineItem, Receipt
from receipt_graveyard.models.verdict import VerdictStatus
from receipt_graveyard.policy.evaluator import (
    PolicyEvaluation,
    PolicyEvaluationError,
    PolicyViolation,
)
from receipt_graveyard.policy.parser import ExpensePolicy

_Bucket = tuple[str, str, str, str]


class CumulativeTrackingError(ValueError):
    """Raised when a receipt lacks identity or date needed for aggregation."""


class CumulativeLimitTracker:
    """Accumulate receipt line items by employee, category rule, and time window.

    Add receipts in submission order. The result for each call is immutable, so
    later receipts that exceed a limit do not change earlier results.
    """

    def __init__(self, policy: ExpensePolicy) -> None:
        self._policy = policy
        self._totals: dict[_Bucket, Decimal] = {}
        self._incomplete: set[_Bucket] = set()
        self._seen_receipts: set[UUID] = set()

    def add_receipt(self, receipt: Receipt) -> PolicyEvaluation:
        """Record a receipt and flag daily/monthly caps crossed by its amounts."""
        if receipt.id in self._seen_receipts:
            raise CumulativeTrackingError(
                f"receipt '{receipt.id}' was already added to this tracker"
            )

        employee_id = (receipt.employee_id or "").strip()
        violations: list[PolicyViolation] = []
        pending_totals: dict[_Bucket, Decimal] = {}
        pending_incomplete: set[_Bucket] = set()

        for rule in self._policy.rules:
            if rule.type != "category_cap":
                continue
            category = (rule.category or "").strip().casefold()
            items = [
                item
                for item in receipt.line_items
                if item.category is not None
                and item.category.strip().casefold() == category
            ]
            if not items:
                continue

            period = str(rule.parameters.get("period", "daily"))
            if period == "trip":
                violations.append(
                    _violation(
                        rule,
                        f"Cannot track the trip cap for {category}: this receipt has no trip-period context.",
                    )
                )
                continue
            if period not in {"daily", "monthly"}:
                raise PolicyEvaluationError(
                    f"rule '{rule.rule_id}' has unsupported cumulative period '{period}'"
                )
            if not employee_id:
                raise CumulativeTrackingError(
                    f"receipt '{receipt.id}' needs employee_id for rule '{rule.rule_id}'"
                )
            if receipt.date is None:
                raise CumulativeTrackingError(
                    f"receipt '{receipt.id}' needs a date for rule '{rule.rule_id}'"
                )

            window = _window_key(receipt.date, period)
            bucket = (employee_id, rule.rule_id, period, window)
            limit = _as_decimal(rule.parameters.get("limit"), rule, "limit")
            expected_currency = str(
                rule.parameters.get("currency", self._policy.base_currency)
            ).upper()
            receipt_currency = str(
                receipt.currency or self._policy.base_currency
            ).upper()
            if receipt_currency != expected_currency:
                violations.append(
                    _violation(
                        rule,
                        f"Cannot compare cumulative {category} spending in "
                        f"{receipt_currency} with the {expected_currency} limit without currency conversion.",
                        limit=limit,
                    )
                )
                pending_incomplete.add(bucket)
                continue

            amounts = [_item_amount(item) for item in items]
            known_amount = sum(
                (amount for amount in amounts if amount is not None),
                start=Decimal(0),
            )
            prior_total = self._totals.get(bucket, Decimal(0))
            cumulative_total = prior_total + known_amount

            if bucket in self._incomplete:
                violations.append(
                    _violation(
                        rule,
                        f"Cannot confirm the {period} {category} total because an earlier receipt in this period had incomplete data.",
                        amount=cumulative_total,
                        limit=limit,
                    )
                )

            for item, amount in zip(items, amounts, strict=True):
                if amount is None:
                    violations.append(
                        _violation(
                            rule,
                            f"Cannot include line item '{item.description}' in the cumulative {category} total because its amount is missing.",
                            limit=limit,
                            item_description=item.description,
                        )
                    )
                    pending_incomplete.add(bucket)

            if cumulative_total > limit:
                violations.append(
                    _violation(
                        rule,
                        f"{category.title()} spending for employee {employee_id} "
                        f"in {period} {window} totals {cumulative_total}, above the cap of {limit} {expected_currency}.",
                        amount=cumulative_total,
                        limit=limit,
                    )
                )

            pending_totals[bucket] = cumulative_total

        # Commit state only after every applicable rule input has been checked.
        self._totals.update(pending_totals)
        self._incomplete.update(pending_incomplete)
        self._seen_receipts.add(receipt.id)
        return PolicyEvaluation(receipt_id=receipt.id, violations=tuple(violations))


def _window_key(receipt_date: date, period: str) -> str:
    if period == "daily":
        return receipt_date.isoformat()
    return receipt_date.strftime("%Y-%m")


def _item_amount(item: LineItem) -> Decimal | None:
    if item.amount is not None:
        amount = item.amount
    elif item.quantity is not None and item.unit_price is not None:
        amount = item.quantity * item.unit_price
    else:
        return None
    if not amount.is_finite():
        raise CumulativeTrackingError(
            f"line item '{item.description}' has a non-finite amount"
        )
    return amount


def _as_decimal(value: Any, rule: PolicyRule, parameter: str) -> Decimal:
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise PolicyEvaluationError(
            f"rule '{rule.rule_id}' has an invalid {parameter} amount"
        ) from exc
    if not amount.is_finite():
        raise PolicyEvaluationError(
            f"rule '{rule.rule_id}' has a non-finite {parameter} amount"
        )
    return amount


def _violation(
    rule: PolicyRule,
    message: str,
    *,
    amount: Decimal | None = None,
    limit: Decimal | None = None,
    item_description: str | None = None,
) -> PolicyViolation:
    return PolicyViolation(
        rule_id=rule.rule_id,
        rule_type=rule.type,
        message=message,
        status=VerdictStatus.FLAGGED_FOR_REVIEW,
        amount=amount,
        limit=limit,
        item_description=item_description,
    )
