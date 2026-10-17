"""SQLite repository for receipt, employee, and verdict records."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from receipt_graveyard.models.employee import Employee
from receipt_graveyard.models.receipt import Receipt
from receipt_graveyard.models.verdict import Verdict


class ReceiptRepository:
    """Persist project models using one SQLite transaction per write.

    ``initialize`` applies the idempotent initial migration. Monetary values are
    stored as decimal text, and every write and its corresponding audit event
    commit or roll back together.
    """

    def __init__(self, database_path: str | Path) -> None:
        requested_path = str(database_path)
        self._memory_anchor: sqlite3.Connection | None = None
        if requested_path == ":memory:":
            self._database = f"file:receipt-graveyard-{uuid4().hex}?mode=memory&cache=shared"
            self._uri = True
            self._memory_anchor = self._connect()
        else:
            self._database = str(Path(database_path))
            self._uri = False

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database, uri=self._uri)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        """Apply the initial schema migration; safe to call more than once."""
        migration = Path(__file__).with_name("migrations") / "001_initial.sql"
        if not self._uri:
            Path(self._database).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.executescript(migration.read_text(encoding="utf-8"))

    def close(self) -> None:
        """Release the anchor connection used to keep an in-memory DB alive."""
        if self._memory_anchor is not None:
            self._memory_anchor.close()
            self._memory_anchor = None

    @staticmethod
    def _json(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _decimal_text(value: Decimal | None) -> str | None:
        return None if value is None else format(value, "f")

    @classmethod
    def _receipt_values(cls, receipt: Receipt) -> tuple[object, ...]:
        line_items = [item.model_dump(mode="json") for item in receipt.line_items]
        return (
            str(receipt.id),
            receipt.employee_id,
            receipt.vendor,
            receipt.date.isoformat() if receipt.date is not None else None,
            cls._decimal_text(receipt.total),
            receipt.currency,
            cls._json(line_items),
            cls._decimal_text(receipt.tax),
            cls._decimal_text(receipt.tip),
        )

    @classmethod
    def _receipt_from_row(cls, row: sqlite3.Row) -> Receipt:
        return Receipt.model_validate(
            {
                "id": row["receipt_id"],
                "employee_id": row["employee_id"],
                "vendor": row["vendor"],
                "date": row["receipt_date"],
                "total": row["total"],
                "currency": row["currency"],
                "line_items": json.loads(row["line_items_json"]),
                "tax": row["tax"],
                "tip": row["tip"],
            }
        )

    @staticmethod
    def _write_audit(
        connection: sqlite3.Connection,
        *,
        entity_type: str,
        entity_id: str,
        action: str,
        receipt_id: str | None = None,
        details: object | None = None,
    ) -> None:
        details_json = ReceiptRepository._json({} if details is None else details)
        connection.execute(
            """INSERT INTO audit_log
               (entity_type, entity_id, receipt_id, action, details_json)
               VALUES (?, ?, ?, ?, ?)""",
            (entity_type, entity_id, receipt_id, action, details_json),
        )

    def insert_employee(self, employee: Employee) -> Employee:
        with self._transaction() as connection:
            connection.execute(
                """INSERT INTO employees
                   (employee_id, name, department, trip_id, city)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    employee.employee_id,
                    employee.name,
                    employee.department,
                    employee.trip_id,
                    employee.city,
                ),
            )
            self._write_audit(
                connection,
                entity_type="employee",
                entity_id=employee.employee_id,
                action="created",
            )
        return employee

    def get_employee(self, employee_id: str) -> Employee | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT employee_id, name, department, trip_id, city "
                "FROM employees WHERE employee_id = ?",
                (employee_id,),
            ).fetchone()
        return None if row is None else Employee.model_validate(dict(row))

    def update_employee(self, employee: Employee) -> bool:
        with self._transaction() as connection:
            cursor = connection.execute(
                """UPDATE employees
                   SET name = ?, department = ?, trip_id = ?, city = ?
                   WHERE employee_id = ?""",
                (
                    employee.name,
                    employee.department,
                    employee.trip_id,
                    employee.city,
                    employee.employee_id,
                ),
            )
            if cursor.rowcount:
                self._write_audit(
                    connection,
                    entity_type="employee",
                    entity_id=employee.employee_id,
                    action="updated",
                )
        return bool(cursor.rowcount)

    def delete_employee(self, employee_id: str) -> bool:
        with self._transaction() as connection:
            cursor = connection.execute(
                "SELECT 1 FROM employees WHERE employee_id = ?", (employee_id,)
            )
            if cursor.fetchone() is None:
                return False
            self._write_audit(
                connection,
                entity_type="employee",
                entity_id=employee_id,
                action="deleted",
            )
            connection.execute(
                "DELETE FROM employees WHERE employee_id = ?", (employee_id,)
            )
        return True

    def insert_receipt(self, receipt: Receipt) -> Receipt:
        with self._transaction() as connection:
            connection.execute(
                """INSERT INTO receipts
                   (receipt_id, employee_id, vendor, receipt_date, total, currency,
                    line_items_json, tax, tip)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                self._receipt_values(receipt),
            )
            self._write_audit(
                connection,
                entity_type="receipt",
                entity_id=str(receipt.id),
                receipt_id=str(receipt.id),
                action="created",
            )
        return receipt

    def get_receipt(self, receipt_id: UUID | str) -> Receipt | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM receipts WHERE receipt_id = ?", (str(receipt_id),)
            ).fetchone()
        return None if row is None else self._receipt_from_row(row)

    def update_receipt(self, receipt: Receipt) -> bool:
        values = self._receipt_values(receipt)
        with self._transaction() as connection:
            cursor = connection.execute(
                """UPDATE receipts SET
                       employee_id = ?, vendor = ?, receipt_date = ?, total = ?,
                       currency = ?, line_items_json = ?, tax = ?, tip = ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE receipt_id = ?""",
                (*values[1:], values[0]),
            )
            if cursor.rowcount:
                self._write_audit(
                    connection,
                    entity_type="receipt",
                    entity_id=str(receipt.id),
                    receipt_id=str(receipt.id),
                    action="updated",
                )
        return bool(cursor.rowcount)

    def delete_receipt(self, receipt_id: UUID | str) -> bool:
        receipt_key = str(receipt_id)
        with self._transaction() as connection:
            if connection.execute(
                "SELECT 1 FROM receipts WHERE receipt_id = ?", (receipt_key,)
            ).fetchone() is None:
                return False
            self._write_audit(
                connection,
                entity_type="receipt",
                entity_id=receipt_key,
                receipt_id=receipt_key,
                action="deleted",
            )
            connection.execute(
                "DELETE FROM receipts WHERE receipt_id = ?", (receipt_key,)
            )
        return True

    def insert_verdict(self, verdict: Verdict) -> Verdict:
        receipt_id = str(verdict.receipt_id)
        with self._transaction() as connection:
            connection.execute(
                """INSERT INTO verdicts
                   (receipt_id, status, reasons_json, rule_ids_json)
                   VALUES (?, ?, ?, ?)""",
                (
                    receipt_id,
                    verdict.status.value,
                    self._json(verdict.reasons),
                    self._json(verdict.rule_ids),
                ),
            )
            self._write_audit(
                connection,
                entity_type="verdict",
                entity_id=receipt_id,
                receipt_id=receipt_id,
                action="created",
            )
        return verdict

    def get_verdict(self, receipt_id: UUID | str) -> Verdict | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM verdicts WHERE receipt_id = ?", (str(receipt_id),)
            ).fetchone()
        if row is None:
            return None
        return Verdict.model_validate(
            {
                "receipt_id": row["receipt_id"],
                "status": row["status"],
                "reasons": json.loads(row["reasons_json"]),
                "rule_ids": json.loads(row["rule_ids_json"]),
            }
        )

    def update_verdict(self, verdict: Verdict) -> bool:
        receipt_id = str(verdict.receipt_id)
        with self._transaction() as connection:
            cursor = connection.execute(
                """UPDATE verdicts
                   SET status = ?, reasons_json = ?, rule_ids_json = ?
                   WHERE receipt_id = ?""",
                (
                    verdict.status.value,
                    self._json(verdict.reasons),
                    self._json(verdict.rule_ids),
                    receipt_id,
                ),
            )
            if cursor.rowcount:
                self._write_audit(
                    connection,
                    entity_type="verdict",
                    entity_id=receipt_id,
                    receipt_id=receipt_id,
                    action="updated",
                )
        return bool(cursor.rowcount)

    def delete_verdict(self, receipt_id: UUID | str) -> bool:
        receipt_key = str(receipt_id)
        with self._transaction() as connection:
            if connection.execute(
                "SELECT 1 FROM verdicts WHERE receipt_id = ?", (receipt_key,)
            ).fetchone() is None:
                return False
            self._write_audit(
                connection,
                entity_type="verdict",
                entity_id=receipt_key,
                receipt_id=receipt_key,
                action="deleted",
            )
            connection.execute(
                "DELETE FROM verdicts WHERE receipt_id = ?", (receipt_key,)
            )
        return True
