"""Tests for receipt image perceptual hashing."""

import cv2
import numpy as np
import pytest

from receipt_graveyard.detection.duplicate import (
    are_duplicates,
    hamming_distance,
    perceptual_hash,
)


def _receipt_image(
    header: str = "CAFE CENTRAL",
    item: str = "LATTE 5.00",
    total: str = "TOTAL 5.00",
) -> np.ndarray:
    image = np.full((420, 280), 255, dtype=np.uint8)
    cv2.putText(image, header, (18, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.65, 0, 2)
    cv2.line(image, (15, 100), (265, 100), 0, 2)
    cv2.putText(image, item, (18, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.65, 0, 2)
    cv2.putText(image, total, (18, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.65, 0, 2)
    return image


def test_identical_image_is_duplicate() -> None:
    image = _receipt_image()

    assert are_duplicates(image, image.copy(), threshold=0)
    assert hamming_distance(perceptual_hash(image), perceptual_hash(image.copy())) == 0


def test_resized_and_jpeg_recompressed_image_is_duplicate() -> None:
    image = _receipt_image()
    resized = cv2.resize(image, (140, 210), interpolation=cv2.INTER_AREA)
    success, encoded = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 72])
    assert success
    recompressed = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE)

    assert are_duplicates(image, recompressed)


def test_visually_different_receipt_is_not_duplicate() -> None:
    cafe_receipt = _receipt_image()
    hardware_receipt = _receipt_image(
        header="HARDWARE STORE",
        item="HAMMER 29.99",
        total="TOTAL 29.99",
    )

    assert not are_duplicates(cafe_receipt, hardware_receipt)


@pytest.mark.parametrize("threshold", [-1, 65])
def test_invalid_duplicate_threshold_is_rejected(threshold: int) -> None:
    image = _receipt_image()

    with pytest.raises(ValueError, match="threshold must be between"):
        are_duplicates(image, image, threshold=threshold)


def test_hamming_distance_rejects_out_of_range_hash() -> None:
    with pytest.raises(ValueError, match="hash_a must be between"):
        hamming_distance(1 << 64, 0)
