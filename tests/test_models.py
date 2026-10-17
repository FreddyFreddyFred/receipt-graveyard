"""Serialization and validation tests for the core Pydantic models."""

from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import BaseModel, ValidationError

from receipt_graveyard.models.employee import Employee
from receipt_graveyard.models.policy import PolicyRule
from receipt_graveyard.models.receipt import LineItem, Receipt
from receipt_graveyard.models.verdict import Verdict, VerdictStatus


@pytest.mark.parametrize(
    "instance",
    [
        LineItem(
            description="Coffee",
            quantity=Decimal(2),
            unit_price=Decimal("3.50"),
            amount=Decimal("7.00"),
            category="meals",
        ),
        Receipt(
            id=UUID("27bb641e-3113-4b94-a778-ec981ea26016"),
            employee_id="employee-001",
            vendor="Cafe Example",
            date=date(2026, 1, 15),
            total=Decimal("7.00"),
            currency="USD",
            line_items=[LineItem(description="Coffee", amount=Decimal("7.00"))],
            tax=Decimal("0.50"),
        ),
        Verdict(
            receipt_id=UUID("27bb641e-3113-4b94-a778-ec981ea26016"),
            status=VerdictStatus.APPROVED,
            reasons=["Within policy limits."],
            rule_ids=["meal-cap"],
        ),
        Employee(
            employee_id="employee-001",
            name="Example Employee",
            department="Finance",
            trip_id="trip-001",
            city="New York",
        ),
        PolicyRule(
            rule_id="meal-cap",
            type="category_cap",
            category="meals",
            parameters={"limit": 25, "currency": "USD"},
            description="Maximum reimbursable meal amount.",
        ),
    ],
    ids=["line-item", "receipt", "verdict", "employee", "policy-rule"],
)
def test_models_round_trip_through_json(instance: BaseModel) -> None:
    restored = type(instance).model_validate_json(instance.model_dump_json())

    assert restored == instance


@pytest.mark.parametrize(
    ("model", "required_fields"),
    [
        (LineItem, ["description"]),
        (Employee, ["employee_id"]),
        (PolicyRule, ["rule_id", "type"]),
        (Verdict, ["receipt_id", "status"]),
    ],
    ids=["line-item", "employee", "policy-rule", "verdict"],
)
def test_missing_required_fields_raise_validation_error(
    model: type[BaseModel], required_fields: list[str]
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        model.model_validate({})

    missing_fields = {error["loc"][0] for error in exc_info.value.errors()}
    assert set(required_fields).issubset(missing_fields)


def test_receipt_optional_fields_default_to_none() -> None:
    receipt = Receipt()

    assert receipt.vendor is None
    assert receipt.date is None
    assert receipt.total is None
    assert receipt.currency is None
    assert receipt.employee_id is None
    assert receipt.tax is None
    assert receipt.tip is None
    assert receipt.line_items == []
