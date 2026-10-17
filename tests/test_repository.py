"""CRUD, transaction, and audit checks for the SQLite repository."""

import sqlite3
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from receipt_graveyard.db.repository import ReceiptRepository
from receipt_graveyard.models.employee import Employee
from receipt_graveyard.models.receipt import LineItem, Receipt
from receipt_graveyard.models.verdict import Verdict, VerdictStatus


@pytest.fixture
def database_path(tmp_path):
    return tmp_path / "receipts.sqlite3"


@pytest.fixture
def repository(database_path):
    instance = ReceiptRepository(database_path)
    instance.initialize()
    yield instance
    instance.close()


def test_employee_insert_query_update_and_delete(repository) -> None:
    employee = Employee(employee_id="employee-1", name="Alex", city="Boston")
    repository.insert_employee(employee)

    assert repository.get_employee("employee-1") == employee

    updated = employee.model_copy(update={"name": "Alex Rivera", "city": "NYC"})
    assert repository.update_employee(updated)
    assert repository.get_employee("employee-1") == updated
    assert not repository.update_employee(Employee(employee_id="missing"))
    assert repository.delete_employee("employee-1")
    assert repository.get_employee("employee-1") is None
    assert not repository.delete_employee("employee-1")


def test_receipt_insert_query_and_update_preserve_model_values(repository) -> None:
    employee = Employee(employee_id="employee-1", name="Alex")
    repository.insert_employee(employee)
    receipt = Receipt(
        employee_id=employee.employee_id,
        vendor="Cafe North",
        date=date(2026, 10, 18),
        total=Decimal("18.40"),
        currency="USD",
        line_items=[
            LineItem(
                description="Lunch",
                quantity=Decimal(2),
                unit_price=Decimal("7.20"),
                amount=Decimal("14.40"),
                category="meals",
            )
        ],
        tax=Decimal("2.00"),
        tip=Decimal("2.00"),
    )
    repository.insert_receipt(receipt)

    assert repository.get_receipt(receipt.id) == receipt

    updated = receipt.model_copy(
        update={"vendor": "Cafe North 2", "total": Decimal("19.10")}
    )
    assert repository.update_receipt(updated)
    assert repository.get_receipt(receipt.id) == updated
    missing = updated.model_copy(update={"id": uuid4()})
    assert not repository.update_receipt(missing)
    assert repository.get_receipt("missing") is None


def test_verdict_insert_query_and_update(repository) -> None:
    receipt = Receipt(total=Decimal("44.75"), currency="USD")
    repository.insert_receipt(receipt)
    verdict = Verdict(
        receipt_id=receipt.id,
        status=VerdictStatus.FLAGGED_FOR_REVIEW,
        reasons=["Needs review"],
        rule_ids=["meals.daily-cap"],
    )
    repository.insert_verdict(verdict)

    assert repository.get_verdict(receipt.id) == verdict

    updated = verdict.model_copy(
        update={"status": VerdictStatus.APPROVED, "reasons": ["Reviewed"]}
    )
    assert repository.update_verdict(updated)
    assert repository.get_verdict(receipt.id) == updated
    missing = updated.model_copy(update={"receipt_id": uuid4()})
    assert not repository.update_verdict(missing)
    assert repository.get_verdict("missing") is None


def test_receipt_deletion_cascades_verdict_and_keeps_audit(repository, database_path) -> None:
    receipt = Receipt(total=Decimal(25), currency="USD")
    repository.insert_receipt(receipt)
    repository.insert_verdict(
        Verdict(receipt_id=receipt.id, status=VerdictStatus.APPROVED)
    )

    assert repository.delete_receipt(receipt.id)
    assert repository.get_receipt(receipt.id) is None
    assert repository.get_verdict(receipt.id) is None
    assert not repository.delete_receipt(receipt.id)

    with sqlite3.connect(database_path) as connection:
        audit_rows = connection.execute(
            "SELECT action, receipt_id FROM audit_log "
            "WHERE entity_type = 'receipt' AND entity_id = ? ORDER BY audit_id",
            (str(receipt.id),),
        ).fetchall()
    assert [action for action, _ in audit_rows] == ["created", "deleted"]
    assert all(receipt_id is None for _, receipt_id in audit_rows)


def test_entity_write_rolls_back_if_audit_write_fails(repository, database_path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """CREATE TRIGGER reject_receipt_audit
               BEFORE INSERT ON audit_log
               WHEN NEW.entity_type = 'receipt'
               BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END"""
        )

    receipt = Receipt(total=Decimal(12), currency="USD")
    with pytest.raises(sqlite3.IntegrityError, match="audit unavailable"):
        repository.insert_receipt(receipt)

    assert repository.get_receipt(receipt.id) is None


def test_in_memory_repository_keeps_database_between_operations() -> None:
    repository = ReceiptRepository(":memory:")
    try:
        repository.initialize()
        employee = Employee(employee_id="memory-employee", name="In Memory")
        repository.insert_employee(employee)
        assert repository.get_employee(employee.employee_id) == employee
    finally:
        repository.close()
