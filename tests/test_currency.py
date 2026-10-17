"""Tests for currency-marker detection and static-rate conversion."""

from decimal import Decimal
from pathlib import Path

import pytest

from receipt_graveyard.extraction.currency import (
    AmbiguousCurrencyError,
    ExchangeRateError,
    UnknownCurrencyWarning,
    UnsupportedCurrencyError,
    convert_amount,
    detect_currency,
    load_exchange_rates,
)

ROOT = Path(__file__).resolve().parents[1]
RATES_PATH = ROOT / "data" / "exchange_rates.json"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("TOTAL $12.50", "USD"),
        ("TOTAL €12.50", "EUR"),
        ("TOTAL £12.50", "GBP"),
        ("TOTAL ¥1200", "JPY"),
        ("TOTAL cAd 12.50", "CAD"),
        ("Paid with JPY 1200", "JPY"),
    ],
)
def test_detects_symbols_and_supported_iso_codes(text: str, expected: str) -> None:
    assert detect_currency(text) == expected


def test_unknown_currency_defaults_to_base_with_warning() -> None:
    with pytest.warns(UnknownCurrencyWarning, match="assuming EUR"):
        detected = detect_currency("TOTAL 25.00", base_currency="EUR")

    assert detected == "EUR"


def test_conflicting_currency_markers_are_rejected() -> None:
    with pytest.raises(AmbiguousCurrencyError, match="conflicting currency markers"):
        detect_currency("TOTAL €10.00 / USD 10.90")


@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [
        ("100", "GBP", Decimal("133.35")),
        ("100", "EUR", Decimal("112.53")),
        ("10000", "JPY", Decimal("63.28")),
    ],
)
def test_converts_gbp_eur_and_jpy_to_usd(
    amount: str, currency: str, expected: Decimal
) -> None:
    assert convert_amount(amount, currency) == expected


def test_conversion_supports_a_non_usd_base_currency() -> None:
    assert convert_amount("112.53", "USD", base_currency="EUR") == Decimal("100.00")
    assert convert_amount("12.50", "USD", base_currency="JPY") == Decimal(1975)


def test_unknown_source_currency_defaults_to_base_with_warning() -> None:
    with pytest.warns(UnknownCurrencyWarning, match="Unknown currency"):
        converted = convert_amount("12.50", "XYZ")

    assert converted == Decimal("12.50")


def test_rate_table_has_provenance_and_supported_currencies() -> None:
    rates = load_exchange_rates(RATES_PATH)

    assert rates.base_currency == "USD"
    assert rates.as_of.isoformat() == "2026-10-16"
    assert {"USD", "EUR", "GBP", "JPY"}.issubset(rates.rates_to_usd)
    assert rates.source_url.startswith("https://")


def test_invalid_base_currency_and_amount_are_rejected() -> None:
    with pytest.raises(UnsupportedCurrencyError, match="no bundled exchange rate"):
        convert_amount("10", "USD", base_currency="XYZ")
    with pytest.raises(ValueError, match="must be finite"):
        convert_amount("NaN", "USD")


def test_invalid_rate_table_has_actionable_error(tmp_path: Path) -> None:
    rate_file = tmp_path / "exchange_rates.json"
    rate_file.write_text("{invalid", encoding="utf-8")

    with pytest.raises(ExchangeRateError, match="could not read exchange rates"):
        load_exchange_rates(rate_file)
