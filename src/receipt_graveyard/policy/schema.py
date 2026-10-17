"""JSON Schema for version 1 expense policies."""

from jsonschema import Draft202012Validator

SUPPORTED_RULE_TYPES = frozenset(
    {
        "category_cap",
        "non_reimbursable",
        "city_daily_limit",
        "context_limit",
        "approval_threshold",
        "client_attendee_requirement",
    }
)

_CURRENCY = {"type": "string", "pattern": "^[A-Z]{3}$"}
_POSITIVE_AMOUNT = {"type": "number", "exclusiveMinimum": 0}
_NON_NEGATIVE_AMOUNT = {"type": "number", "minimum": 0}


def _parameters(
    required: list[str],
    properties: dict[str, dict[str, object]],
    *,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "type": "object",
        "required": required,
        "properties": {
            **properties,
            "currency": _CURRENCY,
        },
        "additionalProperties": False,
        **(extra or {}),
    }


_RULE_CONDITIONS = [
    {
        "if": {"properties": {"type": {"const": "category_cap"}}},
        "then": {
            "required": ["category"],
            "properties": {
                "parameters": _parameters(
                    ["limit", "period"],
                    {
                        "limit": _POSITIVE_AMOUNT,
                        "period": {"enum": ["daily", "monthly", "trip"]},
                    },
                )
            },
        },
    },
    {
        "if": {"properties": {"type": {"const": "non_reimbursable"}}},
        "then": {
            "properties": {
                "parameters": _parameters(
                    ["items"],
                    {
                        "items": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string", "minLength": 1},
                        }
                    },
                )
            }
        },
    },
    {
        "if": {"properties": {"type": {"const": "city_daily_limit"}}},
        "then": {
            "properties": {
                "parameters": _parameters(
                    ["limits"],
                    {
                        "limits": {
                            "type": "object",
                            "minProperties": 1,
                            "additionalProperties": _POSITIVE_AMOUNT,
                        }
                    },
                )
            }
        },
    },
    {
        "if": {"properties": {"type": {"const": "context_limit"}}},
        "then": {
            "properties": {
                "parameters": _parameters(
                    ["context", "limit"],
                    {
                        "context": {"enum": ["trip", "office"]},
                        "limit": _POSITIVE_AMOUNT,
                    },
                )
            }
        },
    },
    {
        "if": {"properties": {"type": {"const": "approval_threshold"}}},
        "then": {
            "required": ["category"],
            "properties": {
                "parameters": _parameters(
                    ["threshold"], {"threshold": _NON_NEGATIVE_AMOUNT}
                )
            },
        },
    },
    {
        "if": {
            "properties": {
                "type": {"const": "client_attendee_requirement"}
            }
        },
        "then": {
            "required": ["category"],
            "properties": {
                "parameters": _parameters(
                    ["threshold"],
                    {
                        "threshold": _NON_NEGATIVE_AMOUNT,
                        "require_client_name": {"type": "boolean"},
                        "minimum_attendees": {"type": "integer", "minimum": 1},
                    },
                    extra={
                        "anyOf": [
                            {"required": ["require_client_name"]},
                            {"required": ["minimum_attendees"]},
                        ]
                    },
                )
            },
        },
    },
]


POLICY_SCHEMA: dict[str, object] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://receipt-graveyard.local/schemas/policy-v1.json",
    "title": "Receipt Graveyard expense policy",
    "type": "object",
    "required": ["version", "rules"],
    "properties": {
        "version": {"const": 1},
        "base_currency": {**_CURRENCY, "default": "USD"},
        "rules": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["rule_id", "type", "parameters"],
                "properties": {
                    "rule_id": {"type": "string", "minLength": 1},
                    "type": {"enum": sorted(SUPPORTED_RULE_TYPES)},
                    "category": {"type": "string", "minLength": 1},
                    "parameters": {"type": "object"},
                    "description": {"type": "string"},
                },
                "additionalProperties": False,
                "allOf": _RULE_CONDITIONS,
            },
        },
    },
    "additionalProperties": False,
}

POLICY_VALIDATOR = Draft202012Validator(POLICY_SCHEMA)
POLICY_VALIDATOR.check_schema(POLICY_SCHEMA)
