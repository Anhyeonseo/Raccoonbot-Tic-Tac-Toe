from types import SimpleNamespace

import numpy as np
import pytest

from raccoonbot_game.game import Action, GameResult, Player
from raccoonbot_game.tools.play_hardware import (
    capture_stable_board,
    format_action,
    reconstruct_placement_game,
    require_empty_board,
    result_message,
)


class FakeCapture:
    def __init__(self, count: int):
        self.remaining = count

    def read(self):
        self.remaining -= 1
        return True, np.zeros((2, 2, 3), dtype=np.uint8)


class FakeObservation:
    def __init__(self, board):
        self.board = board
        self.warped_image = np.zeros((3, 3, 3), dtype=np.uint8)
        self.is_complete = True

    def as_game_board(self):
        return self.board


class FakeObserver:
    def __init__(self, boards):
        self.boards = iter(boards)

    def observe(self, _frame):
        return FakeObservation(next(self.boards))


def test_capture_stable_board_requires_repeated_matching_frames() -> None:
    empty = (None,) * 9
    yellow_at_nine = (None,) * 8 + (Player.ROBOT,)
    boards = [empty, yellow_at_nine, yellow_at_nine, yellow_at_nine, yellow_at_nine]

    board, warped = capture_stable_board(
        FakeCapture(6),
        FakeObserver(boards),
        warmup_frames=1,
        max_frames=5,
    )

    assert board == yellow_at_nine
    assert warped.shape == (3, 3, 3)


def test_require_empty_board_reports_occupied_cells() -> None:
    require_empty_board((None,) * 9)
    with pytest.raises(RuntimeError, match=r"\[2, 9\]"):
        require_empty_board((None, Player.HUMAN, None, None, None, None, None, None, Player.ROBOT))


def test_hardware_game_messages_use_human_cell_numbers() -> None:
    assert format_action(Action(target=4)) == "5번 칸에 배치"
    assert format_action(Action(source=4, target=8)) == "5번 → 9번 이동"
    assert result_message(GameResult.HUMAN_WIN) == "사람 승리!"


def test_reconstruct_placement_game_restores_next_robot_turn() -> None:
    board = (None, None, None, None, Player.HUMAN, None, None, Player.ROBOT, Player.HUMAN)

    game = reconstruct_placement_game(board)

    assert tuple(game.board) == board
    assert game.turn is Player.ROBOT


def test_reconstruct_placement_game_rejects_invalid_counts() -> None:
    with pytest.raises(ValueError, match="red=0 yellow=1"):
        reconstruct_placement_game((Player.ROBOT,) + (None,) * 8)
