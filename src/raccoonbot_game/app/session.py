from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from ..game import Action, Game, GameResult, Player
from ..robot.motion import MotionPlanner
from ..strategy import AiDecision, AiPolicy, decide_robot_action
from ..vision.transition_validator import infer_action


BoardState = Sequence[Player | None]


class SessionStatus(str, Enum):
    WAITING_FOR_HUMAN = "waiting_for_human"
    WAITING_FOR_ROBOT_VERIFICATION = "waiting_for_robot_verification"
    FINISHED = "finished"


@dataclass(frozen=True, slots=True)
class RobotTurn:
    decision: AiDecision
    expected_board: tuple[Player | None, ...]


class RobotVerificationError(RuntimeError):
    pass


class GameSession:
    """Coordinate observed human moves and verified robot pick-and-place turns.

    A robot move is committed to the game only after vision sees the exact
    expected board. This keeps software state aligned with physical reality.
    """

    def __init__(
        self,
        motion: MotionPlanner,
        *,
        game: Game | None = None,
        policy: AiPolicy | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.motion = motion
        self.game = game or Game()
        self.policy = policy or AiPolicy()
        self.rng = rng or random.Random()
        self.pending_robot_turn: RobotTurn | None = None

    @property
    def status(self) -> SessionStatus:
        if self.game.result is not GameResult.IN_PROGRESS:
            return SessionStatus.FINISHED
        if self.pending_robot_turn is not None:
            return SessionStatus.WAITING_FOR_ROBOT_VERIFICATION
        return SessionStatus.WAITING_FOR_HUMAN

    def accept_human_board(self, observed: BoardState) -> RobotTurn | None:
        if self.status is not SessionStatus.WAITING_FOR_HUMAN:
            raise RuntimeError("지금은 사람의 수를 받을 차례가 아닙니다.")
        if self.game.turn is not Player.HUMAN:
            raise RuntimeError("게임 상태의 현재 차례가 사람과 일치하지 않습니다.")

        human_action = infer_action(
            self.game.board,
            observed,
            phase=self.game.phase,
            actor=Player.HUMAN,
        )
        self.game.apply(human_action)
        if self.game.result is not GameResult.IN_PROGRESS:
            return None

        decision = decide_robot_action(self.game, policy=self.policy, rng=self.rng)
        expected = self.game.clone()
        expected.apply(decision.action)
        turn = RobotTurn(decision=decision, expected_board=tuple(expected.board))

        try:
            if decision.action.source is None:
                used_stock = sum(cell is Player.ROBOT for cell in self.game.board)
                self.motion.place_from_stock(used_stock, decision.action.target)
            else:
                self.motion.move_piece(decision.action.source, decision.action.target)
        except Exception:
            self.motion.robot.stop()
            raise

        self.pending_robot_turn = turn
        return turn

    def verify_robot_board(self, observed: BoardState) -> GameResult:
        pending = self.pending_robot_turn
        if pending is None:
            raise RuntimeError("확인할 로봇 동작이 없습니다.")
        actual = tuple(observed)
        if actual != pending.expected_board:
            mismatches = [
                index + 1
                for index, (expected, seen) in enumerate(zip(pending.expected_board, actual))
                if expected is not seen
            ]
            raise RobotVerificationError(
                f"로봇 이동 결과가 예상과 다릅니다. 확인할 칸: {mismatches}"
            )

        result = self.game.apply(pending.decision.action)
        self.pending_robot_turn = None
        return result
