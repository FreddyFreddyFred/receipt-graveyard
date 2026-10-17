"""Shared pytest fixtures for the receipt-graveyard package."""

import importlib
from types import ModuleType

import pytest


@pytest.fixture(scope="session")
def receipt_graveyard_package() -> ModuleType:
    """Return the installed receipt-graveyard package for smoke tests."""
    return importlib.import_module("receipt_graveyard")
