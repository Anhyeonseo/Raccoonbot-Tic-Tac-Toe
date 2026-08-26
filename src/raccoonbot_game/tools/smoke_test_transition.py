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
from raccoonbot_game.tools.teach_pose import validate_angles


def load_taught_pose(
    path: Path,
    name: str,
    *,
    allow_provisional: bool = False,
) -> list[float]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    try:
        values = raw["poses"][name]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"unknown pose name: {name}") from exc
    if values is None:
        raise ValueError(f"pose is not taught: {name}")
    if name in raw.get("_provisional_poses", []) and not allow_provisional:
        raise ValueError(f"pose is provisional: {name}")
    return validate_angles(list(values))


def max_joint_error(actual: list[float], expected: list[float]) -> float:
    return max(abs(a - e) for a, e in zip(actual, expected))


def minimum_joint_limit_margin(angles: list[float]) -> float:
    return min(min(angle - low, high - angle) for angle, (low, high) in zip(angles, JOINT_LIMITS))


def smoke_test(
    robot_factory: Callable[..., Any],
    *,
    port: str,
    start_pose: list[float],
    target_pose: list[float],
    speed: float,
    start_tolerance: float = 5.0,
    reached_tolerance: float = 2.0,
    required_limit_margin: float = 5.0,
    target_dwell_s: float = 0.0,
    settle_s: float = 0.5,
    sleeper: Callable[[float], None] = time.sleep,
) -> tuple[list[float], list[float], list[float]]:
    if not 1 <= speed <= 60:
        raise ValueError("speed must be within 1..60 for the transition smoke test")
    start_pose = validate_angles(start_pose)
    target_pose = validate_angles(target_pose)
    robot = None
    try:
        robot = robot_factory(port_name=port)
        if official_connection_state(robot) is False:
            raise RuntimeError("Mini Dongle+ is open, but no RaccoonBot is paired")
        battery = wait_for_battery(robot, sleeper=sleeper)
        if battery < 3.3:
            raise RuntimeError(f"battery voltage is too low for a transition test: {battery}V")

        actual_start = validate_angles(list(robot.encoder()))
        error = max_joint_error(actual_start, start_pose)
        if error > start_tolerance:
            raise RuntimeError(
                f"robot is not near the expected start pose: max joint error {error:.3f}deg"
            )

        robot.angle_max_speed(speed)
        print(f"start={actual_start} battery={battery}V speed={speed}", flush=True)
        print(f"moving to target={target_pose}", flush=True)
        steps = move_joints_interpolated(robot, target_pose)
        print(f"interpolated move steps={steps}", flush=True)
        sleeper(settle_s)
        reached = validate_angles(list(robot.encoder()))
        reached_error = max_joint_error(reached, target_pose)
        limit_margin = minimum_joint_limit_margin(reached)
        print(
            f"reached={reached} max_error={reached_error:.3f}deg "
            f"min_limit_margin={limit_margin:.3f}deg",
            flush=True,
        )
        if reached_error > reached_tolerance:
            raise RuntimeError(f"target pose error is too large: {reached_error:.3f}deg")
        if limit_margin < required_limit_margin:
            raise RuntimeError(f"target pose is too close to a joint limit: {limit_margin:.3f}deg")
        if target_dwell_s > 0:
            print(f"holding target for {target_dwell_s:g}s", flush=True)
            sleeper(target_dwell_s)

        print(f"returning to start_pose={start_pose}", flush=True)
        steps = move_joints_interpolated(robot, start_pose)
        print(f"interpolated return steps={steps}", flush=True)
        sleeper(settle_s)
        returned = validate_angles(list(robot.encoder()))
        returned_error = max_joint_error(returned, start_pose)
        print(f"returned={returned} max_error={returned_error:.3f}deg", flush=True)
        if returned_error > reached_tolerance:
            raise RuntimeError(f"return pose error is too large: {returned_error:.3f}deg")
        return actual_start, reached, returned
    finally:
        if robot is not None:
            robot.set_speed_joints(0, 0, 0, 0)
            robot.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="두 teaching 자세 사이의 저속 왕복 점검")
    parser.add_argument("profile", type=Path)
    parser.add_argument("--from-pose", default="transit")
    parser.add_argument("--to-pose", default="home")
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--speed", type=float, default=5.0)
    parser.add_argument("--reached-tolerance", type=float, default=2.0)
    parser.add_argument("--target-dwell", type=float, default=0.0)
    parser.add_argument(
        "--allow-provisional-target",
        action="store_true",
        help="재시험 중인 임시 목표 자세만 명시적으로 허용",
    )
    parser.add_argument("--confirm-motion", action="store_true")
    args = parser.parse_args()
    if not args.confirm_motion:
        parser.error("refusing motion without --confirm-motion")
    if not 0.5 <= args.reached_tolerance <= 3.0:
        parser.error("--reached-tolerance must be within 0.5..3.0")
    if not 0 <= args.target_dwell <= 30:
        parser.error("--target-dwell must be within 0..30 seconds")

    try:
        from robomation import RaccoonBot
    except ImportError as exc:
        raise SystemExit("robomation package is not installed") from exc

    smoke_test(
        RaccoonBot,
        port=args.port,
        start_pose=load_taught_pose(args.profile, args.from_pose),
        target_pose=load_taught_pose(
            args.profile,
            args.to_pose,
            allow_provisional=args.allow_provisional_target,
        ),
        speed=args.speed,
        reached_tolerance=args.reached_tolerance,
        target_dwell_s=args.target_dwell,
    )
    print("transition smoke test complete; robot stopped and connection disposed", flush=True)


if __name__ == "__main__":
    main()
