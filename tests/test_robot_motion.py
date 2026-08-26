import pytest

from raccoonbot_game.robot.motion import MotionPlanner, SimulatedRobot


def test_stock_to_cell_uses_safe_hover_sequence() -> None:
    robot = SimulatedRobot()
    MotionPlanner(robot).place_from_stock(0, 4)
    assert robot.commands == [
        "move:home",
        "gripper:open",
        "move:transit",
        "move:stock_1_hover",
        "move:stock_1_grasp",
        "gripper:close",
        "move:stock_1_hover",
        "move:transit",
        "move:cell_5_hover",
        "move:cell_5_grasp",
        "gripper:open",
        "move:cell_5_hover",
        "move:transit",
        "move:home",
    ]


def test_board_move_has_no_adjacency_restriction() -> None:
    robot = SimulatedRobot()
    MotionPlanner(robot).move_piece(0, 8)
    assert "move:cell_1_grasp" in robot.commands
    assert "move:cell_9_grasp" in robot.commands


def test_invalid_pose_indices_are_rejected_before_motion() -> None:
    robot = SimulatedRobot()
    with pytest.raises(ValueError):
        MotionPlanner(robot).move_piece(-1, 8)
    assert robot.commands == []
