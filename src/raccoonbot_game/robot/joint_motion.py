from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any


DEFAULT_MAX_JOINT_STEP_DEGREES = 6.0


def interpolate_joint_path(
    start: Sequence[float],
    target: Sequence[float],
    *,
    max_step_degrees: float = DEFAULT_MAX_JOINT_STEP_DEGREES,
) -> list[list[float]]:
    """Split a four-joint move into small synchronized joint-space waypoints."""

    if len(start) != 4 or len(target) != 4:
        raise ValueError("start and target must contain four joint angles")
    if max_step_degrees <= 0:
        raise ValueError("max_step_degrees must be positive")

    start_values = [float(value) for value in start]
    target_values = [float(value) for value in target]
    maximum_delta = max(
        abs(target_value - start_value)
        for start_value, target_value in zip(start_values, target_values)
    )
    steps = max(1, math.ceil(maximum_delta / max_step_degrees))
    path = []
    for step in range(1, steps + 1):
        ratio = step / steps
        waypoint = [
            start_value + (target_value - start_value) * ratio
            for start_value, target_value in zip(start_values, target_values)
        ]
        path.append(waypoint)
    path[-1] = target_values
    return path


def move_joints_interpolated(
    robot: Any,
    target: Sequence[float],
    *,
    max_step_degrees: float = DEFAULT_MAX_JOINT_STEP_DEGREES,
) -> int:
    """Move through small waypoints to limit sequential per-joint target jumps."""

    start = [float(value) for value in robot.encoder()]
    path = interpolate_joint_path(
        start,
        target,
        max_step_degrees=max_step_degrees,
    )
    for waypoint in path:
        robot.set_angle_joints(*waypoint, wait=True)
    return len(path)
