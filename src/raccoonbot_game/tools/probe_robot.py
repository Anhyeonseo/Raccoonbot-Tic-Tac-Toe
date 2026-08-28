from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from typing import Any


DEFAULT_PORT = "/dev/serial/by-id/usb-Robomation_Mini_Dongle+_CCC0C21B94C3-if00"


def read_snapshot(robot: Any) -> dict[str, Any]:
    """Read sensors without explicitly requesting a joint or gripper motion."""
    return {
        "encoders": robot.encoder(),
        "battery_v": robot.battery(),
        "signal_dbm": robot.signal_strength(),
        "end_effector_device": robot.end_effector_device(),
        "end_effector_status": robot.end_effector_status(),
    }


def format_snapshot(index: int, snapshot: dict[str, Any]) -> str:
    return (
        f"sample={index} encoders={snapshot['encoders']} "
        f"battery={snapshot['battery_v']}V signal={snapshot['signal_dbm']}dBm "
        f"end_effector={snapshot['end_effector_device']} "
        f"status={snapshot['end_effector_status']}"
    )


def official_connection_state(robot: Any) -> bool | None:
    """Return the official package connection state when that API is available."""
    roboid = getattr(robot, "_roboid", None)
    connector = getattr(roboid, "_connector", None)
    is_connected = getattr(connector, "is_connected", None)
    if not callable(is_connected):
        return None
    return bool(is_connected())


def probe(
    robot_factory: Callable[..., Any],
    *,
    port: str,
    samples: int,
    interval_s: float,
    sleeper: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    robot = None
    snapshots: list[dict[str, Any]] = []
    try:
        # No angle, home, pick, or place command is issued by this probe. On the
        # tested RaccoonBot firmware, however, opening a new official-package
        # connection can reset J1 toward 0 degrees. Treat connection itself as
        # a potentially visible hardware action.
        robot = robot_factory(port_name=port)
        if official_connection_state(robot) is False:
            raise RuntimeError("Mini Dongle+ is open, but no RaccoonBot is paired")
        for index in range(1, samples + 1):
            snapshot = read_snapshot(robot)
            snapshots.append(snapshot)
            print(format_snapshot(index, snapshot), flush=True)
            if index < samples:
                sleeper(interval_s)
        return snapshots
    finally:
        if robot is not None:
            robot.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="명시적 이동 명령 없이 RaccoonBot 연결 및 센서 값 확인"
    )
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--interval", type=float, default=0.5)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("--samples must be at least one")
    if args.interval < 0:
        parser.error("--interval cannot be negative")

    try:
        from robomation import RaccoonBot
    except ImportError as exc:
        raise SystemExit("robomation package is not installed") from exc

    print(
        f"connecting port={args.port} (no explicit pose or gripper command; "
        "connection may reset J1 toward 0deg)",
        flush=True,
    )
    probe(
        RaccoonBot,
        port=args.port,
        samples=args.samples,
        interval_s=args.interval,
    )
    print("probe complete; connection disposed", flush=True)


if __name__ == "__main__":
    main()
