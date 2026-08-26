import pytest

from raccoonbot_game.game import Player
from raccoonbot_game.tools.live_board import format_board


def test_format_board() -> None:
    board = (
        Player.ROBOT,
        Player.HUMAN,
        None,
        Player.ROBOT,
        Player.HUMAN,
        Player.ROBOT,
        None,
        Player.HUMAN,
        None,
    )

    assert format_board(board) == "Y R . / Y R Y / . R ."


def test_format_board_rejects_wrong_cell_count() -> None:
    with pytest.raises(ValueError, match="nine cells"):
        format_board((None,) * 8)
