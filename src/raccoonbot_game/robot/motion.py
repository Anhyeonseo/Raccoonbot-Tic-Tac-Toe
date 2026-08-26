from __future__ import annotations

from dataclasses import dataclass, field

from .interface import RobotDriver


def _cell_name(index: int) -> str:
    if index not in range(9):
        raise ValueError("cell index must be between 0 and 8")
    return f"cell_{index + 1}"


def _stock_name(index: int) -> str:
    if index not in range(3):
        raise ValueError("stock index must be between 0 and 2")
    return f"stock_{index + 1}"


@dataclass
class MotionPlanner:
    """Emit a conservative pick-and-place sequence using taught pose names.

    ``home`` is the installation-specific camera-clear observation pose.
    ``transit`` is a compact intermediate pose used before crossing between the
    observation pose and any board/stock hover pose.
    """

    robot: RobotDriver

    def place_from_stock(self, stock: int, target: int) -> None:
        self._pick_and_place(_stock_name(stock), _cell_name(target))

    def move_piece(self, source: int, target: int) -> None:
        if source == target:
            raise ValueError("source and target must be different")
        self._pick_and_place(_cell_name(source), _cell_name(target))

    def _pick_and_place(self, source: str, target: str) -> None:
        self.robot.move_to("home")
        self.robot.open_gripper()
        self.robot.move_to("transit")
        self.robot.move_to(f"{source}_hover")
        self.robot.move_to(f"{source}_grasp")
        self.robot.close_gripper()
        self.robot.move_to(f"{source}_hover")
        # Never sweep a held piece directly across the board.  Folding through
        # the high transit pose keeps the gripper and payload clear of pieces
        # that may be standing in intervening cells.
        self.robot.move_to("transit")
        self.robot.move_to(f"{target}_hover")
        self.robot.move_to(f"{target}_grasp")
        self.robot.open_gripper()
        self.robot.move_to(f"{target}_hover")
        self.robot.move_to("transit")
        self.robot.move_to("home")


@dataclass
class SimulatedRobot:
    """Command logger used by desktop integration tests."""

    commands: list[str] = field(default_factory=list)

    def move_to(self, pose_name: str) -> None:
        self.commands.append(f"move:{pose_name}")

    def open_gripper(self) -> None:
        self.commands.append("gripper:open")

    def close_gripper(self) -> None:
        self.commands.append("gripper:close")

    def stop(self) -> None:
        self.commands.append("stop")
