"""Tests for per-receipt policy evaluation."""

from decimal import Decimal

from receipt_graveyard.models.receipt import LineItem, Receipt
from receipt_graveyard.models.verdict import VerdictStatus
from receipt_graveyard.policy.context import ExpenseContext
from receipt_graveyard.policy.evaluator import evaluate_receipt
from receipt_graveyard.policy.parser import parse_policy

POLICY = parse_policy(
    """\
version: 1
rules:
  - rule_id: meals.daily-cap
    type: category_cap
    category: meals
    parameters:
      limit: 75
      period: daily
  - rule_id: alcohol.exclusion
    type: non_reimbursable
    parameters:
      items: [alcohol, wine]
"""
)


def test_receipt_under_category_cap_passes() -> None:
    receipt = Receipt(
        currency="USD",
        line_items=[
            LineItem(description="Lunch", category="Meals", amount=Decimal(35)),
            LineItem(
                description="Coffee",
                category="meals",
                quantity=2,
                unit_price=Decimal(5),
            ),
        ],
    )

    result = evaluate_receipt(receipt, POLICY)

    assert result.passed
    assert result.violations == ()
    assert result.status is VerdictStatus.APPROVED
    assert result.to_verdict().receipt_id == receipt.id


def test_category_cap_sums_receipt_items_and_references_rule() -> None:
    receipt = Receipt(
        currency="USD",
        line_items=[
            LineItem(description="Lunch", category="meals", amount=Decimal(40)),
            LineItem(description="Coffee", category="meals", amount=Decimal(40)),
        ],
    )

    result = evaluate_receipt(receipt, POLICY)

    assert not result.passed
    assert result.status is VerdictStatus.FLAGGED_FOR_REVIEW
    assert len(result.violations) == 1
    violation = result.violations[0]
    assert violation.rule_id == "meals.daily-cap"
    assert violation.rule_type == "category_cap"
    assert violation.amount == Decimal(80)
    assert violation.limit == Decimal(75)
    assert result.to_verdict().rule_ids == ["meals.daily-cap"]


def test_non_reimbursable_item_denies_and_links_rule() -> None:
    receipt = Receipt(
        line_items=[
            LineItem(description="Glass of WINE", amount=Decimal("14.50"))
        ]
    )

    result = evaluate_receipt(receipt, POLICY)

    assert result.status is VerdictStatus.DENIED
    assert result.violations[0].rule_id == "alcohol.exclusion"
    assert result.violations[0].status is VerdictStatus.DENIED
    assert result.to_verdict().status is VerdictStatus.DENIED


def test_excluded_word_does_not_match_inside_another_word() -> None:
    receipt = Receipt(
        line_items=[LineItem(description="Swine sandwich", amount=Decimal(12))]
    )

    result = evaluate_receipt(receipt, POLICY)

    assert result.passed


def test_incomparable_currency_is_flagged_instead_of_compared() -> None:
    receipt = Receipt(
        currency="EUR",
        line_items=[LineItem(description="Lunch", category="meals", amount=Decimal(40))],
    )

    result = evaluate_receipt(receipt, POLICY)

    assert result.status is VerdictStatus.FLAGGED_FOR_REVIEW
    assert result.violations[0].rule_id == "meals.daily-cap"
    assert "currency conversion" in result.violations[0].message


def test_missing_line_amount_is_flagged_for_review() -> None:
    receipt = Receipt(
        currency="USD",
        line_items=[LineItem(description="Lunch", category="meals")],
    )

    result = evaluate_receipt(receipt, POLICY)

    assert result.status is VerdictStatus.FLAGGED_FOR_REVIEW
    assert result.violations[0].rule_id == "meals.daily-cap"
    assert result.violations[0].item_description == "Lunch"


CONTEXT_POLICY = parse_policy(
    """\
version: 1
rules:
  - rule_id: meal.trip-limit
    type: context_limit
    parameters:
      context: trip
      limit: 100
  - rule_id: meal.office-limit
    type: context_limit
    parameters:
      context: office
      limit: 50
  - rule_id: meal.city-limit
    type: city_daily_limit
    parameters:
      limits:
        New York: 125
        other: 75
"""
)


def test_same_meal_is_allowed_on_trip_and_denied_at_office() -> None:
    receipt = Receipt(currency="USD", total=Decimal(80))

    trip_result = evaluate_receipt(
        receipt,
        CONTEXT_POLICY,
        context=ExpenseContext(expense_type="trip", city="New York"),
    )
    office_result = evaluate_receipt(
        receipt,
        CONTEXT_POLICY,
        context=ExpenseContext(expense_type="office", city="New York"),
    )

    assert trip_result.status is VerdictStatus.APPROVED
    assert office_result.status is VerdictStatus.DENIED
    assert office_result.violations[0].rule_id == "meal.office-limit"


def test_missing_context_uses_lowest_trip_or_office_limit() -> None:
    receipt = Receipt(currency="USD", total=Decimal(80))

    result = evaluate_receipt(receipt, CONTEXT_POLICY)

    assert result.status is VerdictStatus.DENIED
    assert result.violations[0].rule_id == "meal.office-limit"
    assert result.violations[0].limit == Decimal(50)


def test_city_limit_uses_named_city_or_generic_other_limit() -> None:
    receipt = Receipt(currency="USD", total=Decimal(100))

    new_york = evaluate_receipt(
        receipt,
        CONTEXT_POLICY,
        context=ExpenseContext(expense_type="trip", city="new york"),
    )
    generic_city = evaluate_receipt(
        receipt,
        CONTEXT_POLICY,
        context=ExpenseContext(expense_type="trip", city="Boston"),
    )

    assert new_york.status is VerdictStatus.APPROVED
    assert generic_city.status is VerdictStatus.FLAGGED_FOR_REVIEW
    assert generic_city.violations[0].limit == Decimal(75)


def test_missing_city_uses_most_restrictive_city_limit() -> None:
    result = evaluate_receipt(
        Receipt(currency="USD", total=Decimal(100)), CONTEXT_POLICY
    )

    city_violation = next(
        violation
        for violation in result.violations
        if violation.rule_id == "meal.city-limit"
    )
    assert city_violation.limit == Decimal(75)
    assert city_violation.status is VerdictStatus.FLAGGED_FOR_REVIEW
