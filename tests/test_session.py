import random

import pytest

from raccoonbot_game.app.session import GameSession, RobotVerificationError, SessionStatus
from raccoonbot_game.game import Game, GameResult, Player
from raccoonbot_game.robot.motion import MotionPlanner, SimulatedRobot


def test_human_observation_drives_and_verifies_robot_turn() -> None:
    robot = SimulatedRobot()
    session = GameSession(MotionPlanner(robot), rng=random.Random(4))
    human_board = [Player.HUMAN, None, None, None, None, None, None, None, None]

    pending = session.accept_human_board(human_board)

    assert pending is not None
    assert session.status is SessionStatus.WAITING_FOR_ROBOT_VERIFICATION
    assert robot.commands[0] == "move:home"
    assert "move:stock_1_grasp" in robot.commands
    assert session.game.board.count(Player.ROBOT) == 0

    result = session.verify_robot_board(pending.expected_board)

    assert result is GameResult.IN_PROGRESS
    assert session.status is SessionStatus.WAITING_FOR_HUMAN
    assert session.game.board.count(Player.ROBOT) == 1


def test_failed_robot_verification_does_not_commit_move() -> None:
    session = GameSession(MotionPlanner(SimulatedRobot()), rng=random.Random(8))
    human_board = [None, None, None, None, Player.HUMAN, None, None, None, None]
    pending = session.accept_human_board(human_board)
    assert pending is not None

    with pytest.raises(RobotVerificationError, match="예상과 다릅니다"):
        session.verify_robot_board(human_board)

    assert session.game.board.count(Player.ROBOT) == 0
    assert session.pending_robot_turn is pending


def test_human_win_finishes_without_robot_motion() -> None:
    robot = SimulatedRobot()
    game = Game(
        board=[Player.HUMAN, Player.HUMAN, None, Player.ROBOT, Player.ROBOT, None, None, None, None],
        turn=Player.HUMAN,
    )
    session = GameSession(MotionPlanner(robot), game=game, rng=random.Random(1))
    board = list(game.board)
    board[2] = Player.HUMAN
    assert session.accept_human_board(board) is None
    assert session.status is SessionStatus.FINISHED
    assert session.game.result is GameResult.HUMAN_WIN
    assert robot.commands == []
