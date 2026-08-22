from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum


class Player(str, Enum):
    HUMAN = "human"
    ROBOT = "robot"

    @property
    def opponent(self) -> "Player":
        return Player.ROBOT if self is Player.HUMAN else Player.HUMAN


class GamePhase(str, Enum):
    PLACEMENT = "placement"
    MOVEMENT = "movement"
    FINISHED = "finished"


class GameResult(str, Enum):
    IN_PROGRESS = "in_progress"
    HUMAN_WIN = "human_win"
    ROBOT_WIN = "robot_win"
    DRAW_REPETITION = "draw_repetition"
    DRAW_TURN_LIMIT = "draw_turn_limit"


@dataclass(frozen=True, slots=True)
class Action:
    """A placement has only ``target``; a movement also has ``source``."""

    target: int
    source: int | None = None


WINNING_LINES: tuple[tuple[int, int, int], ...] = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)


@dataclass
class Game:
    max_movement_turns: int = 10
    board: list[Player | None] = field(default_factory=lambda: [None] * 9)
    turn: Player = Player.HUMAN
    phase: GamePhase = GamePhase.PLACEMENT
    result: GameResult = GameResult.IN_PROGRESS
    movement_turns: int = 0
    _position_counts: Counter[tuple[tuple[Player | None, ...], Player]] = field(
        default_factory=Counter,
        repr=False,
    )

    def __post_init__(self) -> None:
        if len(self.board) != 9:
            raise ValueError("board must contain exactly 9 cells")
        self._record_position()

    def legal_actions(self) -> list[Action]:
        if self.phase is GamePhase.FINISHED:
            return []

        empty = [index for index, value in enumerate(self.board) if value is None]
        if self.phase is GamePhase.PLACEMENT:
            return [Action(target=index) for index in empty]

        owned = [index for index, value in enumerate(self.board) if value is self.turn]
        return [Action(source=source, target=target) for source in owned for target in empty]

    def apply(self, action: Action) -> GameResult:
        if action not in self.legal_actions():
            raise ValueError(f"illegal action: {action}")

        moving_player = self.turn
        if self.phase is GamePhase.PLACEMENT:
            self.board[action.target] = moving_player
        else:
            assert action.source is not None
            self.board[action.source] = None
            self.board[action.target] = moving_player
            self.movement_turns += 1

        if self.has_won(moving_player):
            self.result = (
                GameResult.HUMAN_WIN
                if moving_player is Player.HUMAN
                else GameResult.ROBOT_WIN
            )
            self.phase = GamePhase.FINISHED
            return self.result

        if self.phase is GamePhase.PLACEMENT and all(cell is not None for cell in self.board):
            raise RuntimeError("placement phase cannot fill all 9 cells")

        if self.phase is GamePhase.PLACEMENT and sum(cell is not None for cell in self.board) == 6:
            self.phase = GamePhase.MOVEMENT

        self.turn = moving_player.opponent

        if self.phase is GamePhase.MOVEMENT:
            if self.movement_turns >= self.max_movement_turns:
                self.result = GameResult.DRAW_TURN_LIMIT
                self.phase = GamePhase.FINISHED
                return self.result

            if self._record_position() >= 3:
                self.result = GameResult.DRAW_REPETITION
                self.phase = GamePhase.FINISHED

        return self.result

    def has_won(self, player: Player) -> bool:
        return any(all(self.board[index] is player for index in line) for line in WINNING_LINES)

    def clone(self) -> "Game":
        clone = Game(
            max_movement_turns=self.max_movement_turns,
            board=self.board.copy(),
            turn=self.turn,
            phase=self.phase,
            result=self.result,
            movement_turns=self.movement_turns,
        )
        clone._position_counts = self._position_counts.copy()
        return clone

    def _record_position(self) -> int:
        key = (tuple(self.board), self.turn)
        self._position_counts[key] += 1
        return self._position_counts[key]

