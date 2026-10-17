"""OpenCV transforms used to normalize receipt images before OCR."""

import cv2
import numpy as np


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Return an 8-bit grayscale copy of a grayscale, BGR, or BGRA image."""
    if not isinstance(image, np.ndarray):
        raise TypeError("image must be a NumPy array")
    if image.size == 0:
        raise ValueError("image must not be empty")
    if image.dtype != np.uint8:
        raise ValueError("image must use 8-bit unsigned integer pixels")

    if image.ndim == 2:
        return image.copy()
    if image.ndim != 3:
        raise ValueError("image must be grayscale, BGR, or BGRA")
    if image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    raise ValueError("color images must have three or four channels")


def estimate_skew_angle(image: np.ndarray) -> float:
    """Return the foreground's observed skew in degrees, normalized to ±45°."""
    grayscale = to_grayscale(image)
    _, foreground = cv2.threshold(
        grayscale, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )

    minimum_line_length = max(12, grayscale.shape[1] // 20)
    line_segments = cv2.HoughLinesP(
        cv2.Canny(foreground, 50, 150),
        rho=1,
        theta=np.pi / 720,
        threshold=max(12, grayscale.shape[1] // 30),
        minLineLength=minimum_line_length,
        maxLineGap=max(5, grayscale.shape[1] // 80),
    )
    horizontal_angles: list[tuple[float, float]] = []
    if line_segments is not None:
        for segment in line_segments.reshape(-1, 4):
            x_start, y_start, x_end, y_end = segment
            delta_x = float(x_end - x_start)
            delta_y = float(y_end - y_start)
            length = float(np.hypot(delta_x, delta_y))
            angle = float(np.degrees(np.arctan2(delta_y, delta_x)))
            angle = ((angle + 90.0) % 180.0) - 90.0
            if abs(angle) <= 25.0 and length >= minimum_line_length:
                horizontal_angles.append((angle, length))

    if horizontal_angles:
        horizontal_angles.sort(key=lambda item: item[0])
        midpoint = sum(length for _, length in horizontal_angles) / 2.0
        cumulative_length = 0.0
        for angle, length in horizontal_angles:
            cumulative_length += length
            if cumulative_length >= midpoint:
                return angle

    coordinates = cv2.findNonZero(foreground)
    if coordinates is None or len(coordinates) < 20:
        return 0.0

    rectangle = cv2.minAreaRect(coordinates)
    corners = cv2.boxPoints(rectangle)
    edges = np.roll(corners, -1, axis=0) - corners
    lengths = np.linalg.norm(edges, axis=1)
    longest_edge = edges[int(np.argmax(lengths))]
    angle = float(np.degrees(np.arctan2(longest_edge[1], longest_edge[0])))

    if angle >= 45.0:
        angle -= 90.0
    elif angle < -45.0:
        angle += 90.0
    return angle


def _rotate_expanded(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate a grayscale image while keeping the full rotated canvas."""
    height, width = image.shape
    center = (width / 2.0, height / 2.0)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    cosine = abs(matrix[0, 0])
    sine = abs(matrix[0, 1])
    new_width = int(np.ceil((height * sine) + (width * cosine)))
    new_height = int(np.ceil((height * cosine) + (width * sine)))
    matrix[0, 2] += (new_width / 2.0) - center[0]
    matrix[1, 2] += (new_height / 2.0) - center[1]
    return cv2.warpAffine(
        image,
        matrix,
        (new_width, new_height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )


def deskew(image: np.ndarray) -> np.ndarray:
    """Rotate receipt content to its nearest horizontal or vertical axis."""
    grayscale = to_grayscale(image)
    angle = estimate_skew_angle(grayscale)
    if abs(angle) < 0.15:
        return grayscale
    return _rotate_expanded(grayscale, angle)


def denoise(image: np.ndarray, strength: float = 10.0) -> np.ndarray:
    """Reduce grayscale image noise while retaining text edges."""
    grayscale = to_grayscale(image)
    return cv2.fastNlMeansDenoising(
        grayscale,
        None,
        h=strength,
        templateWindowSize=7,
        searchWindowSize=21,
    )


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    """Stretch receipt contrast using robust grayscale percentiles and CLAHE."""
    grayscale = to_grayscale(image)
    low, high = np.percentile(grayscale, (1, 99))
    if high <= low:
        return grayscale

    scaled = np.clip(
        (grayscale.astype(np.float32) - low) * (255.0 / (high - low)),
        0,
        255,
    ).astype(np.uint8)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(scaled)


def binarize(image: np.ndarray, block_size: int = 31, constant: int = 10) -> np.ndarray:
    """Convert grayscale input to black text on a white background."""
    grayscale = to_grayscale(image)
    shortest_side = min(grayscale.shape)
    adaptive_block = min(block_size, shortest_side if shortest_side % 2 else shortest_side - 1)
    if adaptive_block < 3:
        _, output = cv2.threshold(
            grayscale, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
        )
        return output

    return cv2.adaptiveThreshold(
        grayscale,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        adaptive_block,
        constant,
    )


def crop_borders(image: np.ndarray, padding_fraction: float = 0.02) -> np.ndarray:
    """Trim the blank border around detected receipt content with safe padding."""
    grayscale = to_grayscale(image)
    _, foreground = cv2.threshold(
        grayscale, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )
    coordinates = cv2.findNonZero(foreground)
    if coordinates is None:
        return grayscale

    x, y, width, height = cv2.boundingRect(coordinates)
    if width == 0 or height == 0:
        return grayscale

    padding = max(2, round(min(grayscale.shape) * padding_fraction))
    x_start = max(0, x - padding)
    y_start = max(0, y - padding)
    x_end = min(grayscale.shape[1], x + width + padding)
    y_end = min(grayscale.shape[0], y + height + padding)
    return grayscale[y_start:y_end, x_start:x_end].copy()
