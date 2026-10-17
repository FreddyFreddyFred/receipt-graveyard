"""Tests for environment-configurable JSON logging."""

import json
from io import StringIO

import pytest

from receipt_graveyard.utils.logging import (
    LOG_LEVEL_ENV,
    configure_logging,
    get_logger,
)


def test_debug_info_and_error_events_are_json_with_context(monkeypatch) -> None:
    output = StringIO()
    monkeypatch.setenv(LOG_LEVEL_ENV, "debug")
    configure_logging(stream=output)
    logger = get_logger("receipt-test")

    logger.debug("image loaded", receipt_id="receipt-1")
    logger.info("receipt parsed", item_count=3)
    logger.error("receipt failed", error_code="bad-image")

    entries = [json.loads(line) for line in output.getvalue().splitlines()]
    assert [entry["level"] for entry in entries] == ["debug", "info", "error"]
    assert [entry["event"] for entry in entries] == [
        "image loaded",
        "receipt parsed",
        "receipt failed",
    ]
    assert entries[0]["logger"] == "receipt-test"
    assert entries[0]["receipt_id"] == "receipt-1"
    assert all("timestamp" in entry for entry in entries)


def test_log_level_environment_variable_filters_lower_levels(monkeypatch) -> None:
    output = StringIO()
    monkeypatch.setenv(LOG_LEVEL_ENV, "ERROR")
    configure_logging(stream=output)
    logger = get_logger()

    logger.debug("hidden debug")
    logger.info("hidden info")
    logger.error("visible error")

    entries = [json.loads(line) for line in output.getvalue().splitlines()]
    assert len(entries) == 1
    assert entries[0]["event"] == "visible error"


def test_unknown_environment_level_fails_with_available_names(monkeypatch) -> None:
    monkeypatch.setenv(LOG_LEVEL_ENV, "TRACE")

    with pytest.raises(ValueError, match="unsupported log level.*DEBUG"):
        configure_logging(stream=StringIO())
