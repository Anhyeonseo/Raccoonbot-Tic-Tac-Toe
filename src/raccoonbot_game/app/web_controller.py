from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from ..game import GameResult, Player
from ..vision.board_observer import GameBoard


GameRunner = Callable[..., GameResult]


class GameCancelled(RuntimeError):
    pass


def _serialize_board(board: GameBoard | None) -> list[str | None]:
    if board is None:
        return [None] * 9
    return [cell.value if isinstance(cell, Player) else None for cell in board]


class WebGameController:
    """Thread-safe bridge between the blocking hardware game and HTTP UI."""

    def __init__(
        self,
        runner: GameRunner,
        runner_kwargs: dict[str, Any],
        *,
        threaded: bool = True,
        difficulty: str = "easy",
    ) -> None:
        self._runner = runner
        self._runner_kwargs = runner_kwargs
        self._threaded = threaded
        self._lock = threading.Lock()
        self._submit_event = threading.Event()
        self._start_event = threading.Event()
        self._cancel_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._state: dict[str, Any] = {
            "revision": 0,
            "stage": "idle",
            "message": "새 게임을 누르면 장비 연결과 보드 확인을 시작합니다.",
            "board": [None] * 9,
            "running": False,
            "can_start": True,
            "can_submit": False,
            "can_stop": False,
            "can_reset": False,
            "submit_label": "내 차례 완료",
            "result": None,
            "difficulty": difficulty,
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            snapshot = self._state.copy()
            snapshot["board"] = list(self._state["board"])
            return snapshot

    def start(self) -> bool:
        with self._lock:
            if self._state["running"]:
                return False
            self._cancel_event.clear()
            self._submit_event.clear()
            self._state.update(
                stage="starting",
                message="장비를 연결하고 게임을 준비하고 있습니다.",
                board=[None] * 9,
                running=True,
                can_start=False,
                can_submit=False,
                can_stop=True,
                can_reset=False,
                submit_label="내 차례 완료",
                result=None,
            )
            self._bump_revision_locked()
            if self._threaded:
                self._worker = threading.Thread(target=self._run, name="hardware-game")
                self._worker.start()
            else:
                self._start_event.set()
            return True

    def submit(self) -> bool:
        with self._lock:
            if not self._state["can_submit"]:
                return False
            self._state["can_submit"] = False
            self._bump_revision_locked()
        self._submit_event.set()
        return True

    def request_stop(self) -> bool:
        """Request a cooperative stop at the next safe command boundary."""

        with self._lock:
            if not self._state["running"]:
                return False
            self._state.update(
                stage="stopping",
                message="현재 관절 이동을 마친 뒤 안전하게 게임을 중단합니다.",
                can_submit=False,
                can_stop=False,
            )
            self._bump_revision_locked()
        self._cancel_event.set()
        self._submit_event.set()
        return True

    def reset(self) -> bool:
        """Clear a finished, stopped, or failed UI session without moving hardware."""

        with self._lock:
            if self._state["running"]:
                return False
            self._cancel_event.clear()
            self._submit_event.clear()
            self._state.update(
                stage="idle",
                message="보드를 비우고 노란 말 3개를 stock에 놓은 뒤 새 게임을 누르세요.",
                board=[None] * 9,
                running=False,
                can_start=True,
                can_submit=False,
                can_stop=False,
                can_reset=False,
                submit_label="내 차례 완료",
                result=None,
            )
            self._bump_revision_locked()
            return True

    def cancel(self) -> None:
        self._cancel_event.set()
        self._start_event.set()
        self._submit_event.set()

    def join(self) -> None:
        worker = self._worker
        if worker is not None:
            worker.join()

    def run_pending(self) -> bool:
        """Run one requested game in the calling thread.

        The official hardware library installs signal handlers, so production
        calls this method from the interpreter's main thread.
        """
        if self._threaded:
            raise RuntimeError("run_pending is only available in main-thread mode")
        self._start_event.wait()
        self._start_event.clear()
        if self._cancel_event.is_set():
            return False
        self._run()
        return True

    def _run(self) -> None:
        try:
            result = self._runner(
                **self._runner_kwargs,
                wait_for_submit=self._wait_for_submit,
                status_callback=self._status_callback,
                cancellation_check=self._check_cancelled,
            )
            with self._lock:
                self._state["result"] = result.value
        except GameCancelled:
            self._set_state(
                "stopped",
                "게임이 안전하게 중단되었습니다. 보드를 정리한 뒤 초기화하세요.",
            )
        except Exception as exc:
            self._set_state("error", f"게임을 중단했습니다: {exc}")
        finally:
            with self._lock:
                self._state["running"] = False
                self._state["can_start"] = not self._cancel_event.is_set()
                self._state["can_submit"] = False
                self._state["can_stop"] = False
                self._state["can_reset"] = True
                self._bump_revision_locked()

    def _check_cancelled(self) -> None:
        if self._cancel_event.is_set():
            raise GameCancelled

    def _wait_for_submit(self, prompt: str) -> None:
        self._check_cancelled()
        retry = "검증" in prompt or "다시" in prompt
        self._submit_event.clear()
        with self._lock:
            self._state["message"] = prompt.removesuffix(": ")
            self._state["can_submit"] = True
            self._state["submit_label"] = "다시 확인" if retry else "내 차례 완료"
            self._bump_revision_locked()
        self._submit_event.wait()
        self._check_cancelled()

    def _status_callback(
        self,
        stage: str,
        message: str,
        board: GameBoard | None,
    ) -> None:
        self._check_cancelled()
        self._set_state(stage, message, board)

    def _set_state(
        self,
        stage: str,
        message: str,
        board: GameBoard | None = None,
    ) -> None:
        with self._lock:
            self._state["stage"] = stage
            self._state["message"] = message
            if board is not None:
                self._state["board"] = _serialize_board(board)
            self._state["can_submit"] = False
            self._bump_revision_locked()

    def _bump_revision_locked(self) -> None:
        self._state["revision"] += 1
