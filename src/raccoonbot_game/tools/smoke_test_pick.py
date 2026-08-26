from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from raccoonbot_game.robot.joint_motion import move_joints_interpolated
from raccoonbot_game.tools.probe_robot import DEFAULT_PORT, official_connection_state
from raccoonbot_game.tools.smoke_test_gripper import wait_for_end_effector
from raccoonbot_game.tools.smoke_test_motion import wait_for_battery
from raccoonbot_game.tools.smoke_test_transition import (
    load_taught_pose,
    max_joint_error,
    minimum_joint_limit_margin,
)
from raccoonbot_game.tools.teach_pose import validate_angles


def verify_reached(
    robot: Any,
    name: str,
    expected: list[float],
    *,
    tolerance: float,
    required_limit_margin: float,
) -> list[float]:
    actual = validate_angles(list(robot.encoder()))
    error = max_joint_error(actual, expected)
    margin = minimum_joint_limit_margin(actual)
    print(
        f"reached {name}={actual} max_error={error:.3f}deg "
        f"min_limit_margin={margin:.3f}deg",
        flush=True,
    )
    if error > tolerance:
        raise RuntimeError(f"{name} pose error is too large: {error:.3f}deg")
    if margin < required_limit_margin:
        raise RuntimeError(f"{name} is too close to a joint limit: {margin:.3f}deg")
    return actual


def move_and_verify(
    robot: Any,
    name: str,
    pose: list[float],
    *,
    tolerance: float,
    required_limit_margin: float,
    settle_s: float,
    sleeper: Callable[[float], None],
) -> list[float]:
    print(f"moving to {name}={pose}", flush=True)
    steps = move_joints_interpolated(robot, pose)
    print(f"interpolated {name} steps={steps}", flush=True)
    sleeper(settle_s)
    return verify_reached(
        robot,
        name,
        pose,
        tolerance=tolerance,
        required_limit_margin=required_limit_margin,
    )


def smoke_test(
    robot_factory: Callable[..., Any],
    *,
    port: str,
    transit: list[float],
    hover: list[float],
    grasp: list[float],
    speed: float,
    pose_prefix: str = "cell_1",
    actuate_gripper: bool = True,
    tolerance: float = 3.0,
    required_limit_margin: float = 5.0,
    settle_s: float = 0.5,
    gripper_settle_s: float = 1.5,
    sleeper: Callable[[float], None] = time.sleep,
) -> None:
    if not 1 <= speed <= 20:
        raise ValueError("speed must be within 1..20 for the pick smoke test")
    transit = validate_angles(transit)
    hover = validate_angles(hover)
    grasp = validate_angles(grasp)
    robot = None
    try:
        robot = robot_factory(port_name=port)
        if official_connection_state(robot) is False:
            raise RuntimeError("Mini Dongle+ is open, but no RaccoonBot is paired")
        battery = wait_for_battery(robot, sleeper=sleeper)
        if battery < 3.3:
            raise RuntimeError(f"battery voltage is too low for a pick test: {battery}V")
        if actuate_gripper:
            device = wait_for_end_effector(robot, sleeper=sleeper)
            if device != 4:
                raise RuntimeError(f"expected DC gripper device 4, detected device {device}")
        actual_start = validate_angles(list(robot.encoder()))
        start_error = max_joint_error(actual_start, transit)
        if start_error > 5.0:
            raise RuntimeError(f"robot is not near transit: max joint error {start_error:.3f}deg")

        robot.angle_max_speed(speed)
        if actuate_gripper:
            robot.place()
            sleeper(gripper_settle_s)
        print(f"start={actual_start} battery={battery}V speed={speed}", flush=True)

        move_and_verify(
            robot,
            f"{pose_prefix}_hover",
            hover,
            tolerance=tolerance,
            required_limit_margin=required_limit_margin,
            settle_s=settle_s,
            sleeper=sleeper,
        )
        move_and_verify(
            robot,
            f"{pose_prefix}_grasp",
            grasp,
            tolerance=tolerance,
            required_limit_margin=required_limit_margin,
            settle_s=settle_s,
            sleeper=sleeper,
        )

        if actuate_gripper:
            print("closing gripper", flush=True)
            robot.pick()
            sleeper(gripper_settle_s)
            if int(robot.end_effector_status()) != 1:
                raise RuntimeError("gripper did not report closed status")
        else:
            print("dry run: gripper remains unchanged", flush=True)

        move_and_verify(
            robot,
            f"{pose_prefix}_hover_with_piece",
            hover,
            tolerance=tolerance,
            required_limit_margin=required_limit_margin,
            settle_s=settle_s,
            sleeper=sleeper,
        )
        sleeper(1.0)
        move_and_verify(
            robot,
            f"{pose_prefix}_grasp_return",
            grasp,
            tolerance=tolerance,
            required_limit_margin=required_limit_margin,
            settle_s=settle_s,
            sleeper=sleeper,
        )

        if actuate_gripper:
            print("opening gripper", flush=True)
            robot.place()
            sleeper(gripper_settle_s)
            if int(robot.end_effector_status()) != 0:
                raise RuntimeError("gripper did not report open status")

        move_and_verify(
            robot,
            f"{pose_prefix}_hover_after_place",
            hover,
            tolerance=tolerance,
            required_limit_margin=required_limit_margin,
            settle_s=settle_s,
            sleeper=sleeper,
        )
        move_and_verify(
            robot,
            "transit",
            transit,
            tolerance=tolerance,
            required_limit_margin=required_limit_margin,
            settle_s=settle_s,
            sleeper=sleeper,
        )
    finally:
        if robot is not None:
            robot.set_speed_joints(0, 0, 0, 0)
            robot.dispose()


def pose_prefix_for(*, cell: int | None, stock: int | None) -> str:
    if cell is not None and stock is not None:
        raise ValueError("choose either cell or stock")
    if stock is not None:
        return f"stock_{stock}"
    return f"cell_{cell if cell is not None else 1}"


def main() -> None:
    parser = argparse.ArgumentParser(description="지정한 칸/대기 말의 제자리 pick-and-place 저속 점검")
    parser.add_argument("profile", type=Path)
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--cell", type=int, choices=range(1, 10))
    target.add_argument("--stock", type=int, choices=range(1, 4))
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--speed", type=float, default=10.0)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="hover/grasp 경로만 시험하고 그리퍼는 작동하지 않음",
    )
    parser.add_argument(
        "--allow-provisional-cell",
        action="store_true",
        help="재시험 중인 잠긴 셀 자세를 명시적으로 허용",
    )
    parser.add_argument("--confirm-motion", action="store_true")
    args = parser.parse_args()
    if not args.confirm_motion:
        parser.error("refusing pick motion without --confirm-motion")

    try:
        from robomation import RaccoonBot
    except ImportError as exc:
        raise SystemExit("robomation package is not installed") from exc

    pose_prefix = pose_prefix_for(cell=args.cell, stock=args.stock)
    smoke_test(
        RaccoonBot,
        port=args.port,
        transit=load_taught_pose(args.profile, "transit"),
        hover=load_taught_pose(
            args.profile,
            f"{pose_prefix}_hover",
            allow_provisional=args.allow_provisional_cell,
        ),
        grasp=load_taught_pose(
            args.profile,
            f"{pose_prefix}_grasp",
            allow_provisional=args.allow_provisional_cell,
        ),
        speed=args.speed,
        pose_prefix=pose_prefix,
        actuate_gripper=not args.dry_run,
    )
    print(
        f"{pose_prefix} pick smoke test complete; robot stopped and connection disposed",
        flush=True,
    )


if __name__ == "__main__":
    main()
