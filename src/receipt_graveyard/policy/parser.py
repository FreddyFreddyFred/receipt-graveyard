"""Safe YAML loading and validation for expense policy documents."""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from jsonschema.exceptions import ValidationError
from pydantic import ValidationError as ModelValidationError

from receipt_graveyard.models.policy import PolicyRule
from receipt_graveyard.policy.schema import POLICY_VALIDATOR


class PolicyValidationError(ValueError):
    """Raised when a policy cannot be parsed or fails its schema."""


@dataclass(frozen=True, slots=True)
class ExpensePolicy:
    """A validated policy document and its typed rules."""

    version: int
    base_currency: str
    rules: tuple[PolicyRule, ...]


def _to_decimal_values(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, list):
        return [_to_decimal_values(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_decimal_values(item) for key, item in value.items()}
    return value


def _schema_error_message(error: ValidationError) -> str:
    while error.context:
        error = max(error.context, key=lambda candidate: len(candidate.absolute_path))
    location = ".".join(str(part) for part in error.absolute_path) or "<root>"
    return f"policy validation failed at {location}: {error.message}"


def parse_policy(document: str) -> ExpensePolicy:
    """Parse a YAML policy string and return typed policy rules."""
    try:
        data = yaml.safe_load(document)
    except yaml.YAMLError as exc:
        detail = getattr(exc, "problem", None) or str(exc).splitlines()[0]
        raise PolicyValidationError(f"invalid policy YAML: {detail}") from exc

    errors = sorted(
        POLICY_VALIDATOR.iter_errors(data),
        key=lambda error: (len(error.absolute_path), list(map(str, error.absolute_path))),
    )
    if errors:
        raise PolicyValidationError(_schema_error_message(errors[0]))

    rule_ids = [rule["rule_id"] for rule in data["rules"]]
    if len(rule_ids) != len(set(rule_ids)):
        raise PolicyValidationError("policy validation failed: rule_id values must be unique")

    try:
        rules = tuple(
            PolicyRule.model_validate(
                {**rule, "parameters": _to_decimal_values(rule["parameters"])}
            )
            for rule in data["rules"]
        )
    except ModelValidationError as exc:
        raise PolicyValidationError(f"policy validation failed: {exc}") from exc

    return ExpensePolicy(
        version=data["version"],
        base_currency=data.get("base_currency", "USD"),
        rules=rules,
    )


def load_policy(path: str | Path) -> ExpensePolicy:
    """Read and parse a UTF-8 YAML policy file."""
    policy_path = Path(path)
    try:
        document = policy_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PolicyValidationError(
            f"could not read policy file '{policy_path}': {exc.strerror or exc}"
        ) from exc
    return parse_policy(document)
