"""Tests for policy YAML parsing and JSON Schema validation."""

from decimal import Decimal

import pytest
from jsonschema import Draft202012Validator

from receipt_graveyard.models.policy import PolicyRule
from receipt_graveyard.policy.parser import (
    ExpensePolicy,
    PolicyValidationError,
    load_policy,
    parse_policy,
)
from receipt_graveyard.policy.schema import POLICY_SCHEMA, SUPPORTED_RULE_TYPES

SAMPLE_POLICY = """\
version: 1
rules:
  - rule_id: meals.daily-cap
    type: category_cap
    category: meals
    parameters:
      limit: 75.00
      period: daily
  - rule_id: alcohol.exclusion
    type: non_reimbursable
    parameters:
      items: [alcohol, liquor]
  - rule_id: city.dining-cap
    type: city_daily_limit
    parameters:
      limits:
        New York: 125.00
        other: 75.00
  - rule_id: trip.meal-cap
    type: context_limit
    parameters:
      context: trip
      limit: 100.00
  - rule_id: meals.manager-approval
    type: approval_threshold
    category: meals
    parameters:
      threshold: 200.00
  - rule_id: meals.client-details
    type: client_attendee_requirement
    category: meals
    parameters:
      threshold: 100.00
      require_client_name: true
      minimum_attendees: 2
"""


def test_policy_schema_is_valid_json_schema() -> None:
    Draft202012Validator.check_schema(POLICY_SCHEMA)


def test_load_sample_policy_returns_all_typed_rule_kinds(tmp_path) -> None:
    policy_file = tmp_path / "sample_policy.yaml"
    policy_file.write_text(SAMPLE_POLICY, encoding="utf-8")

    policy = load_policy(policy_file)

    assert isinstance(policy, ExpensePolicy)
    assert policy.version == 1
    assert policy.base_currency == "USD"
    assert len(policy.rules) == len(SUPPORTED_RULE_TYPES)
    assert all(isinstance(rule, PolicyRule) for rule in policy.rules)
    assert {rule.type for rule in policy.rules} == SUPPORTED_RULE_TYPES
    assert policy.rules[0].parameters["limit"] == Decimal("75.0")


def test_parse_policy_accepts_valid_yaml() -> None:
    policy = parse_policy(SAMPLE_POLICY)

    assert policy.base_currency == "USD"
    assert policy.rules[0].category == "meals"
    assert policy.rules[0].parameters["period"] == "daily"


def test_explicit_base_currency_is_preserved() -> None:
    document = SAMPLE_POLICY.replace("version: 1", "version: 1\nbase_currency: EUR")

    assert parse_policy(document).base_currency == "EUR"


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ("version: [", "invalid policy YAML"),
        ("- not-a-policy", "policy validation failed"),
        (
            SAMPLE_POLICY.replace("period: daily", "period: hourly"),
            "policy validation failed at rules.0.parameters.period",
        ),
        (
            SAMPLE_POLICY.replace("type: category_cap", "type: unknown_rule"),
            "policy validation failed",
        ),
    ],
)
def test_invalid_policy_fails_with_actionable_message(
    document: str,
    message: str,
) -> None:
    with pytest.raises(PolicyValidationError, match=message):
        parse_policy(document)


def test_duplicate_rule_ids_are_rejected() -> None:
    duplicate_ids = SAMPLE_POLICY.replace(
        "rule_id: alcohol.exclusion", "rule_id: meals.daily-cap"
    )

    with pytest.raises(PolicyValidationError, match="rule_id values must be unique"):
        parse_policy(duplicate_ids)


def test_missing_policy_file_has_clear_error(tmp_path) -> None:
    with pytest.raises(PolicyValidationError, match="could not read policy file"):
        load_policy(tmp_path / "missing.yaml")
