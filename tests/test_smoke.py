"""Smoke tests for the initial project package."""

from types import ModuleType


def test_receipt_graveyard_package_imports(
    receipt_graveyard_package: ModuleType,
) -> None:
    """The package is importable through the shared pytest fixture."""
    assert receipt_graveyard_package.__name__ == "receipt_graveyard"
