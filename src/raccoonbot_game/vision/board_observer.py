from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

import cv2
import numpy as np
from numpy.typing import NDArray

from ..calibration import ColorSettings, VisionCalibration
from ..game import Player
from .perspective import cell_bounds, warp_board


Image = NDArray[np.uint8]
GameBoard = tuple[Player | None, ...]


class CellLabel(str, Enum):
    EMPTY = "empty"
    HUMAN = "human"
    ROBOT = "robot"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class CellReading:
    label: CellLabel
    human_ratio: float
    robot_ratio: float
    confidence: float


@dataclass(frozen=True, slots=True)
class BoardObservation:
    cells: tuple[CellReading, ...]
    warped_image: Image = field(repr=False, compare=False)

    @property
    def is_complete(self) -> bool:
        return all(cell.label is not CellLabel.AMBIGUOUS for cell in self.cells)

    def as_game_board(self) -> GameBoard:
        if not self.is_complete:
            raise ValueError("ambiguous cells cannot be converted to a game board")
        mapping = {
            CellLabel.EMPTY: None,
            CellLabel.HUMAN: Player.HUMAN,
            CellLabel.ROBOT: Player.ROBOT,
        }
        return tuple(mapping[cell.label] for cell in self.cells)


class BoardObserver:
    def __init__(self, calibration: VisionCalibration) -> None:
        self.calibration = calibration

    def observe(self, image: Image) -> BoardObservation:
        warped = warp_board(image, self.calibration.board)
        hsv = cv2.cvtColor(warped, cv2.COLOR_BGR2HSV)
        human_mask = _color_mask(hsv, self.calibration.human_color)
        robot_mask = _color_mask(hsv, self.calibration.robot_color)

        readings = []
        for index in range(9):
            x0, y0, x1, y1 = cell_bounds(
                index,
                board_size=self.calibration.board.canonical_size,
                margin_ratio=self.calibration.board.cell_margin_ratio,
            )
            human_ratio = _mask_ratio(human_mask[y0:y1, x0:x1])
            robot_ratio = _mask_ratio(robot_mask[y0:y1, x0:x1])
            readings.append(
                _classify_cell(
                    human_ratio,
                    robot_ratio,
                    self.calibration.human_color,
                    self.calibration.robot_color,
                )
            )
        return BoardObservation(tuple(readings), warped)


class BoardStateStabilizer:
    """Require repeated matching observations before accepting a board state."""

    def __init__(self, *, window_size: int = 5, required_matches: int = 4) -> None:
        if window_size <= 0:
            raise ValueError("window size must be positive")
        if not 1 <= required_matches <= window_size:
            raise ValueError("required matches must be within the window size")
        self.window_size = window_size
        self.required_matches = required_matches
        self._history: deque[GameBoard] = deque(maxlen=window_size)

    def update(self, observation: BoardObservation) -> GameBoard | None:
        if not observation.is_complete:
            return None
        state = observation.as_game_board()
        self._history.append(state)
        state_counts = Counter(self._history)
        candidate, count = state_counts.most_common(1)[0]
        return candidate if count >= self.required_matches else None

    def reset(self) -> None:
        self._history.clear()


def _color_mask(hsv: Image, settings: ColorSettings) -> NDArray[np.uint8]:
    combined = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for hue_low, hue_high in settings.hue_intervals:
        lower = np.asarray(
            (hue_low, settings.saturation_min, settings.value_min),
            dtype=np.uint8,
        )
        upper = np.asarray((hue_high, 255, 255), dtype=np.uint8)
        combined = cv2.bitwise_or(combined, cv2.inRange(hsv, lower, upper))
    kernel = np.ones((3, 3), dtype=np.uint8)
    return cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)


def _mask_ratio(mask: NDArray[np.uint8]) -> float:
    if mask.size == 0:
        return 0.0
    return float(np.count_nonzero(mask)) / float(mask.size)


def _classify_cell(
    human_ratio: float,
    robot_ratio: float,
    human_settings: ColorSettings,
    robot_settings: ColorSettings,
) -> CellReading:
    human_present = human_ratio >= human_settings.pixel_ratio_min
    robot_present = robot_ratio >= robot_settings.pixel_ratio_min

    if human_present and robot_present:
        difference = abs(human_ratio - robot_ratio)
        if difference < 0.02:
            return CellReading(CellLabel.AMBIGUOUS, human_ratio, robot_ratio, 0.0)
        label = CellLabel.HUMAN if human_ratio > robot_ratio else CellLabel.ROBOT
        confidence = min(1.0, difference / 0.1)
        return CellReading(label, human_ratio, robot_ratio, confidence)

    if human_present:
        confidence = min(1.0, human_ratio / human_settings.pixel_ratio_min)
        return CellReading(CellLabel.HUMAN, human_ratio, robot_ratio, confidence)
    if robot_present:
        confidence = min(1.0, robot_ratio / robot_settings.pixel_ratio_min)
        return CellReading(CellLabel.ROBOT, human_ratio, robot_ratio, confidence)

    maximum_ratio = max(
        human_ratio / human_settings.pixel_ratio_min,
        robot_ratio / robot_settings.pixel_ratio_min,
    )
    return CellReading(
        CellLabel.EMPTY,
        human_ratio,
        robot_ratio,
        max(0.0, 1.0 - maximum_ratio),
    )

