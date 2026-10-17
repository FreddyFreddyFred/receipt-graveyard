"""Tests for cumulative employee category-limit tracking."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from receipt_graveyard.detection.accumulator import (
    CumulativeLimitTracker,
    CumulativeTrackingError,
)
from receipt_graveyard.models.receipt import LineItem, Receipt
from receipt_graveyard.models.verdict import VerdictStatus
from receipt_graveyard.policy.parser import parse_policy


def _policy(daily_limit: int = 50, monthly_limit: int = 100):
    return parse_policy(
        f"""\
version: 1
rules:
  - rule_id: meals.daily
    type: category_cap
    category: meals
    parameters:
      limit: {daily_limit}
      period: daily
  - rule_id: meals.monthly
    type: category_cap
    category: meals
    parameters:
      limit: {monthly_limit}
      period: monthly
"""
    )


def _receipt(
    amount: int | None,
    *,
    employee: str = "employee-001",
    purchased: date = date(2026, 1, 15),
    receipt_id=None,
) -> Receipt:
    item_data = {"description": "Lunch", "category": "meals"}
    if amount is not None:
        item_data["amount"] = Decimal(amount)
    return Receipt(
        id=receipt_id or uuid4(),
        employee_id=employee,
        date=purchased,
        currency="USD",
        line_items=[LineItem(**item_data)],
    )


def test_daily_limit_flags_only_the_receipt_that_crosses_the_cap() -> None:
    tracker = CumulativeLimitTracker(_policy(daily_limit=50))
    results = [tracker.add_receipt(_receipt(12)) for _ in range(5)]

    assert all(result.passed for result in results[:4])
    assert results[4].status is VerdictStatus.FLAGGED_FOR_REVIEW
    assert results[4].violations[0].rule_id == "meals.daily"
    assert results[4].violations[0].amount == Decimal(60)
    # Earlier results are immutable after the fifth receipt is submitted.
    assert all(result.status is VerdictStatus.APPROVED for result in results[:4])


def test_monthly_bucket_spans_days_but_resets_at_month_boundary() -> None:
    tracker = CumulativeLimitTracker(_policy(daily_limit=100, monthly_limit=50))
    january = tracker.add_receipt(_receipt(30, purchased=date(2026, 1, 31)))
    february_first = tracker.add_receipt(_receipt(30, purchased=date(2026, 2, 1)))
    february_second = tracker.add_receipt(_receipt(30, purchased=date(2026, 2, 2)))

    assert january.passed
    assert february_first.passed
    assert february_second.status is VerdictStatus.FLAGGED_FOR_REVIEW
    assert [v.rule_id for v in february_second.violations] == ["meals.monthly"]


def test_totals_are_isolated_per_employee() -> None:
    tracker = CumulativeLimitTracker(_policy(daily_limit=50))
    first_employee = tracker.add_receipt(_receipt(40, employee="employee-001"))
    second_employee = tracker.add_receipt(_receipt(40, employee="employee-002"))

    assert first_employee.passed
    assert second_employee.passed


def test_incomplete_receipt_taints_period_for_following_checks() -> None:
    tracker = CumulativeLimitTracker(_policy())
    incomplete = tracker.add_receipt(_receipt(None))
    following = tracker.add_receipt(_receipt(10))

    assert incomplete.status is VerdictStatus.FLAGGED_FOR_REVIEW
    assert following.status is VerdictStatus.FLAGGED_FOR_REVIEW
    assert any("earlier receipt" in violation.message for violation in following.violations)


def test_currency_mismatch_taints_cumulative_bucket() -> None:
    tracker = CumulativeLimitTracker(_policy())
    receipt = _receipt(10)
    receipt.currency = "EUR"
    mismatch = tracker.add_receipt(receipt)
    following = tracker.add_receipt(_receipt(10))

    assert mismatch.status is VerdictStatus.FLAGGED_FOR_REVIEW
    assert following.status is VerdictStatus.FLAGGED_FOR_REVIEW


def test_duplicate_receipt_cannot_be_counted_twice() -> None:
    tracker = CumulativeLimitTracker(_policy())
    receipt = _receipt(10)
    tracker.add_receipt(receipt)

    with pytest.raises(CumulativeTrackingError, match="already added"):
        tracker.add_receipt(receipt)


def test_missing_employee_or_date_is_rejected_when_category_cap_applies() -> None:
    tracker = CumulativeLimitTracker(_policy())
    missing_employee = _receipt(10)
    missing_employee.employee_id = None
    missing_date = _receipt(10)
    missing_date.date = None

    with pytest.raises(CumulativeTrackingError, match="needs employee_id"):
        tracker.add_receipt(missing_employee)
    with pytest.raises(CumulativeTrackingError, match="needs a date"):
        tracker.add_receipt(missing_date)
