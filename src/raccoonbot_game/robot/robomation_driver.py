from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

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
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if gripper_settle_s < 0:
            raise ValueError("gripper_settle_s cannot be negative")
        if robot is None:
            try:
                from robomation import RaccoonBot
            except ImportError as exc:
                raise RuntimeError("install the official robomation package on the Jetson") from exc
            robot = RaccoonBot(port_name=port_name, address=address)
        self.profile = profile
        self.robot = robot
        self.gripper_settle_s = gripper_settle_s
        self._sleep = sleeper
        self.robot.angle_max_speed(profile.max_speed)

    def move_to(self, pose_name: str) -> None:
        self.robot.set_angle_joints(*self.profile.pose(pose_name), wait=True)

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
