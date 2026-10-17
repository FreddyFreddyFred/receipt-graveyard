"""SQLite schema and initial migration acceptance checks."""

import sqlite3
from pathlib import Path

import pytest

DB_DIR = Path(__file__).parents[1] / "src" / "receipt_graveyard" / "db"
EXPECTED_TABLES = {"employees", "receipts", "verdicts", "audit_log"}


@pytest.mark.parametrize(
    "sql_path",
    [DB_DIR / "schema.sql", DB_DIR / "migrations" / "001_initial.sql"],
    ids=["schema", "initial-migration"],
)
def test_schema_runs_idempotently_and_enforces_foreign_keys(sql_path: Path) -> None:
    connection = sqlite3.connect(":memory:")
    try:
        script = sql_path.read_text(encoding="utf-8")
        connection.executescript(script)
        connection.executescript(script)

        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert EXPECTED_TABLES <= tables
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO receipts (receipt_id, employee_id) VALUES (?, ?)",
                ("receipt-orphan", "missing-employee"),
            )

        connection.execute(
            "INSERT INTO employees (employee_id, name) VALUES (?, ?)",
            ("employee-1", "Example Employee"),
        )
        connection.execute(
            "INSERT INTO receipts (receipt_id, employee_id) VALUES (?, ?)",
            ("receipt-1", "employee-1"),
        )
        connection.execute(
            "INSERT INTO verdicts (receipt_id, status) VALUES (?, ?)",
            ("receipt-1", "Approved"),
        )
        connection.execute(
            "INSERT INTO audit_log (entity_type, entity_id, receipt_id, action) "
            "VALUES (?, ?, ?, ?)",
            ("receipt", "receipt-1", "receipt-1", "created"),
        )
        connection.commit()

        connection.execute("DELETE FROM receipts WHERE receipt_id = ?", ("receipt-1",))
        assert connection.execute(
            "SELECT COUNT(*) FROM verdicts WHERE receipt_id = ?", ("receipt-1",)
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT receipt_id FROM audit_log WHERE entity_id = ?", ("receipt-1",)
        ).fetchone()[0] is None
    finally:
        connection.close()
