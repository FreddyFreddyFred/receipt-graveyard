"""Currency detection and deterministic conversion with a bundled rate snapshot."""

from __future__ import annotations

import json
import re
import warnings
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from types import MappingProxyType

_DEFAULT_RATES_PATH = Path(__file__).resolve().parents[3] / "data" / "exchange_rates.json"
_SYMBOL_CURRENCIES = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}


class ExchangeRateError(ValueError):
    """Raised when the configured static exchange-rate table is invalid."""


class UnsupportedCurrencyError(ValueError):
    """Raised when the requested base currency is not in the bundled table."""


class AmbiguousCurrencyError(ValueError):
    """Raised when a receipt text contains more than one currency marker."""


class UnknownCurrencyWarning(UserWarning):
    """Warn that no supported currency marker was detected and a default was used."""


@dataclass(frozen=True, slots=True)
class ExchangeRateTable:
    """Validated rates normalized to USD, plus the snapshot's provenance."""

    base_currency: str
    as_of: date
    rates_to_usd: Mapping[str, Decimal]
    minor_units: Mapping[str, int]
    source: str
    source_url: str


def load_exchange_rates(path: str | Path | None = None) -> ExchangeRateTable:
    """Load and validate the bundled or explicitly supplied JSON rate table."""
    rates_path = Path(path) if path is not None else _DEFAULT_RATES_PATH
    try:
        data = json.loads(rates_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExchangeRateError(f"could not read exchange rates from '{rates_path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ExchangeRateError("exchange-rate document must be a JSON object")
    try:
        base_currency = data["base_currency"]
        as_of = date.fromisoformat(data["as_of"])
        raw_rates = data["rates_to_usd"]
        raw_minor_units = data["minor_units"]
        source = data["source"]
        source_url = data["source_url"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ExchangeRateError(f"exchange-rate document is missing valid metadata: {exc}") from exc

    if base_currency != "USD":
        raise ExchangeRateError("rates_to_usd table must declare USD as its base currency")
    if not isinstance(raw_rates, dict) or not isinstance(raw_minor_units, dict):
        raise ExchangeRateError("rates_to_usd and minor_units must be JSON objects")

    rates: dict[str, Decimal] = {}
    for currency, value in raw_rates.items():
        if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
            raise ExchangeRateError(f"invalid currency code in rate table: {currency!r}")
        try:
            rate = Decimal(str(value))
        except InvalidOperation as exc:
            raise ExchangeRateError(f"invalid rate for {currency}") from exc
        if not rate.is_finite() or rate <= 0:
            raise ExchangeRateError(f"rate for {currency} must be a positive finite number")
        rates[currency] = rate
    if rates.get("USD") != Decimal(1):
        raise ExchangeRateError("USD must have a rate of exactly 1")

    minor_units: dict[str, int] = {}
    for currency, digits in raw_minor_units.items():
        if currency not in rates or isinstance(digits, bool) or not isinstance(digits, int):
            raise ExchangeRateError(f"invalid minor-unit precision for {currency!r}")
        if not 0 <= digits <= 4:
            raise ExchangeRateError(f"minor-unit precision for {currency} must be from 0 to 4")
        minor_units[currency] = digits
    for currency in rates:
        minor_units.setdefault(currency, 2)

    if not isinstance(source, str) or not source.strip():
        raise ExchangeRateError("exchange-rate source must be a non-empty string")
    if not isinstance(source_url, str) or not source_url.startswith("https://"):
        raise ExchangeRateError("exchange-rate source_url must use HTTPS")

    return ExchangeRateTable(
        base_currency=base_currency,
        as_of=as_of,
        rates_to_usd=MappingProxyType(rates),
        minor_units=MappingProxyType(minor_units),
        source=source,
        source_url=source_url,
    )


def detect_currency(
    text: str,
    *,
    base_currency: str = "USD",
    rates_path: str | Path | None = None,
) -> str:
    """Detect an ISO code or common symbol; warn and use the base if absent.

    ``$`` maps to USD and ``¥`` maps to JPY in this MVP. If the text contains
    conflicting markers, the function raises rather than guessing.
    """
    if not isinstance(text, str):
        raise TypeError("receipt text must be a string")
    table = load_exchange_rates(rates_path)
    default = _validate_base_currency(base_currency, table)
    detected = {currency for symbol, currency in _SYMBOL_CURRENCIES.items() if symbol in text}

    codes = "|".join(re.escape(code) for code in sorted(table.rates_to_usd, key=len, reverse=True))
    for match in re.finditer(rf"(?<![A-Za-z])(?:{codes})(?![A-Za-z])", text, re.IGNORECASE):
        detected.add(match.group(0).upper())

    if len(detected) > 1:
        raise AmbiguousCurrencyError(
            "receipt text contains conflicting currency markers: "
            + ", ".join(sorted(detected))
        )
    if detected:
        return next(iter(detected))

    warnings.warn(
        f"No supported currency marker found; assuming {default}.",
        UnknownCurrencyWarning,
        stacklevel=2,
    )
    return default


def convert_amount(
    amount: Decimal | float | str,
    currency: str | None,
    *,
    base_currency: str = "USD",
    rates_path: str | Path | None = None,
) -> Decimal:
    """Convert an amount and round it to the base currency's minor unit.

    Unknown or absent source currency falls back to the base currency with an
    ``UnknownCurrencyWarning``. All conversion rates are static and loaded from
    ``data/exchange_rates.json`` unless a path is supplied explicitly.
    """
    table = load_exchange_rates(rates_path)
    base = _validate_base_currency(base_currency, table)
    try:
        value = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid monetary amount: {amount!r}") from exc
    if not value.is_finite():
        raise ValueError("monetary amount must be finite")

    source = currency.strip().upper() if isinstance(currency, str) else ""
    if source not in table.rates_to_usd:
        warnings.warn(
            f"Unknown currency {currency!r}; assuming {base}.",
            UnknownCurrencyWarning,
            stacklevel=2,
        )
        source = base

    converted = value * table.rates_to_usd[source] / table.rates_to_usd[base]
    quantum = Decimal(1).scaleb(-table.minor_units[base])
    return converted.quantize(quantum, rounding=ROUND_HALF_UP)


def _validate_base_currency(base_currency: str, table: ExchangeRateTable) -> str:
    if not isinstance(base_currency, str):
        raise TypeError("base_currency must be an ISO currency code")
    normalized = base_currency.strip().upper()
    if normalized not in table.rates_to_usd:
        raise UnsupportedCurrencyError(
            f"base currency {normalized!r} has no bundled exchange rate"
        )
    return normalized
