from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

from .game import Action, Game, GameResult, Player
from .strategy import AiPolicy, decide_robot_action


SYMBOLS = {None: ".", Player.HUMAN: "R", Player.ROBOT: "Y"}


def render_ascii(game: Game, *, show_indices: bool = False) -> str:
    """Render the board in the same top-left-to-bottom-right numbering as vision."""

    cells: list[str] = []
    for index, occupant in enumerate(game.board):
        cells.append(str(index + 1) if show_indices and occupant is None else SYMBOLS[occupant])
    return "\n".join(" ".join(cells[row : row + 3]) for row in range(0, 9, 3))


def choose_random_action(game: Game, rng: random.Random) -> Action:
    actions = game.legal_actions()
    if not actions:
        raise ValueError("the game has no legal actions")
    return rng.choice(actions)


@dataclass(frozen=True, slots=True)
class MatchRecord:
    result: GameResult
    actions: tuple[Action, ...]
    robot_reasons: tuple[str, ...]


def play_simulated_match(
    *,
    rng: random.Random | None = None,
    ai_policy: AiPolicy | None = None,
    max_movement_turns: int = 10,
) -> MatchRecord:
    """Play a random child versus the booth AI without any hardware."""

    rng = rng or random.Random()
    game = Game(max_movement_turns=max_movement_turns)
    actions: list[Action] = []
    reasons: list[str] = []

    while game.result is GameResult.IN_PROGRESS:
        if game.turn is Player.HUMAN:
            action = choose_random_action(game, rng)
        else:
            decision = decide_robot_action(game, policy=ai_policy, rng=rng)
            action = decision.action
            reasons.append(decision.reason)
        game.apply(action)
        actions.append(action)

    return MatchRecord(game.result, tuple(actions), tuple(reasons))


def run_tournament(
    games: int,
    *,
    seed: int = 0,
    ai_policy: AiPolicy | None = None,
    max_movement_turns: int = 10,
) -> Counter[GameResult]:
    if games < 1:
        raise ValueError("games must be at least 1")
    rng = random.Random(seed)
    return Counter(
        play_simulated_match(
            rng=rng,
            ai_policy=ai_policy,
            max_movement_turns=max_movement_turns,
        ).result
        for _ in range(games)
    )
