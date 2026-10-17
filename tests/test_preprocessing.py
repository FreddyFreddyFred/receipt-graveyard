"""Tests for deskewing, faded-image enhancement, and transform controls."""

import cv2
import numpy as np
import pytest

from receipt_graveyard.preprocessing import pipeline
from receipt_graveyard.preprocessing.pipeline import (
    PreprocessingConfig,
    preprocess_image,
)
from receipt_graveyard.preprocessing.transforms import estimate_skew_angle


def make_rotated_faded_receipt() -> np.ndarray:
    """Build a deterministic receipt-like image without external test data."""
    receipt = np.full((600, 400), 255, dtype=np.uint8)
    cv2.rectangle(receipt, (25, 25), (375, 575), 230, thickness=2)
    for index, y_position in enumerate(range(90, 530, 55), start=1):
        cv2.putText(
            receipt,
            f"ITEM {index} $12.50",
            (50, y_position),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            100,
            2,
            cv2.LINE_AA,
        )

    rotation = cv2.getRotationMatrix2D((200, 300), 7.0, 1.0)
    rotated = cv2.warpAffine(
        receipt,
        rotation,
        (400, 600),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )
    white = np.full_like(rotated, 255)
    return cv2.addWeighted(rotated, 0.25, white, 0.75, 0)


def test_rotated_receipt_is_deskewed_without_clipping() -> None:
    image = make_rotated_faded_receipt()
    before_angle = estimate_skew_angle(image)

    processed = preprocess_image(image)
    after_angle = estimate_skew_angle(processed)

    assert abs(before_angle) >= 4.0
    assert abs(after_angle) < 1.0
    assert processed.size > 0
    assert processed.shape[0] > 0 and processed.shape[1] > 0


def test_faded_receipt_is_enhanced_and_binarized() -> None:
    image = make_rotated_faded_receipt()

    processed = preprocess_image(image)

    assert int(image.min()) > 0
    assert int(processed.min()) == 0
    assert int(processed.max()) == 255


@pytest.mark.parametrize(
    "disabled_transform",
    ["deskew", "denoise", "enhance_contrast", "binarize", "crop_borders"],
)
def test_each_transform_can_be_disabled(
    monkeypatch: pytest.MonkeyPatch,
    disabled_transform: str,
) -> None:
    def fail_if_called(image: np.ndarray) -> np.ndarray:
        raise AssertionError(f"disabled transform {disabled_transform} was called")

    monkeypatch.setattr(pipeline, disabled_transform, fail_if_called)
    disabled_options = {
        name: False
        for name in (
            "deskew",
            "denoise",
            "enhance_contrast",
            "binarize",
            "crop_borders",
        )
    }
    config = PreprocessingConfig(**disabled_options)
    image = np.full((20, 20), 255, dtype=np.uint8)

    processed = preprocess_image(image, config)

    assert np.array_equal(processed, image)


def test_invalid_empty_image_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        preprocess_image(np.empty((0, 0), dtype=np.uint8))
