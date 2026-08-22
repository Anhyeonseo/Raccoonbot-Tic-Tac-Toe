from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from ..game import Action, GamePhase, Player


BoardState = Sequence[Player | None]


class TransitionErrorCode(str, Enum):
    INVALID_BOARD = "invalid_board"
    NO_CHANGE = "no_change"
    TOO_MANY_CHANGES = "too_many_changes"
    WRONG_PLAYER = "wrong_player"
    OCCUPIED_TARGET = "occupied_target"
    PIECE_REMOVED = "piece_removed"
    INVALID_PLACEMENT = "invalid_placement"
    INVALID_MOVEMENT = "invalid_movement"


@dataclass(frozen=True, slots=True)
class InvalidTransition(ValueError):
    code: TransitionErrorCode
    message: str

    def __str__(self) -> str:
        return self.message


def infer_action(
    before: BoardState,
    after: BoardState,
    *,
    phase: GamePhase,
    actor: Player = Player.HUMAN,
) -> Action:
    """Infer one legal physical action from two observed board states.

    This validates only the physical transition. The game engine remains the
    final authority for whether the inferred action is legal in the game.
    """

    previous = _normalize_board(before)
    current = _normalize_board(after)
    changes = [
        (index, previous[index], current[index])
        for index in range(9)
        if previous[index] is not current[index]
    ]

    if not changes:
        raise InvalidTransition(TransitionErrorCode.NO_CHANGE, "보드에서 변화를 찾지 못했습니다.")

    if phase is GamePhase.PLACEMENT:
        return _infer_placement(changes, actor)
    if phase is GamePhase.MOVEMENT:
        return _infer_movement(changes, actor)
    raise InvalidTransition(
        TransitionErrorCode.INVALID_BOARD,
        "종료된 게임에서는 새로운 행동을 받을 수 없습니다.",
    )


def _normalize_board(board: BoardState) -> tuple[Player | None, ...]:
    if len(board) != 9:
        raise InvalidTransition(
            TransitionErrorCode.INVALID_BOARD,
            "보드는 정확히 9칸이어야 합니다.",
        )
    normalized = tuple(board)
    if any(value not in (None, Player.HUMAN, Player.ROBOT) for value in normalized):
        raise InvalidTransition(
            TransitionErrorCode.INVALID_BOARD,
            "알 수 없는 말 상태가 포함되어 있습니다.",
        )
    return normalized


def _infer_placement(
    changes: list[tuple[int, Player | None, Player | None]],
    actor: Player,
) -> Action:
    if len(changes) > 1:
        raise InvalidTransition(
            TransitionErrorCode.TOO_MANY_CHANGES,
            "배치 단계에서는 말 하나만 놓아주세요.",
        )

    index, old, new = changes[0]
    if old is not None:
        raise InvalidTransition(
            TransitionErrorCode.INVALID_PLACEMENT,
            "배치 단계에서는 기존 말을 움직이지 마세요.",
        )
    if new is not actor:
        raise InvalidTransition(
            TransitionErrorCode.WRONG_PLAYER,
            "자기 색깔의 말 하나를 놓아주세요.",
        )
    return Action(target=index)


def _infer_movement(
    changes: list[tuple[int, Player | None, Player | None]],
    actor: Player,
) -> Action:
    if len(changes) != 2:
        code = (
            TransitionErrorCode.TOO_MANY_CHANGES
            if len(changes) > 2
            else TransitionErrorCode.INVALID_MOVEMENT
        )
        raise InvalidTransition(code, "자기 말 하나만 빈칸으로 옮겨주세요.")

    source = [index for index, old, new in changes if old is actor and new is None]
    target = [index for index, old, new in changes if old is None and new is actor]
    if len(source) == 1 and len(target) == 1:
        return Action(source=source[0], target=target[0])

    if any(old is actor.opponent or new is actor.opponent for _, old, new in changes):
        raise InvalidTransition(
            TransitionErrorCode.WRONG_PLAYER,
            "상대방 말은 움직일 수 없습니다.",
        )
    if any(old is not None and new is not None for _, old, new in changes):
        raise InvalidTransition(
            TransitionErrorCode.OCCUPIED_TARGET,
            "말은 빈칸으로만 옮길 수 있습니다.",
        )
    if source and not target:
        raise InvalidTransition(
            TransitionErrorCode.PIECE_REMOVED,
            "집어 든 말을 빈칸에 다시 놓아주세요.",
        )
    raise InvalidTransition(
        TransitionErrorCode.INVALID_MOVEMENT,
        "자기 말 하나만 빈칸으로 옮겨주세요.",
    )

