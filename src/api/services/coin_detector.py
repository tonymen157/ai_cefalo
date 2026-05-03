import cv2
import numpy as np


def detect_coin(image_path: str, coin_diameter_mm: float = 26.5) -> float:
    """Detect coin and return mm/pixel ratio.

    Args:
        image_path: Path to X-ray image.
        coin_diameter_mm: Coin diameter in mm (default 26.5 for $1 USD).
    Returns:
        mm_per_pixel value if coin detected.
    Raises:
        ValueError if no coin detected or image invalid.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Could not read image for coin detection")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 5)

    # Detect circles using HoughCircles
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=100,
        param1=50,
        param2=30,
        minRadius=20,
        maxRadius=200,
    )

    if circles is None:
        raise ValueError("No $1 USD coin detected in image")

    circles = np.uint16(np.around(circles))
    # Take the largest circle (most likely the coin)
    circles_sorted = sorted(circles[0, :], key=lambda c: c[2], reverse=True)

    for circle in circles_sorted:
        pixel_diameter = circle[2] * 2
        mm_per_pixel = coin_diameter_mm / pixel_diameter
        if 0.05 < mm_per_pixel < 0.5:  # Reasonable range for dental X-rays
            return round(mm_per_pixel, 6)

    raise ValueError("No valid coin detected (unreasonable size)")
