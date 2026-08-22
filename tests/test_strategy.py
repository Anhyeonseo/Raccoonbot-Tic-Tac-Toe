import random

import pytest

from raccoonbot_game.game import Action, Game, Player
from raccoonbot_game.strategy import AiPolicy, decide_robot_action


def test_policy_probabilities_are_validated() -> None:
    with pytest.raises(ValueError):
        AiPolicy(block_probability=1.1)
    with pytest.raises(ValueError):
        AiPolicy(best_move_probability=0.8, second_best_probability=0.3)


def test_robot_always_takes_immediate_win() -> None:
    game = Game(
        board=[
            Player.ROBOT,
            Player.ROBOT,
            None,
            Player.HUMAN,
            None,
            None,
            Player.HUMAN,
            None,
            None,
        ],
        turn=Player.ROBOT,
    )

    decision = decide_robot_action(
        game,
        policy=AiPolicy(block_probability=0.0, best_move_probability=0.0),
        rng=random.Random(5),
    )

    assert decision.action == Action(target=2)
    assert decision.reason == "immediate_win"


def test_robot_blocks_immediate_placement_threat_when_required() -> None:
    game = Game(
        board=[
            Player.HUMAN,
            Player.HUMAN,
            None,
            Player.ROBOT,
            None,
            None,
            None,
            None,
            None,
        ],
        turn=Player.ROBOT,
    )

    decision = decide_robot_action(
        game,
        policy=AiPolicy(block_probability=1.0),
        rng=random.Random(1),
    )

    assert decision.action == Action(target=2)
    assert decision.reason == "block_immediate_threat"


def test_default_random_probability_is_fifteen_percent() -> None:
    assert AiPolicy().random_move_probability == pytest.approx(0.15)

