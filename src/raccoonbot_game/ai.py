from __future__ import annotations

import random

from .game import Action, Game, GameResult, Player, WINNING_LINES


def choose_robot_action(
    game: Game,
    *,
    skill: float = 0.7,
    rng: random.Random | None = None,
) -> Action:
    """Choose a competent but intentionally imperfect robot action.

    Immediate wins are always taken. Otherwise ``skill`` is the probability of
    selecting one of the highest-scoring actions instead of a random legal move.
    """

    if game.turn is not Player.ROBOT:
        raise ValueError("the robot can only choose an action on its turn")
    if not 0.0 <= skill <= 1.0:
        raise ValueError("skill must be between 0.0 and 1.0")

    rng = rng or random.Random()
    actions = game.legal_actions()
    if not actions:
        raise ValueError("the game has no legal robot actions")

    scored = [(action, _score_action(game, action)) for action in actions]
    winning = [action for action, score in scored if score >= 10_000]
    if winning:
        return rng.choice(winning)

    if rng.random() > skill:
        return rng.choice(actions)

    best_score = max(score for _, score in scored)
    best = [action for action, score in scored if score == best_score]
    return rng.choice(best)


def _score_action(game: Game, action: Action) -> int:
    candidate = game.clone()
    result = candidate.apply(action)
    if result is GameResult.ROBOT_WIN:
        return 10_000

    score = 0
    for line in WINNING_LINES:
        robot_count = sum(candidate.board[index] is Player.ROBOT for index in line)
        human_count = sum(candidate.board[index] is Player.HUMAN for index in line)
        empty_count = 3 - robot_count - human_count

        if human_count == 0:
            score += robot_count * robot_count * 10 + empty_count
        if robot_count == 0 and human_count == 2 and empty_count == 1:
            score -= 80

    if candidate.board[4] is Player.ROBOT:
        score += 8
    return score

