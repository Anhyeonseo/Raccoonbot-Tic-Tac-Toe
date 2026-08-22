from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


Point = tuple[float, float]
HueInterval = tuple[int, int]


@dataclass(frozen=True, slots=True)
class CameraSettings:
    device: int = 0
    width: int = 1280
    height: int = 720
    exposure: float | None = None
    white_balance: float | None = None
    gain: float | None = None

    def __post_init__(self) -> None:
        if self.device < 0:
            raise ValueError("camera device index cannot be negative")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("camera dimensions must be positive")


@dataclass(frozen=True, slots=True)
class BoardSettings:
    corners: tuple[Point, Point, Point, Point]
    rotation: int = 0
    canonical_size: int = 600
    cell_margin_ratio: float = 0.2

    def __post_init__(self) -> None:
        if len(self.corners) != 4:
            raise ValueError("board requires four corners")
        if self.rotation not in (0, 1, 2, 3):
            raise ValueError("rotation must be 0, 1, 2, or 3 quarter-turns")
        if self.canonical_size < 90:
            raise ValueError("canonical board size is too small")
        if not 0.0 <= self.cell_margin_ratio < 0.5:
            raise ValueError("cell margin ratio must be between 0.0 and 0.5")


@dataclass(frozen=True, slots=True)
class ColorSettings:
    hue_intervals: tuple[HueInterval, ...]
    saturation_min: int = 100
    value_min: int = 60
    pixel_ratio_min: float = 0.08

    def __post_init__(self) -> None:
        if not self.hue_intervals:
            raise ValueError("at least one hue interval is required")
        for low, high in self.hue_intervals:
            if not 0 <= low <= high <= 179:
                raise ValueError("OpenCV hue intervals must be within 0..179")
        for value in (self.saturation_min, self.value_min):
            if not 0 <= value <= 255:
                raise ValueError("HSV thresholds must be within 0..255")
        if not 0.0 < self.pixel_ratio_min <= 1.0:
            raise ValueError("pixel ratio must be within (0.0, 1.0]")


@dataclass(frozen=True, slots=True)
class VisionCalibration:
    camera: CameraSettings
    board: BoardSettings
    human_color: ColorSettings
    robot_color: ColorSettings

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "VisionCalibration":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "VisionCalibration":
        camera = CameraSettings(**raw["camera"])
        board_raw = raw["board"]
        board = BoardSettings(
            corners=tuple(tuple(point) for point in board_raw["corners"]),
            rotation=board_raw.get("rotation", 0),
            canonical_size=board_raw.get("canonical_size", 600),
            cell_margin_ratio=board_raw.get("cell_margin_ratio", 0.2),
        )
        return cls(
            camera=camera,
            board=board,
            human_color=_color_from_dict(raw["human_color"]),
            robot_color=_color_from_dict(raw["robot_color"]),
        )


def default_synthetic_calibration(size: int = 600) -> VisionCalibration:
    """Return deterministic values intended for generated test images only."""

    edge = float(size - 1)
    return VisionCalibration(
        camera=CameraSettings(width=size, height=size),
        board=BoardSettings(
            corners=((0.0, 0.0), (edge, 0.0), (edge, edge), (0.0, edge)),
            canonical_size=size,
        ),
        human_color=ColorSettings(hue_intervals=((0, 10), (170, 179))),
        robot_color=ColorSettings(hue_intervals=((20, 38),)),
    )


def _color_from_dict(raw: dict[str, Any]) -> ColorSettings:
    return ColorSettings(
        hue_intervals=tuple(tuple(interval) for interval in raw["hue_intervals"]),
        saturation_min=raw.get("saturation_min", 100),
        value_min=raw.get("value_min", 60),
        pixel_ratio_min=raw.get("pixel_ratio_min", 0.08),
    )

