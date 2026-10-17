"""Tests for per-receipt policy evaluation."""

from decimal import Decimal

from receipt_graveyard.models.receipt import LineItem, Receipt
from receipt_graveyard.models.verdict import VerdictStatus
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
