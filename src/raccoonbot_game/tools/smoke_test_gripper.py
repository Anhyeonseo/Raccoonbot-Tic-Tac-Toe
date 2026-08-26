from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from typing import Any

from raccoonbot_game.tools.probe_robot import DEFAULT_PORT, official_connection_state
from raccoonbot_game.tools.smoke_test_motion import wait_for_battery


def wait_for_end_effector(
    robot: Any,
    *,
    attempts: int = 20,
    interval_s: float = 0.1,
    sleeper: Callable[[float], None] = time.sleep,
) -> int:
    device = 0
    for attempt in range(attempts):
        device = int(robot.end_effector_device())
        if device != 0:
            return device
        if attempt < attempts - 1:
            sleeper(interval_s)
    raise RuntimeError("end effector was not detected")


def smoke_test(
    robot_factory: Callable[..., Any],
    *,
    port: str,
    settle_s: float = 1.5,
    sleeper: Callable[[float], None] = time.sleep,
) -> tuple[int, int, int]:
    if settle_s < 0.5:
        raise ValueError("settle time must be at least 0.5 seconds")
    robot = None
    try:
        robot = robot_factory(port_name=port)
        if official_connection_state(robot) is False:
            raise RuntimeError("Mini Dongle+ is open, but no RaccoonBot is paired")
        battery = wait_for_battery(robot, sleeper=sleeper)
        if battery < 3.3:
            raise RuntimeError(f"battery voltage is too low for a gripper test: {battery}V")
        device = wait_for_end_effector(robot, sleeper=sleeper)
        if device != 4:
            raise RuntimeError(f"expected DC gripper device 4, detected device {device}")

        robot.set_speed_joints(0, 0, 0, 0)
        print(f"battery={battery}V end_effector={device}; opening", flush=True)
        robot.place()
        sleeper(settle_s)
        opened_first = int(robot.end_effector_status())
        print(f"opened status={opened_first}; closing", flush=True)

        robot.pick()
        sleeper(settle_s)
        closed = int(robot.end_effector_status())
        print(f"closed status={closed}; opening again", flush=True)

        robot.place()
        sleeper(settle_s)
        opened_last = int(robot.end_effector_status())
        print(f"opened_again status={opened_last}", flush=True)
        return opened_first, closed, opened_last
    finally:
        if robot is not None:
            robot.set_speed_joints(0, 0, 0, 0)
            robot.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="RaccoonBot DC 그리퍼 열기·닫기·열기 점검")
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--settle", type=float, default=1.5)
    parser.add_argument(
        "--confirm-motion",
        action="store_true",
        help="실제 그리퍼가 움직인다는 것을 확인한 경우에만 지정",
    )
    args = parser.parse_args()
    if not args.confirm_motion:
        parser.error("refusing gripper motion without --confirm-motion")

    try:
        from robomation import RaccoonBot
    except ImportError as exc:
        raise SystemExit("robomation package is not installed") from exc

    smoke_test(RaccoonBot, port=args.port, settle_s=args.settle)
    print("gripper smoke test complete; arm stopped and connection disposed", flush=True)


if __name__ == "__main__":
    main()
