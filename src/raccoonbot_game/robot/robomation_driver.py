from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from typing import Any

from .joint_motion import DEFAULT_MAX_JOINT_STEP_DEGREES, move_joints_interpolated
from .pose_profile import RobotPoseProfile


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
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if gripper_settle_s < 0:
            raise ValueError("gripper_settle_s cannot be negative")
        if joint_step_degrees <= 0:
            raise ValueError("joint_step_degrees must be positive")
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
        self._sleep = sleeper
        self.robot.angle_max_speed(profile.max_speed)

    def move_to(self, pose_name: str) -> None:
        move_joints_interpolated(
            self.robot,
            self.profile.pose(pose_name),
            max_step_degrees=self.joint_step_degrees,
        )

    def open_gripper(self) -> None:
        self.robot.place()
        self._sleep(self.gripper_settle_s)

    def close_gripper(self) -> None:
        self.robot.pick()
        self._sleep(self.gripper_settle_s)

    def stop(self) -> None:
        """Stop commanded motion without unlocking the arm joints."""
        self.robot.set_speed_joints(0, 0, 0, 0)

    def dispose(self) -> None:
        self.robot.dispose()
