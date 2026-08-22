from __future__ import annotations

import cv2
import numpy as np
from numpy.typing import NDArray

from ..calibration import BoardSettings


Image = NDArray[np.uint8]


def warp_board(image: Image, settings: BoardSettings) -> Image:
    """Warp a calibrated board quadrilateral into a square top-down view."""

    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("expected a BGR image with shape (height, width, 3)")

    source = np.asarray(settings.corners, dtype=np.float32)
    edge = float(settings.canonical_size - 1)
    destination = np.asarray(
        ((0.0, 0.0), (edge, 0.0), (edge, edge), (0.0, edge)),
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(source, destination)
    warped = cv2.warpPerspective(
        image,
        transform,
        (settings.canonical_size, settings.canonical_size),
        flags=cv2.INTER_LINEAR,
    )
    if settings.rotation:
        warped = np.rot90(warped, k=settings.rotation).copy()
    return warped


def cell_bounds(
    index: int,
    *,
    board_size: int,
    margin_ratio: float,
) -> tuple[int, int, int, int]:
    """Return x0, y0, x1, y1 for the central ROI of one board cell."""

    if not 0 <= index < 9:
        raise ValueError("cell index must be between 0 and 8")
    if not 0.0 <= margin_ratio < 0.5:
        raise ValueError("margin ratio must be between 0.0 and 0.5")

    row, column = divmod(index, 3)
    cell = board_size / 3.0
    margin = cell * margin_ratio
    x0 = int(round(column * cell + margin))
    y0 = int(round(row * cell + margin))
    x1 = int(round((column + 1) * cell - margin))
    y1 = int(round((row + 1) * cell - margin))
    return x0, y0, x1, y1

