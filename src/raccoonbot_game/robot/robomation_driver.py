from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from typing import Any

from .joint_motion import DEFAULT_MAX_JOINT_STEP_DEGREES, move_joints_interpolated
from .pose_profile import RobotPoseProfile


DEFAULT_REACHED_TOLERANCE_DEGREES = 3.0
DEFAULT_MOVE_RETRIES = 2


class RobomationDriver:
    """Adapter from the official ``robomation.RaccoonBot`` to RobotDriver."""

    def __init__(
        self,
        profile: RobotPoseProfile,
        *,
        port_name: str | None = None,
        address: str | None = None,
        robot: Any | None = None,
        gripper_settle_s: float = 0.8,
        joint_step_degrees: float = DEFAULT_MAX_JOINT_STEP_DEGREES,
        interpolate_moves: bool = False,
        reached_tolerance_degrees: float = DEFAULT_REACHED_TOLERANCE_DEGREES,
        move_retries: int = DEFAULT_MOVE_RETRIES,
        before_action: Callable[[], None] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if gripper_settle_s < 0:
            raise ValueError("gripper_settle_s cannot be negative")
        if joint_step_degrees <= 0:
            raise ValueError("joint_step_degrees must be positive")
        if reached_tolerance_degrees <= 0:
            raise ValueError("reached_tolerance_degrees must be positive")
        if isinstance(move_retries, bool) or not isinstance(move_retries, int):
            raise TypeError("move_retries must be an integer")
        if move_retries < 0:
            raise ValueError("move_retries cannot be negative")
        if robot is None:
            try:
                from robomation import RaccoonBot
            except ImportError as exc:
                raise RuntimeError("install the official robomation package on the Jetson") from exc
            connect_args: dict[str, str] = {}
            if port_name is not None:
                connect_args["port_name"] = port_name
            if address is not None:
                parameters = inspect.signature(RaccoonBot).parameters
                if "address" not in parameters:
                    raise RuntimeError(
                        "installed robomation package does not support address selection; "
                        "use port_name or upgrade robomation"
                    )
                connect_args["address"] = address
            robot = RaccoonBot(**connect_args)
        self.profile = profile
        self.robot = robot
        self.gripper_settle_s = gripper_settle_s
        self.joint_step_degrees = joint_step_degrees
        self.interpolate_moves = interpolate_moves
        self.reached_tolerance_degrees = reached_tolerance_degrees
        self.move_retries = move_retries
        self._before_action = before_action or (lambda: None)
        self._sleep = sleeper
        self.robot.angle_max_speed(profile.max_speed)

    def move_to(self, pose_name: str) -> None:
        self._before_action()
        target = self.profile.pose(pose_name)
        attempts = self.move_retries + 1
        for attempt in range(1, attempts + 1):
            if self.interpolate_moves:
                move_joints_interpolated(
                    self.robot,
                    target,
                    max_step_degrees=self.joint_step_degrees,
                )
            else:
                self.robot.set_angle_joints(*target, wait=True)

            actual = [float(value) for value in self.robot.encoder()]
            joint_errors = [
                abs(actual_value - target_value)
                for actual_value, target_value in zip(actual, target)
            ]
            maximum_error = max(joint_errors)
            if maximum_error <= self.reached_tolerance_degrees:
                if attempt > 1:
                    print(
                        f"motion retry recovered pose={pose_name!r} "
                        f"attempt={attempt}/{attempts} "
                        f"joint_errors_deg={[round(value, 3) for value in joint_errors]}",
                        flush=True,
                    )
                return

            print(
                f"motion target not reached pose={pose_name!r} "
                f"attempt={attempt}/{attempts} "
                f"target={[round(value, 3) for value in target]} "
                f"actual={[round(value, 3) for value in actual]} "
                f"joint_errors_deg={[round(value, 3) for value in joint_errors]}",
                flush=True,
            )

        self.stop()
        raise RuntimeError(
            f"robot did not reach pose {pose_name!r} after {attempts} attempts: "
            f"max joint error {maximum_error:.3f}deg "
            f"(tolerance {self.reached_tolerance_degrees:.3f}deg; "
            f"joint errors {[round(value, 3) for value in joint_errors]}deg)"
        )

    def open_gripper(self) -> None:
        self._before_action()
        self.robot.place()
        self._sleep(self.gripper_settle_s)

    def close_gripper(self) -> None:
        self._before_action()
        self.robot.pick()
        self._sleep(self.gripper_settle_s)

    def stop(self) -> None:
        """Stop commanded motion without unlocking the arm joints."""
        self.robot.set_speed_joints(0, 0, 0, 0)

    def dispose(self) -> None:
        self.robot.dispose()
