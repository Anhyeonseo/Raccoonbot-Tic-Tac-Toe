from __future__ import annotations

import cv2
import numpy as np
from numpy.typing import NDArray

from ..game import Player


Image = NDArray[np.uint8]


def render_board(
    board: tuple[Player | None, ...] | list[Player | None],
    *,
    cell_size: int = 200,
    token_radius_ratio: float = 0.28,
) -> Image:
    """Render a deterministic black/white board for desktop vision tests."""

    if len(board) != 9:
        raise ValueError("board must contain exactly 9 cells")
    if cell_size < 30:
        raise ValueError("cell size is too small")
    if not 0.05 <= token_radius_ratio < 0.5:
        raise ValueError("token radius ratio must be within [0.05, 0.5)")

    size = cell_size * 3
    image = np.empty((size, size, 3), dtype=np.uint8)
    for index, occupant in enumerate(board):
        row, column = divmod(index, 3)
        background = 235 if (row + column) % 2 == 0 else 25
        x0, y0 = column * cell_size, row * cell_size
        x1, y1 = x0 + cell_size, y0 + cell_size
        image[y0:y1, x0:x1] = (background, background, background)

        if occupant is not None:
            center = (x0 + cell_size // 2, y0 + cell_size // 2)
            radius = int(round(cell_size * token_radius_ratio))
            color = (0, 0, 230) if occupant is Player.HUMAN else (0, 220, 220)
            cv2.circle(image, center, radius, color, thickness=-1, lineType=cv2.LINE_AA)

    for offset in (0, cell_size, cell_size * 2, size - 1):
        cv2.line(image, (offset, 0), (offset, size - 1), (90, 90, 90), 2)
        cv2.line(image, (0, offset), (size - 1, offset), (90, 90, 90), 2)
    return image


def project_board(
    board_image: Image,
    destination_corners: tuple[tuple[float, float], ...],
    *,
    canvas_width: int = 900,
    canvas_height: int = 700,
) -> Image:
    """Project a square board onto a larger canvas for perspective tests."""

    if len(destination_corners) != 4:
        raise ValueError("four destination corners are required")
    height, width = board_image.shape[:2]
    source = np.asarray(
        ((0.0, 0.0), (width - 1.0, 0.0), (width - 1.0, height - 1.0), (0.0, height - 1.0)),
        dtype=np.float32,
    )
    destination = np.asarray(destination_corners, dtype=np.float32)
    transform = cv2.getPerspectiveTransform(source, destination)
    canvas = np.full((canvas_height, canvas_width, 3), 105, dtype=np.uint8)
    warped = cv2.warpPerspective(board_image, transform, (canvas_width, canvas_height))
    mask_source = np.full((height, width), 255, dtype=np.uint8)
    mask = cv2.warpPerspective(mask_source, transform, (canvas_width, canvas_height))
    canvas[mask > 0] = warped[mask > 0]
    return canvas

