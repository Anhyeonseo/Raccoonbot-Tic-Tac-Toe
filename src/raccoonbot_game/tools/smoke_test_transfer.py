from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from raccoonbot_game.tools.probe_robot import DEFAULT_PORT, official_connection_state
from raccoonbot_game.tools.smoke_test_gripper import wait_for_end_effector
from raccoonbot_game.tools.smoke_test_motion import wait_for_battery
from raccoonbot_game.tools.smoke_test_pick import move_and_verify
from raccoonbot_game.tools.smoke_test_transition import load_taught_pose, max_joint_error
from raccoonbot_game.tools.teach_pose import validate_angles


def transfer_test(
    robot_factory: Callable[..., Any],
    *,
    port: str,
    transit: list[float],
    source_hover: list[float],
    source_grasp: list[float],
    target_hover: list[float],
    target_grasp: list[float],
    speed: float,
    source_name: str,
    target_name: str,
    tolerance: float = 3.0,
    required_limit_margin: float = 5.0,
    settle_s: float = 0.5,
    gripper_settle_s: float = 1.5,
    sleeper: Callable[[float], None] = time.sleep,
) -> None:
    if not 1 <= speed <= 60:
        raise ValueError("speed must be within 1..60 for the transfer test")
    transit = validate_angles(transit)
    source_hover = validate_angles(source_hover)
    source_grasp = validate_angles(source_grasp)
    target_hover = validate_angles(target_hover)
    target_grasp = validate_angles(target_grasp)
    robot = None
    try:
        robot = robot_factory(port_name=port)
        if official_connection_state(robot) is False:
            raise RuntimeError("Mini Dongle+ is open, but no RaccoonBot is paired")
        battery = wait_for_battery(robot, sleeper=sleeper)
        if battery < 3.3:
            raise RuntimeError(f"battery voltage is too low for a transfer test: {battery}V")
        device = wait_for_end_effector(robot, sleeper=sleeper)
        if device != 4:
            raise RuntimeError(f"expected DC gripper device 4, detected device {device}")
        actual_start = validate_angles(list(robot.encoder()))
        start_error = max_joint_error(actual_start, transit)
        if start_error > 5.0:
            raise RuntimeError(f"robot is not near transit: max joint error {start_error:.3f}deg")

        robot.angle_max_speed(speed)
        robot.place()
        sleeper(gripper_settle_s)
        print(
            f"start={actual_start} battery={battery}V speed={speed} "
            f"transfer={source_name}->{target_name}",
            flush=True,
        )

        move_and_verify(
            robot,
            f"{source_name}_hover",
            source_hover,
            tolerance=tolerance,
            required_limit_margin=required_limit_margin,
            settle_s=settle_s,
            sleeper=sleeper,
        )
        move_and_verify(
            robot,
            f"{source_name}_grasp",
            source_grasp,
            tolerance=tolerance,
            required_limit_margin=required_limit_margin,
            settle_s=settle_s,
            sleeper=sleeper,
        )
        print("closing gripper", flush=True)
        robot.pick()
        sleeper(gripper_settle_s)
        if int(robot.end_effector_status()) != 1:
            raise RuntimeError("gripper did not report closed status")

        move_and_verify(
            robot,
            f"{source_name}_hover_with_piece",
            source_hover,
            tolerance=tolerance,
            required_limit_margin=required_limit_margin,
            settle_s=settle_s,
            sleeper=sleeper,
        )
        move_and_verify(
            robot,
            "transit_with_piece",
            transit,
            tolerance=tolerance,
            required_limit_margin=required_limit_margin,
            settle_s=settle_s,
            sleeper=sleeper,
        )
        move_and_verify(
            robot,
            f"{target_name}_hover_with_piece",
            target_hover,
            tolerance=tolerance,
            required_limit_margin=required_limit_margin,
            settle_s=settle_s,
            sleeper=sleeper,
        )
        move_and_verify(
            robot,
            f"{target_name}_grasp",
            target_grasp,
            tolerance=tolerance,
            required_limit_margin=required_limit_margin,
            settle_s=settle_s,
            sleeper=sleeper,
        )
        print("opening gripper", flush=True)
        robot.place()
        sleeper(gripper_settle_s)
        if int(robot.end_effector_status()) != 0:
            raise RuntimeError("gripper did not report open status")

        move_and_verify(
            robot,
            f"{target_name}_hover_after_place",
            target_hover,
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


def source_name_for(*, stock: int | None, from_cell: int | None) -> str:
    if stock is not None and from_cell is not None:
        raise ValueError("choose either stock or from-cell")
    if stock is not None:
        return f"stock_{stock}"
    if from_cell is not None:
        return f"cell_{from_cell}"
    raise ValueError("a stock or from-cell source is required")


def main() -> None:
    parser = argparse.ArgumentParser(description="대기 위치/보드 칸의 말을 지정한 보드 칸으로 실제 운반")
    parser.add_argument("profile", type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--stock", type=int, choices=range(1, 4))
    source.add_argument("--from-cell", type=int, choices=range(1, 10))
    parser.add_argument("--cell", type=int, choices=range(1, 10), required=True)
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--speed", type=float, default=10.0)
    parser.add_argument("--confirm-motion", action="store_true")
    args = parser.parse_args()
    if not args.confirm_motion:
        parser.error("refusing transfer motion without --confirm-motion")

    try:
        from robomation import RaccoonBot
    except ImportError as exc:
        raise SystemExit("robomation package is not installed") from exc

    if args.from_cell == args.cell:
        parser.error("source and target cells must be different")
    source_name = source_name_for(stock=args.stock, from_cell=args.from_cell)
    target_name = f"cell_{args.cell}"
    transfer_test(
        RaccoonBot,
        port=args.port,
        transit=load_taught_pose(args.profile, "transit"),
        source_hover=load_taught_pose(args.profile, f"{source_name}_hover"),
        source_grasp=load_taught_pose(args.profile, f"{source_name}_grasp"),
        target_hover=load_taught_pose(args.profile, f"{target_name}_hover"),
        target_grasp=load_taught_pose(args.profile, f"{target_name}_grasp"),
        speed=args.speed,
        source_name=source_name,
        target_name=target_name,
    )
    print(
        f"transfer {source_name}->{target_name} complete; robot stopped and connection disposed",
        flush=True,
    )


if __name__ == "__main__":
    main()
