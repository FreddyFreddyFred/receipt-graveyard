"""Perceptual image hashes for finding identical or near-identical receipts."""

from __future__ import annotations

import operator

import cv2
import numpy as np

from receipt_graveyard.preprocessing.transforms import to_grayscale

_DCT_SIZE = 32
_HASH_SIZE = 8
_HASH_BITS = _HASH_SIZE * _HASH_SIZE
_DEFAULT_THRESHOLD = 10


def perceptual_hash(image: np.ndarray) -> int:
    """Return a 64-bit DCT perceptual hash for a grayscale or color image.

    The image is normalized to grayscale and resized before a 2-D discrete
    cosine transform. The low-frequency coefficients encode the broad visual
    structure and are resilient to ordinary resizing and JPEG compression.
    """
    grayscale = to_grayscale(image)
    resized = cv2.resize(
        grayscale,
        (_DCT_SIZE, _DCT_SIZE),
        interpolation=cv2.INTER_AREA,
    )
    coefficients = cv2.dct(resized.astype(np.float32))[:_HASH_SIZE, :_HASH_SIZE]
    values = coefficients.reshape(-1)
    median = float(np.median(values[1:]))

    image_hash = 0
    for coefficient in values:
        image_hash = (image_hash << 1) | int(coefficient > median)
    return image_hash


def hamming_distance(hash_a: int, hash_b: int) -> int:
    """Return the differing bit count for two 64-bit perceptual hashes."""
    value_a = _validate_hash(hash_a, name="hash_a")
    value_b = _validate_hash(hash_b, name="hash_b")
    return (value_a ^ value_b).bit_count()


def are_duplicates(
    image_a: np.ndarray,
    image_b: np.ndarray,
    *,
    threshold: int = _DEFAULT_THRESHOLD,
) -> bool:
    """Return whether two images' perceptual hashes are within a bit threshold."""
    if isinstance(threshold, bool) or not isinstance(threshold, int):
        raise TypeError("threshold must be an integer")
    if not 0 <= threshold <= _HASH_BITS:
        raise ValueError(f"threshold must be between 0 and {_HASH_BITS}")
    return hamming_distance(perceptual_hash(image_a), perceptual_hash(image_b)) <= threshold


def _validate_hash(value: int, *, name: str) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a 64-bit integer")
    try:
        integer = operator.index(value)
    except TypeError as exc:
        raise TypeError(f"{name} must be a 64-bit integer") from exc
    if not 0 <= integer < 1 << _HASH_BITS:
        raise ValueError(f"{name} must be between 0 and 2**{_HASH_BITS} - 1")
    return integer
