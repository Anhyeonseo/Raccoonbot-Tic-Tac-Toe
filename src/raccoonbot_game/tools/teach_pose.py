from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from raccoonbot_game.robot.joint_motion import move_joints_interpolated
from raccoonbot_game.robot.pose_profile import JOINT_LIMITS
from raccoonbot_game.tools.probe_robot import DEFAULT_PORT, official_connection_state
from raccoonbot_game.tools.smoke_test_motion import wait_for_battery


def validate_angles(angles: list[float]) -> list[float]:
    if len(angles) != 4:
        raise RuntimeError(f"expected four encoder values, got {angles}")
    values = [round(float(value), 3) for value in angles]
    for joint, (angle, (low, high)) in enumerate(zip(values, JOINT_LIMITS), start=1):
        if not low <= angle <= high:
            raise RuntimeError(f"J{joint} is outside {low}..{high}: {angle}")
    return values


def save_pose(template: Path, output: Path, pose_name: str, angles: list[float]) -> None:
    source = output if output.exists() else template
    raw = json.loads(source.read_text(encoding="utf-8"))
    poses = raw.get("poses")
    if not isinstance(poses, dict) or pose_name not in poses:
        raise ValueError(f"unknown pose name: {pose_name}")
    poses[pose_name] = validate_angles(angles)
    provisional = raw.get("_provisional_poses", [])
    if isinstance(provisional, list):
        raw["_provisional_poses"] = [name for name in provisional if name != pose_name]
    raw["_warning"] = (
        "장비별 teaching 값입니다. null 자세를 모두 저장한 뒤 "
        "raccoonbot-validate-poses로 검증하세요."
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)


def load_pose(path: Path, pose_name: str) -> list[float]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    try:
        angles = raw["poses"][pose_name]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"unknown pose name: {pose_name}") from exc
    if angles is None:
        raise ValueError(f"pose is not taught: {pose_name}")
    return validate_angles(list(angles))


def wait_for_teach_click(
    robot: Any,
    *,
    timeout_s: float,
    poll_s: float = 0.05,
    reporter: Callable[[str], None] = print,
    sleeper: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> list[float]:
    started = monotonic()
    next_report = started
    while monotonic() - started < timeout_s:
        if robot.button("teach", "click"):
            return validate_angles(list(robot.encoder()))
        now = monotonic()
        if now >= next_report:
            reporter(f"encoders={validate_angles(list(robot.encoder()))}")
            next_report = now + 1.0
        sleeper(poll_s)
    raise TimeoutError(f"Teach button was not pressed within {timeout_s:g} seconds")


def teach_pose(
    robot_factory: Callable[..., Any],
    *,
    template: Path,
    output: Path,
    pose_name: str,
    port: str,
    capture_current: bool,
    timeout_s: float,
    start_pose: list[float] | None = None,
    start_speed: float = 10.0,
    start_motion_mode: str = "interpolated",
) -> list[float]:
    if start_motion_mode not in {"interpolated", "direct"}:
        raise ValueError("start_motion_mode must be interpolated or direct")
    robot = None
    motors_released = False
    try:
        robot = robot_factory(port_name=port)
        if official_connection_state(robot) is False:
            raise RuntimeError("Mini Dongle+ is open, but no RaccoonBot is paired")
        battery = wait_for_battery(robot)
        if battery < 3.3:
            raise RuntimeError(f"battery voltage is too low for teaching: {battery}V")

        robot.set_speed_joints(0, 0, 0, 0)
        if capture_current:
            angles = validate_angles(list(robot.encoder()))
        else:
            if start_pose is not None:
                robot.angle_max_speed(start_speed)
                start_pose = validate_angles(start_pose)
                print(f"저장된 시작 자세로 이동합니다: {start_pose}", flush=True)
                if start_motion_mode == "direct":
                    robot.set_angle_joints(*start_pose, wait=True)
                    print("시작 자세 도착: direct", flush=True)
                else:
                    steps = move_joints_interpolated(robot, start_pose)
                    print(f"시작 자세 도착: interpolated steps={steps}", flush=True)
            print(
                "모터를 해제합니다. 팔을 손으로 받친 채 천천히 자세를 맞추고 "
                "로봇의 Teach 버튼을 한 번 누르세요.",
                flush=True,
            )
            robot.motor(-1, False)
            motors_released = True
            angles = wait_for_teach_click(robot, timeout_s=timeout_s)

        save_pose(template, output, pose_name, angles)
        print(f"saved {pose_name}={angles} -> {output}", flush=True)
        return angles
    finally:
        if robot is not None:
            robot.set_speed_joints(0, 0, 0, 0)
            if motors_released:
                robot.motor(-1, True)
            robot.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="물리 Teach 버튼으로 RaccoonBot 자세 저장")
    parser.add_argument("pose_name")
    parser.add_argument("--output", type=Path, default=Path("config/robot_poses.json"))
    parser.add_argument(
        "--template",
        type=Path,
        default=Path("config/robot_poses.template.json"),
    )
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--start-from",
        help="모터 해제 전에 이 이름의 저장된 자세로 안전하게 이동",
    )
    parser.add_argument("--start-speed", type=float, default=10.0)
    parser.add_argument(
        "--start-motion-mode",
        choices=("interpolated", "direct"),
        default="interpolated",
        help="저장된 시작 자세까지 이동하는 방식",
    )
    parser.add_argument(
        "--capture-current",
        action="store_true",
        help="모터를 해제하지 않고 현재 엔코더 값을 바로 저장",
    )
    parser.add_argument(
        "--confirm-manual-teaching",
        action="store_true",
        help="모터가 해제되어 팔을 직접 받쳐야 함을 확인",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if not 1 <= args.start_speed <= 30:
        parser.error("--start-speed must be within 1..30")
    if args.capture_current and args.start_from:
        parser.error("--start-from cannot be used with --capture-current")
    if not args.capture_current and not args.confirm_manual_teaching:
        parser.error("manual teaching requires --confirm-manual-teaching")

    try:
        from robomation import RaccoonBot
    except ImportError as exc:
        raise SystemExit("robomation package is not installed") from exc

    teach_pose(
        RaccoonBot,
        template=args.template,
        output=args.output,
        pose_name=args.pose_name,
        port=args.port,
        capture_current=args.capture_current,
        timeout_s=args.timeout,
        start_pose=load_pose(args.output, args.start_from) if args.start_from else None,
        start_speed=args.start_speed,
        start_motion_mode=args.start_motion_mode,
    )


if __name__ == "__main__":
    main()
