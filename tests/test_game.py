import random

import pytest

from raccoonbot_game.ai import choose_robot_action
from raccoonbot_game.game import Action, Game, GamePhase, GameResult, Player


def play(game: Game, *targets: int) -> None:
    for target in targets:
        game.apply(Action(target=target))


def test_human_can_win_during_placement() -> None:
    game = Game()
    play(game, 0, 3, 1, 4, 2)

    assert game.result is GameResult.HUMAN_WIN
    assert game.phase is GamePhase.FINISHED


def test_game_enters_movement_after_six_placements() -> None:
    game = Game()
    play(game, 0, 1, 2, 3, 4, 8)

    assert game.phase is GamePhase.MOVEMENT
    assert game.turn is Player.HUMAN
    assert len(game.legal_actions()) == 9


def test_piece_can_move_to_any_empty_cell() -> None:
    game = Game()
    play(game, 0, 1, 2, 3, 4, 8)

    result = game.apply(Action(source=0, target=7))

    assert result is GameResult.IN_PROGRESS
    assert game.board[0] is None
    assert game.board[7] is Player.HUMAN


def test_player_cannot_move_opponents_piece() -> None:
    game = Game()
    play(game, 0, 1, 2, 3, 4, 8)

    with pytest.raises(ValueError, match="illegal action"):
        game.apply(Action(source=1, target=7))


def test_robot_always_takes_immediate_win_even_when_skill_is_zero() -> None:
    game = Game(board=[Player.ROBOT, Player.ROBOT, None, Player.HUMAN, None, None, None, None, None], turn=Player.ROBOT)

    action = choose_robot_action(game, skill=0.0, rng=random.Random(1))

    assert action == Action(target=2)


def test_movement_turn_limit_ends_game() -> None:
    game = Game(max_movement_turns=1)
    play(game, 0, 1, 2, 3, 4, 8)

    result = game.apply(Action(source=0, target=7))

    assert result is GameResult.DRAW_TURN_LIMIT
    assert game.phase is GamePhase.FINISHED

