import threading
import time

from raccoonbot_game.app.web_controller import WebGameController
from raccoonbot_game.game import GameResult, Player


def wait_until(predicate, timeout: float = 1.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("condition was not met before timeout")


def test_controller_bridges_browser_submit_to_blocking_game() -> None:
    runner_started = threading.Event()

    def runner(*, wait_for_submit, status_callback, **_kwargs):
        board = (Player.HUMAN,) + (None,) * 8
        status_callback("waiting_human", "빨간 말을 놓으세요.", board)
        runner_started.set()
        wait_for_submit("손을 뺀 뒤 완료를 누르세요.")
        status_callback("finished", "사람 승리!", board)
        return GameResult.HUMAN_WIN

    controller = WebGameController(runner, {})
    assert controller.submit() is False
    assert controller.start() is True
    assert controller.start() is False
    assert runner_started.wait(1)
    wait_until(lambda: controller.snapshot()["can_submit"])

    state = controller.snapshot()
    assert state["board"] == ["human"] + [None] * 8
    assert controller.submit() is True
    controller.join()

    state = controller.snapshot()
    assert state["stage"] == "finished"
    assert state["result"] == "human_win"
    assert state["can_start"] is True


def test_controller_reports_runner_errors() -> None:
    def runner(**_kwargs):
        raise RuntimeError("camera offline")

    controller = WebGameController(runner, {})
    assert controller.start() is True
    controller.join()

    state = controller.snapshot()
    assert state["stage"] == "error"
    assert "camera offline" in state["message"]
    assert state["can_start"] is True


def test_main_thread_mode_runs_requested_game_in_calling_thread() -> None:
    calling_thread = threading.current_thread()
    observed_thread = None

    def runner(**_kwargs):
        nonlocal observed_thread
        observed_thread = threading.current_thread()
        return GameResult.DRAW_TURN_LIMIT

    controller = WebGameController(runner, {}, threaded=False)
    assert controller.start() is True
    assert controller.run_pending() is True

    assert observed_thread is calling_thread
    assert controller.snapshot()["result"] == "draw_turn_limit"


def test_operator_stop_interrupts_wait_and_requires_reset() -> None:
    waiting = threading.Event()

    def runner(*, wait_for_submit, **_kwargs):
        waiting.set()
        wait_for_submit("빨간 말을 놓으세요.")
        raise AssertionError("cancelled wait must not return")

    controller = WebGameController(runner, {})
    assert controller.start() is True
    assert waiting.wait(1)
    wait_until(lambda: controller.snapshot()["can_submit"])

    assert controller.request_stop() is True
    controller.join()
    stopped = controller.snapshot()
    assert stopped["stage"] == "stopped"
    assert stopped["can_start"] is False
    assert stopped["can_reset"] is True

    assert controller.reset() is True
    reset = controller.snapshot()
    assert reset["stage"] == "idle"
    assert reset["can_start"] is True
    assert reset["can_reset"] is False


def test_operator_stop_is_checked_between_hardware_actions() -> None:
    entered = threading.Event()
    release = threading.Event()

    def runner(*, cancellation_check, **_kwargs):
        entered.set()
        assert release.wait(1)
        cancellation_check()
        raise AssertionError("cancellation check must raise")

    controller = WebGameController(runner, {})
    assert controller.start() is True
    assert entered.wait(1)
    assert controller.request_stop() is True
    release.set()
    controller.join()

    assert controller.snapshot()["stage"] == "stopped"


def test_reset_is_rejected_while_game_is_running() -> None:
    waiting = threading.Event()

    def runner(*, wait_for_submit, **_kwargs):
        waiting.set()
        wait_for_submit("대기")
        return GameResult.DRAW_REPETITION

    controller = WebGameController(runner, {})
    assert controller.start() is True
    assert waiting.wait(1)
    assert controller.reset() is False
    assert controller.request_stop() is True
    controller.join()
