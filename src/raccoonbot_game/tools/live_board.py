from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from raccoonbot_game.calibration import VisionCalibration
from raccoonbot_game.game import Player
from raccoonbot_game.vision.board_observer import BoardObserver, BoardStateStabilizer, GameBoard


def format_board(board: GameBoard) -> str:
    if len(board) != 9:
        raise ValueError("board must contain nine cells")
    symbols = {None: ".", Player.HUMAN: "R", Player.ROBOT: "Y"}
    values = [symbols[cell] for cell in board]
    return " / ".join(" ".join(values[index : index + 3]) for index in range(0, 9, 3))


def _open_camera(calibration: VisionCalibration, device: int) -> cv2.VideoCapture:
    capture = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not capture.isOpened():
        raise RuntimeError(f"camera /dev/video{device} could not be opened")
    capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, calibration.camera.width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, calibration.camera.height)
    capture.set(cv2.CAP_PROP_FPS, 30)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return capture


def _draw_preview(observation_image, board: GameBoard | None):
    preview = observation_image.copy()
    size = preview.shape[0]
    for offset in (size // 3, size * 2 // 3):
        cv2.line(preview, (offset, 0), (offset, size), (70, 255, 70), 2)
        cv2.line(preview, (0, offset), (size, offset), (70, 255, 70), 2)
    if board is not None:
        cv2.putText(
            preview,
            format_board(board),
            (12, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (40, 255, 40),
            2,
        )
    return preview


def main() -> None:
    parser = argparse.ArgumentParser(description="Jetson 카메라에서 안정화된 3x3 보드 상태 읽기")
    parser.add_argument("calibration", type=Path)
    parser.add_argument("--device", type=int, help="기본값은 캘리브레이션의 카메라 번호")
    parser.add_argument("--frames", type=int, default=0, help="0이면 Ctrl+C까지 계속 실행")
    parser.add_argument("--warmup-frames", type=int, default=30)
    parser.add_argument("--window-size", type=int, default=5)
    parser.add_argument("--required-matches", type=int, default=4)
    parser.add_argument("--save-warped", type=Path)
    parser.add_argument("--preview", action="store_true", help="Jetson 로컬 화면에 보정 영상 표시")
    args = parser.parse_args()
    if args.frames < 0:
        parser.error("--frames must be zero or positive")
    if args.warmup_frames < 0:
        parser.error("--warmup-frames must be zero or positive")

    calibration = VisionCalibration.load(args.calibration)
    device = calibration.camera.device if args.device is None else args.device
    observer = BoardObserver(calibration)
    stabilizer = BoardStateStabilizer(
        window_size=args.window_size,
        required_matches=args.required_matches,
    )
    capture = _open_camera(calibration, device)
    expected_shape = (calibration.camera.height, calibration.camera.width)
    frames_seen = 0
    failed_reads = 0
    last_state: GameBoard | None = None
    stable_state_seen = False

    print(
        f"camera=/dev/video{device} expected={expected_shape[1]}x{expected_shape[0]} "
        f"warmup={args.warmup_frames} stabilizer={args.required_matches}/{args.window_size}",
        flush=True,
    )
    try:
        for _ in range(args.warmup_frames):
            ok, frame = capture.read()
            if not ok or frame is None:
                raise RuntimeError("camera frame read failed during warmup")
            if frame.shape[:2] != expected_shape:
                raise RuntimeError(
                    "camera frame size does not match calibration: "
                    f"got {frame.shape[1]}x{frame.shape[0]}, "
                    f"expected {expected_shape[1]}x{expected_shape[0]}"
                )

        while args.frames == 0 or frames_seen < args.frames:
            ok, frame = capture.read()
            if not ok or frame is None:
                failed_reads += 1
                if failed_reads >= 5:
                    raise RuntimeError("camera frame read failed five times in a row")
                continue
            failed_reads = 0
            frames_seen += 1
            if frame.shape[:2] != expected_shape:
                raise RuntimeError(
                    "camera frame size does not match calibration: "
                    f"got {frame.shape[1]}x{frame.shape[0]}, "
                    f"expected {expected_shape[1]}x{expected_shape[0]}"
                )

            observation = observer.observe(frame)
            state = stabilizer.update(observation)
            if state is not None:
                stable_state_seen = True
                if state != last_state:
                    print(f"stable frame={frames_seen}: {format_board(state)}", flush=True)
                    last_state = state
                    if args.save_warped:
                        args.save_warped.parent.mkdir(parents=True, exist_ok=True)
                        if not cv2.imwrite(str(args.save_warped), observation.warped_image):
                            raise RuntimeError(f"could not write image: {args.save_warped}")

            if args.preview:
                cv2.imshow("RaccoonBot board", _draw_preview(observation.warped_image, state))
                if cv2.waitKey(1) & 0xFF in (27, ord("q")):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        capture.release()
        if args.preview:
            cv2.destroyAllWindows()

    if args.frames and not stable_state_seen:
        raise RuntimeError(f"no stable board state observed in {frames_seen} frames")


if __name__ == "__main__":
    main()
