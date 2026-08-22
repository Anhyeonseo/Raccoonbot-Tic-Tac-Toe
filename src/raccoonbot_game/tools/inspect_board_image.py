from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from raccoonbot_game.calibration import VisionCalibration
from raccoonbot_game.vision.board_observer import BoardObserver


def main() -> None:
    parser = argparse.ArgumentParser(description="저장된 사진에서 3x3 말 상태 검사")
    parser.add_argument("image", type=Path)
    parser.add_argument("calibration", type=Path)
    parser.add_argument("--warped-output", type=Path)
    args = parser.parse_args()

    image = cv2.imread(str(args.image))
    if image is None:
        parser.error(f"이미지를 읽을 수 없습니다: {args.image}")
    observation = BoardObserver(VisionCalibration.load(args.calibration)).observe(image)
    symbols = {"empty": ".", "human": "R", "robot": "Y", "ambiguous": "?"}
    values = [symbols[cell.label.value] for cell in observation.cells]
    print("\n".join(" ".join(values[row : row + 3]) for row in range(0, 9, 3)))
    for index, cell in enumerate(observation.cells, start=1):
        print(
            f"cell {index}: {cell.label.value:9s} "
            f"red={cell.human_ratio:.3f} yellow={cell.robot_ratio:.3f} "
            f"confidence={cell.confidence:.2f}"
        )
    if args.warped_output:
        args.warped_output.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(args.warped_output), observation.warped_image)


if __name__ == "__main__":
    main()
