from __future__ import annotations

import shutil
import threading
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np

from ..calibration import BoardSettings, CameraSettings, VisionCalibration
from ..tools.create_calibration import sample_hue_settings
from ..vision.board_observer import BoardObserver


FrameProvider = Callable[[], np.ndarray]
Point = tuple[int, int]
POINT_LABELS = ("TL", "TR", "BR", "BL", "RED", "YELLOW")


@dataclass(frozen=True, slots=True)
class CalibrationProposal:
    calibration: VisionCalibration
    preview_jpeg: bytes
    cells: tuple[dict[str, Any], ...]


class WebCalibrationController:
    """Thread-safe capture, preview, and explicit-save calibration workflow."""

    def __init__(self, calibration_path: Path, frame_provider: FrameProvider) -> None:
        self.calibration_path = calibration_path
        self._frame_provider = frame_provider
        self._lock = threading.Lock()
        self._frame: np.ndarray | None = None
        self._frame_jpeg: bytes | None = None
        self._proposal: CalibrationProposal | None = None
        self._busy = False

    @property
    def busy(self) -> bool:
        with self._lock:
            return self._busy

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            frame = self._frame
            proposal = self._proposal
            return {
                "busy": self._busy,
                "has_frame": frame is not None,
                "has_preview": proposal is not None,
                "width": int(frame.shape[1]) if frame is not None else None,
                "height": int(frame.shape[0]) if frame is not None else None,
                "point_order": list(POINT_LABELS),
            }

    def capture(self) -> dict[str, Any]:
        self._set_busy(True)
        try:
            frame = self._frame_provider()
            if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3:
                raise RuntimeError("camera capture must return a BGR image")
            jpeg = _encode_jpeg(frame)
            with self._lock:
                self._frame = frame.copy()
                self._frame_jpeg = jpeg
                self._proposal = None
            return {
                "width": int(frame.shape[1]),
                "height": int(frame.shape[0]),
                "point_order": list(POINT_LABELS),
            }
        finally:
            self._set_busy(False)

    def image(self, *, preview: bool = False) -> bytes | None:
        with self._lock:
            if preview:
                return self._proposal.preview_jpeg if self._proposal else None
            return self._frame_jpeg

    def preview(self, payload: dict[str, Any]) -> dict[str, Any]:
        points = _parse_points(payload.get("points"))
        with self._lock:
            if self._frame is None:
                raise ValueError("먼저 카메라 사진을 촬영하세요")
            frame = self._frame.copy()

        _validate_board_corners(points[:4], frame.shape[1], frame.shape[0])
        current = VisionCalibration.load(self.calibration_path)
        camera = CameraSettings(
            device=current.camera.device,
            width=int(frame.shape[1]),
            height=int(frame.shape[0]),
            exposure=current.camera.exposure,
            white_balance=current.camera.white_balance,
            gain=current.camera.gain,
        )
        board = BoardSettings(
            corners=tuple((float(x), float(y)) for x, y in points[:4]),
            rotation=current.board.rotation,
            canonical_size=current.board.canonical_size,
            cell_margin_ratio=current.board.cell_margin_ratio,
        )
        proposal = VisionCalibration(
            camera=camera,
            board=board,
            human_color=sample_hue_settings(
                frame,
                points[4],
                base=current.human_color,
            ),
            robot_color=sample_hue_settings(
                frame,
                points[5],
                base=current.robot_color,
            ),
        )
        observation = BoardObserver(proposal).observe(frame)
        cells = tuple(
            {
                "cell": index + 1,
                "label": reading.label.value,
                "red_ratio": round(reading.human_ratio, 4),
                "yellow_ratio": round(reading.robot_ratio, 4),
            }
            for index, reading in enumerate(observation.cells)
        )
        preview_image = _draw_preview(observation.warped_image, cells)
        stored = CalibrationProposal(proposal, _encode_jpeg(preview_image), cells)
        with self._lock:
            self._proposal = stored
        return {
            "cells": list(cells),
            "human_color": asdict(proposal.human_color),
            "robot_color": asdict(proposal.robot_color),
        }

    def save(self) -> dict[str, Any]:
        with self._lock:
            if self._proposal is None:
                raise ValueError("미리보기를 먼저 생성하세요")
            calibration = self._proposal.calibration

        target = self.calibration_path
        target.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = target.with_name(f"{target.stem}.backup-{timestamp}{target.suffix}")
        if target.exists():
            shutil.copy2(target, backup)
        temporary = target.with_suffix(target.suffix + ".tmp")
        calibration.save(temporary)
        temporary.replace(target)
        return {
            "saved": str(target),
            "backup": str(backup) if backup.exists() else None,
        }

    def _set_busy(self, busy: bool) -> None:
        with self._lock:
            if busy and self._busy:
                raise RuntimeError("캘리브레이션 작업이 이미 진행 중입니다")
            self._busy = busy


def _parse_points(raw: Any) -> tuple[Point, Point, Point, Point, Point, Point]:
    if not isinstance(raw, list) or len(raw) != 6:
        raise ValueError("TL, TR, BR, BL, RED, YELLOW 여섯 점이 필요합니다")
    points: list[Point] = []
    for value in raw:
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError("각 점은 [x, y] 형식이어야 합니다")
        x, y = value
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValueError("점 좌표는 숫자여야 합니다")
        points.append((int(round(x)), int(round(y))))
    return tuple(points)  # type: ignore[return-value]


def _validate_board_corners(corners: tuple[Point, ...], width: int, height: int) -> None:
    if any(not 0 <= x < width or not 0 <= y < height for x, y in corners):
        raise ValueError("보드 모서리가 카메라 이미지 밖에 있습니다")
    polygon = np.asarray(corners, dtype=np.float32)
    if not cv2.isContourConvex(polygon.astype(np.int32)):
        raise ValueError("보드 모서리 순서를 TL, TR, BR, BL로 확인하세요")
    minimum_area = width * height * 0.05
    if abs(cv2.contourArea(polygon)) < minimum_area:
        raise ValueError("선택한 보드 영역이 너무 작습니다")


def _draw_preview(image: np.ndarray, cells: tuple[dict[str, Any], ...]) -> np.ndarray:
    preview = image.copy()
    size = preview.shape[0]
    for offset in (size // 3, size * 2 // 3):
        cv2.line(preview, (offset, 0), (offset, size), (80, 255, 80), 3)
        cv2.line(preview, (0, offset), (size, offset), (80, 255, 80), 3)
    for cell in cells:
        index = int(cell["cell"]) - 1
        row, column = divmod(index, 3)
        x = column * size // 3 + 12
        y = row * size // 3 + 28
        label = str(cell["label"])
        text = f"{index + 1}: {label}"
        cv2.putText(
            preview,
            text,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 0, 255),
            2,
            cv2.LINE_AA,
        )
    return preview


def _encode_jpeg(image: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".jpg", image, (cv2.IMWRITE_JPEG_QUALITY, 90))
    if not ok:
        raise RuntimeError("이미지를 JPEG로 변환하지 못했습니다")
    return encoded.tobytes()
