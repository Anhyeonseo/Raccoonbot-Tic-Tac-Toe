from __future__ import annotations

from typing import Protocol


class RobotDriver(Protocol):
    """Small boundary to isolate the future RaccoonBot SDK adapter."""

    def move_to(self, pose_name: str) -> None: ...

    def open_gripper(self) -> None: ...

    def close_gripper(self) -> None: ...

    def stop(self) -> None: ...
