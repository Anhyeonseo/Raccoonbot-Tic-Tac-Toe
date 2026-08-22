from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

from raccoonbot_game.calibration import (
    BoardSettings,
    CameraSettings,
    ColorSettings,
    VisionCalibration,
)


WINDOW = "Calibration: TL, TR, BR, BL, RED, YELLOW (R=reset, Enter=save, Esc=quit)"


def _hue_settings(image: np.ndarray, point: tuple[int, int], *, radius: int = 8) -> ColorSettings:
    x, y = point
    y0, y1 = max(0, y - radius), min(image.shape[0], y + radius + 1)
    x0, x1 = max(0, x - radius), min(image.shape[1], x + radius + 1)
    hsv = cv2.cvtColor(image[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    saturated = hsv[hsv[:, :, 1] >= 80]
    if saturated.size == 0:
        raise ValueError("선택 영역의 채도가 너무 낮습니다")
    hue = int(np.median(saturated[:, 0]))
    low, high = hue - 10, hue + 10
    if low < 0:
        intervals = ((0, high), (180 + low, 179))
    elif high > 179:
        intervals = ((low, 179), (0, high - 180))
    else:
        intervals = ((low, high),)
    return ColorSettings(hue_intervals=intervals, saturation_min=80, value_min=50)


def collect_points(image: np.ndarray) -> list[tuple[int, int]] | None:
    points: list[tuple[int, int]] = []

    def on_mouse(event: int, x: int, y: int, _flags: int, _data: object) -> None:
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 6:
            points.append((x, y))

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WINDOW, on_mouse)
    labels = ("TL", "TR", "BR", "BL", "RED", "YELLOW")
    while True:
        preview = image.copy()
        for index, point in enumerate(points):
            color = (0, 255, 0) if index < 4 else ((0, 0, 255) if index == 4 else (0, 255, 255))
            cv2.circle(preview, point, 7, color, -1)
            cv2.putText(preview, labels[index], (point[0] + 9, point[1] - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        next_label = labels[len(points)] if len(points) < 6 else "Enter to save"
        cv2.putText(preview, f"Next: {next_label}", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 240, 30), 2)
        cv2.imshow(WINDOW, preview)
        key = cv2.waitKey(20) & 0xFF
        if key in (27, ord("q")):
            cv2.destroyAllWindows()
            return None
        if key == ord("r"):
            points.clear()
        if key in (10, 13) and len(points) == 6:
            cv2.destroyAllWindows()
            return points


def main() -> None:
    parser = argparse.ArgumentParser(description="사진 한 장으로 보드/색상 캘리브레이션 생성")
    parser.add_argument("image", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--rotation", type=int, choices=range(4), default=0)
    args = parser.parse_args()
    image = cv2.imread(str(args.image))
    if image is None:
        parser.error(f"이미지를 읽을 수 없습니다: {args.image}")

    points = collect_points(image)
    if points is None:
        print("취소했습니다.")
        return
    corners = tuple((float(x), float(y)) for x, y in points[:4])
    calibration = VisionCalibration(
        camera=CameraSettings(width=image.shape[1], height=image.shape[0]),
        board=BoardSettings(corners=corners, rotation=args.rotation),
        human_color=_hue_settings(image, points[4]),
        robot_color=_hue_settings(image, points[5]),
    )
    calibration.save(args.output)
    print(f"캘리브레이션을 저장했습니다: {args.output}")


if __name__ == "__main__":
    main()
