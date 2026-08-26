from __future__ import annotations

import argparse
import random
import time
from pathlib import Path
from typing import Any

import cv2

from raccoonbot_game.app.session import GameSession, RobotVerificationError
from raccoonbot_game.calibration import VisionCalibration
from raccoonbot_game.game import Action, Game, GameResult, Player
from raccoonbot_game.robot.motion import MotionPlanner
from raccoonbot_game.robot.pose_profile import RobotPoseProfile
from raccoonbot_game.robot.robomation_driver import RobomationDriver
from raccoonbot_game.tools.live_board import _open_camera, format_board
from raccoonbot_game.tools.probe_robot import DEFAULT_PORT, official_connection_state
from raccoonbot_game.tools.smoke_test_gripper import wait_for_end_effector
from raccoonbot_game.tools.smoke_test_motion import wait_for_battery
from raccoonbot_game.vision.board_observer import (
    BoardObserver,
    BoardStateStabilizer,
    GameBoard,
)


def capture_stable_board(
    capture: Any,
    observer: Any,
    *,
    warmup_frames: int = 5,
    max_frames: int = 120,
    window_size: int = 5,
    required_matches: int = 4,
) -> tuple[GameBoard, Any]:
    if warmup_frames < 0 or max_frames <= 0:
        raise ValueError("warmup_frames must be nonnegative and max_frames must be positive")
    for _ in range(warmup_frames):
        ok, frame = capture.read()
        if not ok or frame is None:
            raise RuntimeError("camera frame read failed during board capture warmup")

    stabilizer = BoardStateStabilizer(
        window_size=window_size,
        required_matches=required_matches,
    )
    last_observation = None
    for _ in range(max_frames):
        ok, frame = capture.read()
        if not ok or frame is None:
            continue
        last_observation = observer.observe(frame)
        state = stabilizer.update(last_observation)
        if state is not None:
            return state, last_observation.warped_image
    raise RuntimeError(f"no stable board state observed in {max_frames} frames")


def require_empty_board(board: GameBoard) -> None:
    occupied = [index + 1 for index, cell in enumerate(board) if cell is not None]
    if occupied:
        raise RuntimeError(f"새 게임 시작 전 보드를 비워주세요. 점유 칸: {occupied}")


def reconstruct_placement_game(board: GameBoard) -> Game:
    human_cells = [index for index, cell in enumerate(board) if cell is Player.HUMAN]
    robot_cells = [index for index, cell in enumerate(board) if cell is Player.ROBOT]
    if len(human_cells) > 3 or len(robot_cells) > 3:
        raise ValueError("각 색상의 말은 최대 3개여야 합니다.")
    if len(human_cells) not in (len(robot_cells), len(robot_cells) + 1):
        raise ValueError(
            "배치 단계 재개판의 말 개수가 올바르지 않습니다: "
            f"red={len(human_cells)} yellow={len(robot_cells)}"
        )

    game = Game()
    replay: list[int] = []
    for index, human_cell in enumerate(human_cells):
        replay.append(human_cell)
        if index < len(robot_cells):
            replay.append(robot_cells[index])
    for offset, cell in enumerate(replay):
        if game.result is not GameResult.IN_PROGRESS:
            raise ValueError("이미 승리한 배치판 뒤에 추가 말이 있습니다.")
        game.apply(Action(target=cell))
    if tuple(game.board) != tuple(board):
        raise ValueError("관측 보드를 배치 단계 게임으로 복원하지 못했습니다.")
    return game


def format_action(action: Action) -> str:
    if action.source is None:
        return f"{action.target + 1}번 칸에 배치"
    return f"{action.source + 1}번 → {action.target + 1}번 이동"


def result_message(result: GameResult) -> str:
    return {
        GameResult.HUMAN_WIN: "사람 승리!",
        GameResult.ROBOT_WIN: "라쿤봇 승리!",
        GameResult.DRAW_REPETITION: "같은 상태가 반복되어 무승부!",
        GameResult.DRAW_TURN_LIMIT: "이동 턴 제한으로 무승부!",
        GameResult.IN_PROGRESS: "게임 진행 중",
    }[result]


def _save_warped(directory: Path | None, index: int, label: str, image: Any) -> None:
    if directory is None:
        return
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{index:02d}-{label}.jpg"
    if not cv2.imwrite(str(target), image):
        raise RuntimeError(f"could not write image: {target}")


def run_game(
    *,
    profile_path: Path,
    calibration_path: Path,
    port: str,
    device: int | None,
    joint_step_degrees: float,
    seed: int,
    capture_dir: Path | None,
    resume_placement: bool = False,
) -> GameResult:
    profile = RobotPoseProfile.load(profile_path)
    calibration = VisionCalibration.load(calibration_path)
    camera_device = calibration.camera.device if device is None else device
    robot = None
    driver = None
    capture = None
    try:
        from robomation import RaccoonBot

        robot = RaccoonBot(port_name=port)
        if official_connection_state(robot) is False:
            raise RuntimeError("Mini Dongle+ is open, but no RaccoonBot is paired")
        battery = wait_for_battery(robot)
        if battery < 3.3:
            raise RuntimeError(f"battery voltage is too low to start a game: {battery}V")
        device_type = wait_for_end_effector(robot)
        if device_type != 4:
            raise RuntimeError(f"expected DC gripper device 4, detected device {device_type}")

        driver = RobomationDriver(
            profile,
            robot=robot,
            joint_step_degrees=joint_step_degrees,
        )
        motion = MotionPlanner(driver)
        observer = BoardObserver(calibration)
        capture = _open_camera(calibration, camera_device)

        print(
            f"장비 준비 완료: battery={battery}V speed={profile.max_speed:g} "
            f"joint_step={joint_step_degrees:g}° camera=/dev/video{camera_device}",
            flush=True,
        )
        print("카메라 관찰 자세로 이동합니다. 작업 영역에서 손을 빼주세요.", flush=True)
        driver.move_to("home")
        time.sleep(0.5)
        initial, warped = capture_stable_board(capture, observer, warmup_frames=15)
        print(f"초기 보드: {format_board(initial)}", flush=True)
        _save_warped(capture_dir, 0, "initial", warped)
        if any(cell is not None for cell in initial):
            if not resume_placement:
                require_empty_board(initial)
            game = reconstruct_placement_game(initial)
            print(
                f"현재 배치판에서 재개: red={initial.count(Player.HUMAN)} "
                f"yellow={initial.count(Player.ROBOT)} next={game.turn.value}",
                flush=True,
            )
        else:
            game = Game()
        session = GameSession(motion, game=game, rng=random.Random(seed))

        capture_index = 1
        if session.game.result is GameResult.IN_PROGRESS and session.game.turn is Player.ROBOT:
            print("재개된 로봇 차례를 실행합니다. 작업 영역에 손을 넣지 마세요.", flush=True)
            pending = session.play_robot_turn()
            print(
                f"라쿤봇 수: {format_action(pending.decision.action)} "
                f"({pending.decision.reason})",
                flush=True,
            )
            while True:
                actual, warped = capture_stable_board(capture, observer)
                print(f"로봇 수 관측: {format_board(actual)}", flush=True)
                _save_warped(capture_dir, capture_index, "robot-resume", warped)
                capture_index += 1
                try:
                    session.verify_robot_board(actual)
                    break
                except RobotVerificationError as exc:
                    print(f"자동 검증 실패: {exc}", flush=True)
                    input("운영자가 보드를 확인한 뒤 재촬영하려면 Enter를 누르세요: ")

        while session.game.result is GameResult.IN_PROGRESS:
            print("\n사람 차례입니다.", flush=True)
            if session.game.phase.value == "placement":
                prompt = "빨간 말 하나를 빈칸에 놓고 손을 완전히 뺀 뒤 Enter를 누르세요: "
            else:
                prompt = "빨간 말 하나를 원하는 빈칸으로 옮기고 손을 뺀 뒤 Enter를 누르세요: "
            input(prompt)

            observed, warped = capture_stable_board(capture, observer)
            print(f"사람 수 관측: {format_board(observed)}", flush=True)
            _save_warped(capture_dir, capture_index, "human", warped)
            capture_index += 1
            try:
                print("라쿤봇이 생각하고 움직입니다. 작업 영역에 손을 넣지 마세요.", flush=True)
                pending = session.accept_human_board(observed)
            except ValueError as exc:
                print(f"사람 수를 인정할 수 없습니다: {exc}", flush=True)
                continue

            if pending is None:
                break
            print(
                f"라쿤봇 수: {format_action(pending.decision.action)} "
                f"({pending.decision.reason})",
                flush=True,
            )

            time.sleep(0.5)
            while True:
                actual, warped = capture_stable_board(capture, observer)
                print(f"로봇 수 관측: {format_board(actual)}", flush=True)
                _save_warped(capture_dir, capture_index, "robot", warped)
                capture_index += 1
                try:
                    session.verify_robot_board(actual)
                    break
                except RobotVerificationError as exc:
                    print(f"자동 검증 실패: {exc}", flush=True)
                    input("운영자가 보드를 확인한 뒤 재촬영하려면 Enter를 누르세요: ")

        print(f"\n게임 종료: {result_message(session.game.result)}", flush=True)
        print(f"최종 보드: {format_board(tuple(session.game.board))}", flush=True)
        return session.game.result
    finally:
        if capture is not None:
            capture.release()
        if driver is not None:
            driver.stop()
            driver.dispose()
        elif robot is not None:
            robot.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="카메라와 실제 RaccoonBot으로 한 게임 진행")
    parser.add_argument("--profile", type=Path, default=Path("config/robot_poses.json"))
    parser.add_argument("--calibration", type=Path, default=Path("config/vision.json"))
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--device", type=int)
    parser.add_argument("--joint-step", type=float, default=6.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--capture-dir", type=Path, default=Path("work/game-captures"))
    parser.add_argument("--resume-placement", action="store_true")
    parser.add_argument("--confirm-hardware", action="store_true")
    args = parser.parse_args()
    if not args.confirm_hardware:
        parser.error("refusing hardware game without --confirm-hardware")
    if not 1 <= args.joint_step <= 6:
        parser.error("--joint-step must be within 1..6 degrees")

    try:
        result = run_game(
            profile_path=args.profile,
            calibration_path=args.calibration,
            port=args.port,
            device=args.device,
            joint_step_degrees=args.joint_step,
            seed=args.seed,
            capture_dir=args.capture_dir,
            resume_placement=args.resume_placement,
        )
    except KeyboardInterrupt:
        raise SystemExit("운영자가 게임을 중단했습니다. 로봇을 정지했습니다.")
    except ImportError as exc:
        raise SystemExit("robomation package is not installed") from exc
    raise SystemExit(0 if result is not GameResult.IN_PROGRESS else 1)


if __name__ == "__main__":
    main()
