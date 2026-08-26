from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from typing import Any

from raccoonbot_game.robot.joint_motion import move_joints_interpolated
from raccoonbot_game.robot.pose_profile import JOINT_LIMITS
from raccoonbot_game.tools.probe_robot import DEFAULT_PORT, official_connection_state


def build_target(start: list[float], joint: int, delta: float) -> list[float]:
    if len(start) != 4:
        raise RuntimeError(f"expected four encoder values, got {start}")
    if joint not in (1, 2, 3, 4):
        raise ValueError("joint must be within 1..4")
    if not 0 < abs(delta) <= 5:
        raise ValueError("absolute delta must be within 0..5 degrees")
    target = [float(value) for value in start]
    target[joint - 1] += delta
    low, high = JOINT_LIMITS[joint - 1]
    if not low <= target[joint - 1] <= high:
        raise RuntimeError(f"target J{joint} is outside {low}..{high}: {target[joint - 1]}")
    return target


def wait_for_battery(
    robot: Any,
    *,
    attempts: int = 20,
    interval_s: float = 0.1,
    sleeper: Callable[[float], None] = time.sleep,
) -> float:
    """Wait for a default sensory packet after the BLE connection becomes ready."""
    battery = 0.0
    for attempt in range(attempts):
        battery = float(robot.battery())
        if battery >= 2.0:
            return battery
        if attempt < attempts - 1:
            sleeper(interval_s)
    raise RuntimeError(f"battery sensor did not become ready: {battery}V")


def smoke_test(
    robot_factory: Callable[..., Any],
    *,
    port: str,
    joint: int,
    delta: float,
    speed: float,
    settle_s: float = 0.5,
    sleeper: Callable[[float], None] = time.sleep,
) -> tuple[list[float], list[float], list[float]]:
    if not 1 <= speed <= 10:
        raise ValueError("speed must be within 1..10 for the smoke test")
    robot = None
    try:
        robot = robot_factory(port_name=port)
        if official_connection_state(robot) is False:
            raise RuntimeError("Mini Dongle+ is open, but no RaccoonBot is paired")
        battery = wait_for_battery(robot, sleeper=sleeper)
        if battery < 3.3:
            raise RuntimeError(f"battery voltage is too low for a motion test: {battery}V")

        start = [float(value) for value in robot.encoder()]
        target = build_target(start, joint, delta)
        print(f"start={start} battery={battery}V", flush=True)
        print(f"moving J{joint} delta={delta:+g}deg target={target} speed={speed}", flush=True)
        robot.angle_max_speed(speed)
        steps = move_joints_interpolated(robot, target)
        print(f"interpolated move steps={steps}", flush=True)
        sleeper(settle_s)
        reached = [float(value) for value in robot.encoder()]
        print(f"reached={reached}", flush=True)

        print(f"returning to start={start}", flush=True)
        steps = move_joints_interpolated(robot, start)
        print(f"interpolated return steps={steps}", flush=True)
        sleeper(settle_s)
        returned = [float(value) for value in robot.encoder()]
        print(f"returned={returned}", flush=True)
        return start, reached, returned
    finally:
        if robot is not None:
            robot.set_speed_joints(0, 0, 0, 0)
            robot.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="RaccoonBot 단일 관절 저속 왕복 점검")
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--joint", type=int, default=1)
    parser.add_argument("--delta", type=float, default=3.0)
    parser.add_argument("--speed", type=float, default=5.0)
    parser.add_argument(
        "--confirm-motion",
        action="store_true",
        help="실제 로봇이 움직인다는 것을 확인한 경우에만 지정",
    )
    args = parser.parse_args()
    if not args.confirm_motion:
        parser.error("refusing motion without --confirm-motion")

    try:
        from robomation import RaccoonBot
    except ImportError as exc:
        raise SystemExit("robomation package is not installed") from exc

    smoke_test(
        RaccoonBot,
        port=args.port,
        joint=args.joint,
        delta=args.delta,
        speed=args.speed,
    )
    print("motion smoke test complete; robot stopped and connection disposed", flush=True)


if __name__ == "__main__":
    main()
