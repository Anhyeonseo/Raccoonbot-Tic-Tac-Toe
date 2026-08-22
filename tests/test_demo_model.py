from raccoonbot_game.app.demo_model import DemoGame
from raccoonbot_game.game import Game, GamePhase, Player


def test_placement_click_runs_human_and_robot_turn() -> None:
    demo = DemoGame(seed=3)
    demo.click(0)
    assert demo.game.board.count(Player.HUMAN) == 1
    assert demo.game.board.count(Player.ROBOT) == 1
    assert demo.game.turn is Player.HUMAN


def test_occupied_cell_does_not_change_placement_board() -> None:
    demo = DemoGame(seed=3)
    demo.click(0)
    before = demo.game.board.copy()
    occupied = next(index for index, value in enumerate(before) if value is not None)
    demo.click(occupied)
    assert demo.game.board == before
    assert "이미 말" in demo.message


def test_movement_uses_select_then_any_empty_destination() -> None:
    demo = DemoGame(seed=5)
    demo.game = Game(
        board=[Player.HUMAN, Player.ROBOT, Player.HUMAN, Player.ROBOT, Player.HUMAN, None, None, None, Player.ROBOT],
        turn=Player.HUMAN,
        phase=GamePhase.MOVEMENT,
    )
    demo.click(0)
    assert demo.selected_source == 0
    demo.click(7)
    assert demo.game.board[0] is None
    assert demo.game.board[7] is Player.HUMAN


def test_reset_starts_clean_human_game() -> None:
    demo = DemoGame(seed=2)
    demo.click(4)
    demo.reset()
    assert demo.game.board == [None] * 9
    assert demo.game.turn is Player.HUMAN
