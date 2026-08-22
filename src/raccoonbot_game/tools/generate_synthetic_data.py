from __future__ import annotations

import argparse
import random
from pathlib import Path

import cv2

from raccoonbot_game.calibration import BoardSettings, default_synthetic_calibration
from raccoonbot_game.game import Player
from raccoonbot_game.vision.synthetic import project_board, render_board


def main() -> None:
    parser = argparse.ArgumentParser(description="빨강/노랑 3말 잇기 합성 테스트 이미지 생성")
    parser.add_argument("output", type=Path)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count는 1 이상이어야 합니다")

    rng = random.Random(args.seed)
    args.output.mkdir(parents=True, exist_ok=True)
    for number in range(args.count):
        cells = [None] * 9
        occupied = rng.sample(range(9), rng.randint(0, 6))
        for order, index in enumerate(occupied):
            cells[index] = Player.HUMAN if order % 2 == 0 else Player.ROBOT
        board = render_board(cells)
        corners = (
            (rng.randint(80, 160), rng.randint(50, 110)),
            (rng.randint(720, 820), rng.randint(45, 120)),
            (rng.randint(730, 850), rng.randint(570, 660)),
            (rng.randint(45, 150), rng.randint(560, 660)),
        )
        image = project_board(board, corners)
        cv2.imwrite(str(args.output / f"board_{number:03d}.png"), image)

        if number == 0:
            calibration = default_synthetic_calibration()
            calibration = type(calibration)(
                camera=calibration.camera,
                board=BoardSettings(corners=tuple((float(x), float(y)) for x, y in corners)),
                human_color=calibration.human_color,
                robot_color=calibration.robot_color,
            )
            calibration.save(args.output / "board_000.calibration.json")
    print(f"{args.output}에 합성 이미지 {args.count}장을 생성했습니다.")


if __name__ == "__main__":
    main()
