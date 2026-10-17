"""Generate the deterministic, synthetic receipt dataset used by tests."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"
IMAGE_ROOT = DATA_ROOT / "sample_receipts"

EMPLOYEES = [
    {
        "employee_id": "employee-001",
        "name": "Alex Example",
        "department": "Finance",
        "city": "New York",
        "trip_id": "trip-ny-001",
    },
    {
        "employee_id": "employee-002",
        "name": "Blair Sample",
        "department": "Engineering",
        "city": "Boston",
        "trip_id": "trip-bos-001",
    },
    {
        "employee_id": "employee-003",
        "name": "Casey Demo",
        "department": "Marketing",
        "city": "San Francisco",
        "trip_id": "trip-sf-001",
    },
]

RECEIPTS: list[dict[str, Any]] = [
    {"vendor": "Central Cafe", "date": "2026-01-05", "currency": "USD", "amount": "16.50", "item": "Coffee and sandwich", "category": "meals", "variant": "clean"},
    {"vendor": "Metro Deli", "date": "2026-01-06", "currency": "USD", "amount": "25.00", "item": "Lunch special", "category": "meals", "variant": "clean"},
    {"vendor": "Corner Market", "date": "2026-01-07", "currency": "USD", "amount": "18.75", "item": "Office snacks", "category": "supplies", "variant": "faded"},
    {"vendor": "City Cab", "date": "2026-01-08", "currency": "USD", "amount": "32.40", "item": "Taxi fare", "category": "transport", "variant": "rotated"},
    {"vendor": "Office Supply", "date": "2026-01-09", "currency": "USD", "amount": "45.19", "item": "Paper and pens", "category": "supplies", "variant": "clean"},
    {"vendor": "Lotus Bistro", "date": "2026-01-10", "currency": "EUR", "amount": "43.20", "item": "Team dinner", "category": "meals", "variant": "multi_currency"},
    {"vendor": "Northstar Hotel", "date": "2026-01-11", "currency": "USD", "amount": "148.00", "item": "One night lodging", "category": "lodging", "variant": "clean"},
    {"vendor": "Sushi House", "date": "2026-01-12", "currency": "JPY", "amount": "3200", "item": "Sushi set", "category": "meals", "variant": "multi_currency"},
    {"vendor": "Rail Ticket", "date": "2026-01-13", "currency": "EUR", "amount": "21.50", "item": "Train ticket", "category": "transport", "variant": "rotated_multi_currency"},
    {"vendor": "Green Grocer", "date": "2026-01-14", "currency": "USD", "amount": "18.22", "item": "Fruit basket", "category": "meals", "variant": "faded"},
    {"vendor": "Roastery", "date": "2026-01-15", "currency": "USD", "amount": "9.50", "item": "Coffee beans", "category": "meals", "variant": "handwritten"},
    {"vendor": "Skyline Dining", "date": "2026-01-16", "currency": "USD", "amount": "124.80", "item": "Client dinner", "category": "meals", "variant": "rotated"},
    {"vendor": "RideShare", "date": "2026-01-17", "currency": "GBP", "amount": "17.40", "item": "Ride to airport", "category": "transport", "variant": "multi_currency"},
    {"vendor": "Bookshop", "date": "2026-01-18", "currency": "USD", "amount": "27.65", "item": "Reference books", "category": "supplies", "variant": "clean"},
    {"vendor": "Tacos and Co", "date": "2026-01-19", "currency": "USD", "amount": "38.60", "item": "Team lunch", "category": "meals", "variant": "faded"},
    {"vendor": "Community Pharmacy", "date": "2026-01-20", "currency": "USD", "amount": "11.80", "item": "First aid supplies", "category": "medical", "variant": "rotated"},
    {"vendor": "Harbor Cafe", "date": "2026-02-03", "currency": "USD", "amount": "22.10", "item": "Breakfast", "category": "meals", "variant": "clean"},
    {"vendor": "Wine and Dine", "date": "2026-02-04", "currency": "USD", "amount": "117.00", "item": "Dinner and wine", "category": "meals", "variant": "clean", "line_items": [{"description": "Dinner", "amount": "89.00", "category": "meals"}, {"description": "Wine", "amount": "28.00", "category": "meals"}]},
    {"vendor": "Paper Plane Cafe", "date": "2026-02-05", "currency": "USD", "amount": "65.00", "item": "Client lunch", "category": "meals", "variant": "handwritten"},
    {"vendor": "Transit Kiosk", "date": "2026-02-06", "currency": "JPY", "amount": "900", "item": "Metro pass", "category": "transport", "variant": "faded_multi_currency"},
]


def _render_receipt(record: dict[str, Any], index: int) -> np.ndarray:
    image = np.full((760, 520), 255, dtype=np.uint8)
    rng = random.Random(index)
    handwritten = "handwritten" in record["variant"]
    font = cv2.FONT_HERSHEY_SCRIPT_COMPLEX if handwritten else cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.72 if handwritten else 0.62
    thickness = 1 if handwritten else 2

    cv2.putText(image, "THE RECEIPT GRAVEYARD", (22, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 45, 1, cv2.LINE_AA)
    cv2.putText(image, record["vendor"].upper(), (28, 90), font, scale, 18, thickness, cv2.LINE_AA)
    cv2.line(image, (20, 112), (500, 112), 70, 1, cv2.LINE_AA)
    cv2.putText(image, f"DATE: {record['date']}", (25, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.55, 20, 1, cv2.LINE_AA)
    cv2.putText(image, f"RECEIPT: RG-{index:03d}", (25, 192), cv2.FONT_HERSHEY_SIMPLEX, 0.55, 20, 1, cv2.LINE_AA)
    cv2.putText(image, "ITEM                         AMOUNT", (25, 245), cv2.FONT_HERSHEY_SIMPLEX, 0.52, 35, 1, cv2.LINE_AA)

    line_items = record.get("line_items") or [
        {"description": record["item"], "amount": record["amount"], "category": record["category"]}
    ]
    y = 292
    for item in line_items:
        jitter = rng.randint(-2, 2) if handwritten else 0
        amount = f"{record['currency']} {item['amount']}"
        cv2.putText(image, item["description"][:28], (25 + jitter, y + jitter), font, scale, 25, thickness, cv2.LINE_AA)
        cv2.putText(image, amount, (310 + jitter, y + jitter), font, scale, 25, thickness, cv2.LINE_AA)
        y += 52

    cv2.line(image, (20, 610), (500, 610), 70, 1, cv2.LINE_AA)
    cv2.putText(image, f"TOTAL  {record['currency']} {record['amount']}", (25, 665), font, 0.78 if handwritten else 0.66, 10, 2, cv2.LINE_AA)
    cv2.putText(image, "THANK YOU", (25, 710), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 65, 1, cv2.LINE_AA)

    variant = record["variant"]
    if "faded" in variant:
        image = cv2.addWeighted(image, 0.42, np.full_like(image, 255), 0.58, 0)
        noise = np.random.default_rng(index).normal(0, 2, image.shape).astype(np.int16)
        image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    if "rotated" in variant:
        angle = 3.5 if index % 2 else -4.0
        matrix = cv2.getRotationMatrix2D((260, 380), angle, 1.0)
        image = cv2.warpAffine(image, matrix, (520, 760), borderValue=255)
    return image


def _write_if_unchanged(path: Path, content: bytes) -> None:
    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError(f"refusing to overwrite user-modified sample file: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _encode_png(image: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(".png", image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    if not success:
        raise RuntimeError("OpenCV failed to encode a sample receipt")
    return encoded.tobytes()


def generate() -> None:
    """Create 20 unique synthetic receipts and two seeded duplicate images."""
    IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_receipts: list[dict[str, Any]] = []
    employee_ids = [employee["employee_id"] for employee in EMPLOYEES]

    for index, record in enumerate(RECEIPTS, start=1):
        filename = f"receipt-{index:03d}.png"
        image = _render_receipt(record, index)
        _write_if_unchanged(IMAGE_ROOT / filename, _encode_png(image))
        line_items = record.get("line_items") or [
            {"description": record["item"], "amount": record["amount"], "category": record["category"]}
        ]
        manifest_receipts.append(
            {
                "image": filename,
                "employee_id": employee_ids[(index - 1) % len(employee_ids)],
                "vendor": record["vendor"],
                "date": record["date"],
                "currency": record["currency"],
                "total": record["amount"],
                "line_items": line_items,
                "tags": [record["variant"]],
                "duplicate_of": None,
            }
        )

    exact_source = IMAGE_ROOT / "receipt-001.png"
    exact_duplicate = IMAGE_ROOT / "receipt-021-exact-duplicate.png"
    _write_if_unchanged(exact_duplicate, exact_source.read_bytes())
    manifest_receipts.append(
        {
            **manifest_receipts[0],
            "image": exact_duplicate.name,
            "employee_id": employee_ids[1],
            "tags": ["seeded_duplicate", "exact_duplicate"],
            "duplicate_of": exact_source.name,
        }
    )

    near_source = IMAGE_ROOT / "receipt-006.png"
    near_image = cv2.imdecode(np.frombuffer(near_source.read_bytes(), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    resized = cv2.resize(near_image, (416, 608), interpolation=cv2.INTER_AREA)
    success, jpeg = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 78])
    if not success:
        raise RuntimeError("OpenCV failed to encode the near-duplicate sample")
    decoded = cv2.imdecode(jpeg, cv2.IMREAD_GRAYSCALE)
    near_duplicate = IMAGE_ROOT / "receipt-022-near-duplicate.png"
    _write_if_unchanged(near_duplicate, _encode_png(decoded))
    manifest_receipts.append(
        {
            **manifest_receipts[5],
            "image": near_duplicate.name,
            "tags": ["seeded_duplicate", "near_duplicate", "multi_currency"],
            "duplicate_of": near_source.name,
        }
    )

    manifest = {
        "dataset_version": 1,
        "description": "Synthetic receipts with ground-truth fields for local tests; no real people or transaction data.",
        "employees": EMPLOYEES,
        "receipts": manifest_receipts,
    }
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _write_if_unchanged(DATA_ROOT / "employee_manifest.json", manifest_bytes)


if __name__ == "__main__":
    generate()
