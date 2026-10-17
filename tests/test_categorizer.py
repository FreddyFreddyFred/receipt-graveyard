"""Tests for configurable vendor and item categorization."""

import json
from pathlib import Path

import pytest

from receipt_graveyard.extraction.categorizer import (
    CategoryRulesError,
    classify_category,
    load_category_rules,
)

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "data" / "category_rules.json"


@pytest.mark.parametrize(
    ("vendor", "expected"),
    [
        ("Uber", "transport"),
        ("Hilton", "lodging"),
        ("Staples", "supplies"),
        ("Unknown Emporium", "other"),
    ],
)
def test_known_vendors_and_unknown_fallback(vendor: str, expected: str) -> None:
    assert classify_category(vendor=vendor) == expected


def test_item_description_takes_priority_over_vendor() -> None:
    assert classify_category("Coffee", vendor="Uber") == "meals"


def test_sample_dataset_item_keywords_use_configured_categories() -> None:
    assert classify_category("Office snacks", vendor="Corner Market") == "supplies"
    assert classify_category("First aid supplies", vendor="Community Pharmacy") == "medical"


def test_keyword_matching_uses_word_boundaries() -> None:
    assert classify_category(vendor="Cuber Analytics") == "other"


def test_custom_rules_file_changes_categories_without_code_changes(tmp_path: Path) -> None:
    rules_path = tmp_path / "custom_categories.json"
    rules_path.write_text(
        json.dumps(
            {
                "version": 1,
                "unknown_category": "misc",
                "rules": [{"category": "commute", "keywords": ["uber"]}],
            }
        ),
        encoding="utf-8",
    )

    assert classify_category(vendor="Uber", rules_path=rules_path) == "commute"
    assert classify_category(vendor="Unknown", rules_path=rules_path) == "misc"


def test_custom_rules_can_be_loaded_and_reused() -> None:
    rules = load_category_rules(RULES_PATH)

    assert classify_category("Taxi fare", rules=rules) == "transport"


def test_invalid_category_rule_file_has_clear_error(tmp_path: Path) -> None:
    rules_path = tmp_path / "invalid.json"
    rules_path.write_text('{"version": 1, "unknown_category": "other", "rules": []}', encoding="utf-8")

    with pytest.raises(CategoryRulesError, match="non-empty array"):
        load_category_rules(rules_path)


def test_rules_and_rules_path_cannot_be_supplied_together() -> None:
    rules = load_category_rules(RULES_PATH)

    with pytest.raises(ValueError, match="either rules or rules_path"):
        classify_category(vendor="Uber", rules=rules, rules_path=RULES_PATH)
