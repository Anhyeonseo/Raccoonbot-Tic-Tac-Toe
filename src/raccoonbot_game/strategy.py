from __future__ import annotations

import random
from dataclasses import dataclass

from .game import Action, Game, GameResult, Player, WINNING_LINES


@dataclass(frozen=True, slots=True)
class AiPolicy:
    """Probabilities controlling the intentionally imperfect booth AI."""

    block_probability: float = 0.7
    best_move_probability: float = 0.6
    second_best_probability: float = 0.25

    def __post_init__(self) -> None:
        for name, value in (
            ("block_probability", self.block_probability),
            ("best_move_probability", self.best_move_probability),
            ("second_best_probability", self.second_best_probability),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0.0 and 1.0")
        if self.best_move_probability + self.second_best_probability > 1.0:
            raise ValueError("best and second-best probabilities cannot exceed 1.0")

    @property
    def random_move_probability(self) -> float:
        return 1.0 - self.best_move_probability - self.second_best_probability


@dataclass(frozen=True, slots=True)
class AiDecision:
    action: Action
    reason: str
    score: int
    used_randomness: bool


def decide_robot_action(
    game: Game,
    *,
    policy: AiPolicy | None = None,
    rng: random.Random | None = None,
) -> AiDecision:
    """Choose a competent but intentionally fallible robot action.

    Immediate wins are always taken. An immediate human threat is blocked
    according to ``block_probability``. Other actions mix best-scoring,
    second-best, and fully random legal choices.
    """

    if game.turn is not Player.ROBOT:
        raise ValueError("the robot can only choose an action on its turn")

    policy = policy or AiPolicy()
    rng = rng or random.Random()
    actions = game.legal_actions()
    if not actions:
        raise ValueError("the game has no legal robot actions")

    scored = [(action, _score_action(game, action)) for action in actions]

    winning = [item for item in scored if _result_after(game, item[0]) is GameResult.ROBOT_WIN]
    if winning:
        action, score = rng.choice(winning)
        return AiDecision(action, "immediate_win", score, False)

    if _count_winning_actions(game, Player.HUMAN):
        safe = [
            item
            for item in scored
            if _human_wins_after_robot_action(game, item[0]) == 0
        ]
        if safe and rng.random() < policy.block_probability:
            best_score = max(score for _, score in safe)
            choices = [item for item in safe if item[1] == best_score]
            action, score = rng.choice(choices)
            return AiDecision(action, "block_immediate_threat", score, False)

    score_levels = sorted({score for _, score in scored}, reverse=True)
    best_score = score_levels[0]
    second_score = score_levels[1] if len(score_levels) > 1 else best_score
    roll = rng.random()

    if roll < policy.best_move_probability:
        pool = [item for item in scored if item[1] == best_score]
        reason = "best_scored_move"
        used_randomness = False
    elif roll < policy.best_move_probability + policy.second_best_probability:
        pool = [item for item in scored if item[1] == second_score]
        reason = "second_best_move"
        used_randomness = True
    else:
        pool = scored
        reason = "random_legal_move"
        used_randomness = True

    action, score = rng.choice(pool)
    return AiDecision(action, reason, score, used_randomness)


def _result_after(game: Game, action: Action) -> GameResult:
    candidate = game.clone()
    return candidate.apply(action)


def _human_wins_after_robot_action(game: Game, action: Action) -> int:
    candidate = game.clone()
    candidate.apply(action)
    if candidate.result is not GameResult.IN_PROGRESS:
        return 0
    return _count_winning_actions(candidate, Player.HUMAN)


def _count_winning_actions(game: Game, player: Player) -> int:
    if game.result is not GameResult.IN_PROGRESS:
        return 0

    probe = game.clone()
    probe.turn = player
    wins = 0
    for action in probe.legal_actions():
        candidate = probe.clone()
        result = candidate.apply(action)
        expected = GameResult.HUMAN_WIN if player is Player.HUMAN else GameResult.ROBOT_WIN
        if result is expected:
            wins += 1
    return wins


def _score_action(game: Game, action: Action) -> int:
    candidate = game.clone()
    result = candidate.apply(action)
    if result is GameResult.ROBOT_WIN:
        return 10_000
    if result is not GameResult.IN_PROGRESS:
        return -500

    score = 0
    for line in WINNING_LINES:
        robot_count = sum(candidate.board[index] is Player.ROBOT for index in line)
        human_count = sum(candidate.board[index] is Player.HUMAN for index in line)
        empty_count = 3 - robot_count - human_count

        if human_count == 0:
            score += robot_count * robot_count * 10 + empty_count
        if robot_count == 0 and human_count == 2 and empty_count == 1:
            score -= 80

    score -= _count_winning_actions(candidate, Player.HUMAN) * 250
    if candidate.board[4] is Player.ROBOT:
        score += 8
    return score

