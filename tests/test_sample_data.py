"""Acceptance checks for the generated sample receipt dataset."""

import json
from pathlib import Path

import cv2
import numpy as np

from receipt_graveyard.detection.duplicate import are_duplicates
from receipt_graveyard.policy.parser import load_policy
from receipt_graveyard.policy.schema import SUPPORTED_RULE_TYPES

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"
IMAGE_ROOT = DATA_ROOT / "sample_receipts"


def test_manifest_covers_all_receipts_and_at_least_three_employees() -> None:
    manifest = json.loads(
        (DATA_ROOT / "employee_manifest.json").read_text(encoding="utf-8")
    )
    employees = {employee["employee_id"] for employee in manifest["employees"]}
    receipts = manifest["receipts"]
    images = list(IMAGE_ROOT.glob("*.png"))

    assert len(employees) >= 3
    assert len(images) >= 20
    assert {record["image"] for record in receipts} == {image.name for image in images}
    assert all(record["employee_id"] in employees for record in receipts)
    assert all(record["total"] and record["currency"] for record in receipts)


def test_variants_and_currencies_are_represented() -> None:
    manifest = json.loads(
        (DATA_ROOT / "employee_manifest.json").read_text(encoding="utf-8")
    )
    records = manifest["receipts"]
    tags = {tag for record in records for tag in record["tags"]}

    assert {"clean", "faded", "rotated", "handwritten"}.issubset(tags)
    assert {"USD", "EUR", "GBP", "JPY"}.issubset(
        {record["currency"] for record in records}
    )
    for path in IMAGE_ROOT.glob("*.png"):
        decoded = cv2.imdecode(np.frombuffer(path.read_bytes(), np.uint8), cv2.IMREAD_GRAYSCALE)
        assert decoded is not None
        assert decoded.size > 0


def test_two_seeded_duplicate_pairs_are_manifested_and_detectable() -> None:
    manifest = json.loads(
        (DATA_ROOT / "employee_manifest.json").read_text(encoding="utf-8")
    )
    duplicates = [record for record in manifest["receipts"] if record["duplicate_of"]]

    assert len(duplicates) >= 2
    for duplicate in duplicates:
        duplicate_path = IMAGE_ROOT / duplicate["image"]
        source_path = IMAGE_ROOT / duplicate["duplicate_of"]
        duplicate_image = cv2.imdecode(
            np.frombuffer(duplicate_path.read_bytes(), np.uint8), cv2.IMREAD_GRAYSCALE
        )
        source_image = cv2.imdecode(
            np.frombuffer(source_path.read_bytes(), np.uint8), cv2.IMREAD_GRAYSCALE
        )
        assert are_duplicates(source_image, duplicate_image)
    exact_pair = next(record for record in duplicates if "exact_duplicate" in record["tags"])
    assert (IMAGE_ROOT / exact_pair["image"]).read_bytes() == (
        IMAGE_ROOT / exact_pair["duplicate_of"]
    ).read_bytes()


def test_sample_policy_loads_all_supported_rule_types() -> None:
    policy = load_policy(DATA_ROOT / "sample_policy.yaml")

    assert policy.version == 1
    assert {rule.type for rule in policy.rules} == SUPPORTED_RULE_TYPES
