"""Configurable keyword-based classification for receipt items and vendors."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_RULES_PATH = Path(__file__).resolve().parents[3] / "data" / "category_rules.json"


class CategoryRulesError(ValueError):
    """Raised when the category keyword configuration is invalid."""


@dataclass(frozen=True, slots=True)
class CategoryRule:
    """One ordered category and its matching phrases."""

    category: str
    keywords: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CategoryRules:
    """Validated, ordered category rules and the unknown-result category."""

    unknown_category: str
    rules: tuple[CategoryRule, ...]


def load_category_rules(path: str | Path | None = None) -> CategoryRules:
    """Load the default or caller-supplied version 1 keyword rules JSON file."""
    rules_path = Path(path) if path is not None else _DEFAULT_RULES_PATH
    try:
        document = json.loads(rules_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CategoryRulesError(f"could not read category rules from '{rules_path}': {exc}") from exc

    if (
        not isinstance(document, dict)
        or isinstance(document.get("version"), bool)
        or document.get("version") != 1
    ):
        raise CategoryRulesError("category rules must be a version 1 JSON object")
    unknown_category = document.get("unknown_category")
    if not isinstance(unknown_category, str) or not unknown_category.strip():
        raise CategoryRulesError("unknown_category must be a non-empty string")
    raw_rules = document.get("rules")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise CategoryRulesError("rules must be a non-empty array")

    parsed: list[CategoryRule] = []
    for index, raw_rule in enumerate(raw_rules):
        if not isinstance(raw_rule, dict):
            raise CategoryRulesError(f"rule {index} must be an object")
        category = raw_rule.get("category")
        keywords = raw_rule.get("keywords")
        if not isinstance(category, str) or not category.strip():
            raise CategoryRulesError(f"rule {index} needs a non-empty category")
        if not isinstance(keywords, list) or not keywords:
            raise CategoryRulesError(f"rule {index} needs a non-empty keywords array")
        if any(not isinstance(keyword, str) or not keyword.strip() for keyword in keywords):
            raise CategoryRulesError(f"rule {index} keywords must be non-empty strings")
        normalized = tuple(dict.fromkeys(" ".join(word.split()) for word in keywords))
        parsed.append(CategoryRule(category=category.strip(), keywords=normalized))

    return CategoryRules(unknown_category=unknown_category.strip(), rules=tuple(parsed))


def classify_category(
    description: str | None = None,
    *,
    vendor: str | None = None,
    rules: CategoryRules | Mapping[str, object] | None = None,
    rules_path: str | Path | None = None,
) -> str:
    """Classify an item description, falling back to its vendor and then `other`.

    The JSON configuration is ordered: the first category rule that matches
    wins. A validated ``CategoryRules`` instance or a custom JSON path can be
    supplied so applications can change categories without editing code.
    """
    if rules is not None and rules_path is not None:
        raise ValueError("supply either rules or rules_path, not both")
    config = _coerce_rules(rules) if rules is not None else load_category_rules(rules_path)
    texts = [
        _validated_text(description, name="description"),
        _validated_text(vendor, name="vendor"),
    ]
    for text in texts:
        if not text:
            continue
        normalized_text = " ".join(text.split()).casefold()
        for rule in config.rules:
            for keyword in rule.keywords:
                pattern = rf"(?<!\w){re.escape(keyword.casefold())}(?!\w)"
                if re.search(pattern, normalized_text):
                    return rule.category
    return config.unknown_category


def _coerce_rules(rules: CategoryRules | Mapping[str, object]) -> CategoryRules:
    if isinstance(rules, CategoryRules):
        return rules
    try:
        unknown_category = rules["unknown_category"]
        raw_rules = rules["rules"]
    except KeyError as exc:
        raise CategoryRulesError(f"category rules are missing {exc.args[0]!r}") from exc
    if not isinstance(unknown_category, str) or not unknown_category.strip():
        raise CategoryRulesError("unknown_category must be a non-empty string")
    if not isinstance(raw_rules, (list, tuple)) or not raw_rules:
        raise CategoryRulesError("rules must be a non-empty array")
    parsed: list[CategoryRule] = []
    for index, raw_rule in enumerate(raw_rules):
        if not isinstance(raw_rule, Mapping):
            raise CategoryRulesError(f"rule {index} must be an object")
        category = raw_rule.get("category")
        keywords = raw_rule.get("keywords")
        if not isinstance(category, str) or not category.strip():
            raise CategoryRulesError(f"rule {index} needs a non-empty category")
        if not isinstance(keywords, (list, tuple)) or not keywords:
            raise CategoryRulesError(f"rule {index} needs a non-empty keywords array")
        if any(not isinstance(word, str) or not word.strip() for word in keywords):
            raise CategoryRulesError(f"rule {index} keywords must be non-empty strings")
        parsed.append(
            CategoryRule(
                category=category.strip(),
                keywords=tuple(dict.fromkeys(" ".join(word.split()) for word in keywords)),
            )
        )
    return CategoryRules(unknown_category=unknown_category.strip(), rules=tuple(parsed))


def _validated_text(value: str | None, *, name: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string or None")
    return value
