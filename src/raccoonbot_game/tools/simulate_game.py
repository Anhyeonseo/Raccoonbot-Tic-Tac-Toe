from __future__ import annotations

import argparse
import random

from raccoonbot_game.game import Action, Game, GamePhase, GameResult, Player
from raccoonbot_game.simulation import render_ascii, run_tournament
from raccoonbot_game.strategy import AiPolicy, decide_robot_action


RESULT_LABEL = {
    GameResult.HUMAN_WIN: "사람 승리",
    GameResult.ROBOT_WIN: "로봇 승리",
    GameResult.DRAW_REPETITION: "반복 무승부",
    GameResult.DRAW_TURN_LIMIT: "이동 횟수 제한 무승부",
}


def _parse_cell(value: str) -> int:
    cell = int(value) - 1
    if cell not in range(9):
        raise ValueError("칸 번호는 1~9입니다.")
    return cell


def _read_human_action(game: Game) -> Action:
    while True:
        print("\n" + render_ascii(game, show_indices=True))
        try:
            if game.phase is GamePhase.PLACEMENT:
                action = Action(target=_parse_cell(input("놓을 칸 (1~9): ").strip()))
            else:
                values = input("옮길 말과 빈 칸 (예: 2 9): ").split()
                if len(values) != 2:
                    raise ValueError("숫자 두 개를 입력하세요.")
                action = Action(source=_parse_cell(values[0]), target=_parse_cell(values[1]))
            if action not in game.legal_actions():
                raise ValueError("현재 상태에서 가능한 수가 아닙니다.")
            return action
        except ValueError as exc:
            print(f"입력 오류: {exc}")


def interactive(seed: int) -> None:
    rng = random.Random(seed)
    game = Game()
    print("빨강(R)은 사람, 노랑(Y)은 로봇입니다. 사람부터 시작합니다.")
    while game.result is GameResult.IN_PROGRESS:
        if game.turn is Player.HUMAN:
            action = _read_human_action(game)
        else:
            decision = decide_robot_action(game, policy=AiPolicy(), rng=rng)
            action = decision.action
            source = "배치" if action.source is None else f"{action.source + 1}에서"
            print(f"\n로봇: {source} {action.target + 1}번 칸으로 ({decision.reason})")
        game.apply(action)

    print("\n최종 보드\n" + render_ascii(game))
    print(RESULT_LABEL[game.result])


def main() -> None:
    parser = argparse.ArgumentParser(description="RaccoonBot 3말 잇기 데스크톱 시뮬레이터")
    parser.add_argument("--games", type=int, default=0, help="0이면 대화형, 양수면 자동 대회")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    if args.games:
        results = run_tournament(args.games, seed=args.seed)
        print(f"자동 경기 {args.games}회 (seed={args.seed})")
        for result in GameResult:
            if result is not GameResult.IN_PROGRESS:
                print(f"{result.value}: {results[result]}")
    else:
        interactive(args.seed)


if __name__ == "__main__":
    main()
