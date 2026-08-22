from __future__ import annotations

import random
from dataclasses import dataclass, field

from ..game import Action, Game, GamePhase, GameResult, Player
from ..strategy import AiDecision, AiPolicy, decide_robot_action


RESULT_MESSAGES = {
    GameResult.HUMAN_WIN: "축하합니다! 빨강 승리!",
    GameResult.ROBOT_WIN: "라쿤봇 승리! 다시 도전해 보세요.",
    GameResult.DRAW_REPETITION: "같은 상황이 반복되어 무승부입니다.",
    GameResult.DRAW_TURN_LIMIT: "이동 횟수 제한으로 무승부입니다.",
}


@dataclass
class DemoGame:
    """Hardware-free UI model that follows the exact physical game rules."""

    seed: int = 0
    policy: AiPolicy = field(default_factory=AiPolicy)
    game: Game = field(default_factory=Game, init=False)
    selected_source: int | None = field(default=None, init=False)
    message: str = field(default="빨강 말을 놓을 빈칸을 선택하세요.", init=False)
    last_robot_decision: AiDecision | None = field(default=None, init=False)
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def reset(self) -> None:
        self.game = Game()
        self.selected_source = None
        self.last_robot_decision = None
        self.message = "빨강 말을 놓을 빈칸을 선택하세요."

    def click(self, index: int) -> None:
        if index not in range(9):
            raise ValueError("cell index must be between 0 and 8")
        if self.game.result is not GameResult.IN_PROGRESS:
            self.message = "새 게임을 눌러 다시 시작하세요."
            return
        if self.game.turn is not Player.HUMAN:
            self.message = "라쿤봇 차례입니다. 잠시 기다려 주세요."
            return

        action = self._human_action(index)
        if action is None:
            return
        self.game.apply(action)
        self.selected_source = None
        if self._show_result_if_finished():
            return

        self.last_robot_decision = decide_robot_action(
            self.game,
            policy=self.policy,
            rng=self._rng,
        )
        self.game.apply(self.last_robot_decision.action)
        if self._show_result_if_finished():
            return
        self.message = (
            "빨강 말 하나를 선택한 뒤 원하는 빈칸을 선택하세요."
            if self.game.phase is GamePhase.MOVEMENT
            else "빨강 말을 놓을 빈칸을 선택하세요."
        )

    def _human_action(self, index: int) -> Action | None:
        occupant = self.game.board[index]
        if self.game.phase is GamePhase.PLACEMENT:
            if occupant is not None:
                self.message = "이미 말이 있는 칸입니다. 빈칸을 선택하세요."
                return None
            return Action(target=index)

        if self.selected_source is None:
            if occupant is not Player.HUMAN:
                self.message = "먼저 빨강 말 하나를 선택하세요."
                return None
            self.selected_source = index
            self.message = f"{index + 1}번 말을 선택했습니다. 옮길 빈칸을 선택하세요."
            return None

        if occupant is Player.HUMAN:
            self.selected_source = index
            self.message = f"{index + 1}번 말로 선택을 바꿨습니다."
            return None
        if occupant is not None:
            self.message = "말이 있는 칸에는 놓을 수 없습니다."
            return None
        return Action(source=self.selected_source, target=index)

    def _show_result_if_finished(self) -> bool:
        if self.game.result is GameResult.IN_PROGRESS:
            return False
        self.message = RESULT_MESSAGES[self.game.result]
        return True
