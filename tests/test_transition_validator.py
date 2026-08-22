import pytest

from raccoonbot_game.game import Action, GamePhase, Player
from raccoonbot_game.vision.transition_validator import (
    InvalidTransition,
    TransitionErrorCode,
    infer_action,
)


E = None
H = Player.HUMAN
R = Player.ROBOT


def test_infers_one_piece_placement() -> None:
    before = [E, E, E, E, R, E, E, E, E]
    after = [E, E, H, E, R, E, E, E, E]

    assert infer_action(before, after, phase=GamePhase.PLACEMENT) == Action(target=2)


def test_infers_free_movement_to_any_empty_cell() -> None:
    before = [H, R, H, R, H, E, E, E, R]
    after = [E, R, H, R, H, E, E, H, R]

    assert infer_action(before, after, phase=GamePhase.MOVEMENT) == Action(source=0, target=7)


def test_rejects_moving_two_pieces() -> None:
    before = [H, R, H, R, H, E, E, E, R]
    after = [E, R, E, R, H, H, E, H, R]

    with pytest.raises(InvalidTransition) as error:
        infer_action(before, after, phase=GamePhase.MOVEMENT)

    assert error.value.code is TransitionErrorCode.TOO_MANY_CHANGES


def test_rejects_opponent_piece_change() -> None:
    before = [H, R, H, R, H, E, E, E, R]
    after = [H, E, H, R, H, R, E, E, R]

    with pytest.raises(InvalidTransition) as error:
        infer_action(before, after, phase=GamePhase.MOVEMENT)

    assert error.value.code is TransitionErrorCode.WRONG_PLAYER

