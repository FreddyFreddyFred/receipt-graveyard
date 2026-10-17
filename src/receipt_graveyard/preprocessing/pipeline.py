"""Configurable receipt image preprocessing pipeline."""

from dataclasses import dataclass

import numpy as np

from receipt_graveyard.preprocessing.transforms import (
    binarize,
    crop_borders,
    denoise,
    deskew,
    enhance_contrast,
    to_grayscale,
)


@dataclass(frozen=True, slots=True)
class PreprocessingConfig:
    """Toggle each cleanup transform independently."""

    deskew: bool = True
    denoise: bool = True
    enhance_contrast: bool = True
    binarize: bool = True
    crop_borders: bool = True


def preprocess_image(
    image: np.ndarray,
    config: PreprocessingConfig | None = None,
) -> np.ndarray:
    """Normalize a grayscale, BGR, or BGRA receipt image for OCR."""
    settings = config or PreprocessingConfig()
    processed = to_grayscale(image)

    if settings.deskew:
        processed = deskew(processed)
    if settings.denoise:
        processed = denoise(processed)
    if settings.enhance_contrast:
        processed = enhance_contrast(processed)
    if settings.binarize:
        processed = binarize(processed)
    if settings.crop_borders:
        processed = crop_borders(processed)

    return processed
