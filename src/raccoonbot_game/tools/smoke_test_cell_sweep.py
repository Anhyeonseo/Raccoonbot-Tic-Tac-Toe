from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
from typing import Any

from raccoonbot_game.robot.pose_profile import RobotPoseProfile
from raccoonbot_game.robot.robomation_driver import RobomationDriver
from raccoonbot_game.tools.probe_robot import DEFAULT_PORT, official_connection_state
from raccoonbot_game.tools.smoke_test_gripper import wait_for_end_effector
from raccoonbot_game.tools.smoke_test_motion import wait_for_battery


def cell_sweep_pose_sequence(
    *,
    first_cell: int = 1,
    last_cell: int = 9,
) -> list[tuple[str, str]]:
    """Return the pose/gripper sequence for moving one piece cell by cell."""
    if not 1 <= first_cell < last_cell <= 9:
        raise ValueError("cell sweep requires 1 <= first_cell < last_cell <= 9")

    commands: list[tuple[str, str]] = []
    for source in range(first_cell, last_cell):
        target = source + 1
        commands.extend(
            [
                ("move", f"cell_{source}_hover"),
                ("move", f"cell_{source}_grasp"),
                ("gripper", "close"),
                ("move", f"cell_{source}_hover"),
                ("move", "transit"),
                ("move", f"cell_{target}_hover"),
                ("move", f"cell_{target}_grasp"),
                ("gripper", "open"),
                ("move", f"cell_{target}_hover"),
                ("move", "transit"),
            ]
        )
    return commands


def execute_cell_sweep(
    driver: RobomationDriver,
    *,
    status_reader: Callable[[], int],
    first_cell: int = 1,
    last_cell: int = 9,
    reporter: Callable[[str], None] = print,
) -> None:
    total = last_cell - first_cell
    for segment, source in enumerate(range(first_cell, last_cell), start=1):
        target = source + 1
        reporter(f"[{segment}/{total}] cell_{source} -> cell_{target}")
        for kind, value in cell_sweep_pose_sequence(
            first_cell=source,
            last_cell=target,
        ):
            if kind == "move":
                driver.move_to(value)
            elif value == "close":
                driver.close_gripper()
                if status_reader() != 1:
                    raise RuntimeError(
                        f"gripper did not report closed after picking from cell_{source}"
                    )
            else:
                driver.open_gripper()
                if status_reader() != 0:
                    raise RuntimeError(
                        f"gripper did not report open after placing in cell_{target}"
                    )
        reporter(f"[{segment}/{total}] cell_{source} -> cell_{target} complete")


def cell_sweep_test(
    robot_factory: Callable[..., Any],
    *,
    profile: RobotPoseProfile,
    port: str,
) -> None:
    robot = None
    driver = None
    try:
        robot = robot_factory(port_name=port)
        if official_connection_state(robot) is False:
            raise RuntimeError("Mini Dongle+ is open, but no RaccoonBot is paired")
        battery = wait_for_battery(robot)
        if battery < 3.3:
            raise RuntimeError(f"battery voltage is too low for a cell sweep: {battery}V")
        device = wait_for_end_effector(robot)
        if device != 4:
            raise RuntimeError(f"expected DC gripper device 4, detected device {device}")

        actual_start = [float(value) for value in robot.encoder()]
        driver = RobomationDriver(profile, robot=robot, interpolate_moves=False)
        print(
            f"cell sweep ready: battery={battery}V speed={profile.max_speed:g} "
            f"camera=disabled connected_pose="
            f"{[round(value, 3) for value in actual_start]}",
            flush=True,
        )

        # The tested firmware resets the arm toward its connection pose when a
        # new official-package session opens. Enter the same high transit pose
        # used by the hardware game before approaching any board cell.
        driver.move_to("transit")

        driver.open_gripper()
        if int(robot.end_effector_status()) != 0:
            raise RuntimeError("gripper did not report open before the cell sweep")

        execute_cell_sweep(
            driver,
            status_reader=lambda: int(robot.end_effector_status()),
        )
        driver.move_to("home_high")
        driver.move_to("home")
        print("cell sweep complete: piece is in cell_9; robot returned home", flush=True)
    finally:
        if driver is not None:
            driver.stop()
        elif robot is not None:
            robot.set_speed_joints(0, 0, 0, 0)
        if robot is not None:
            robot.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="카메라 없이 말 하나를 1번부터 9번까지 순서대로 운반"
    )
    parser.add_argument("profile", type=Path)
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--confirm-motion", action="store_true")
    args = parser.parse_args()
    if not args.confirm_motion:
        parser.error("refusing cell sweep motion without --confirm-motion")

    try:
        from robomation import RaccoonBot
    except ImportError as exc:
        raise SystemExit("robomation package is not installed") from exc

    cell_sweep_test(
        RaccoonBot,
        profile=RobotPoseProfile.load(args.profile),
        port=args.port,
    )


if __name__ == "__main__":
    main()
