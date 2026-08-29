from raccoonbot_game.tools.web_hardware import move_to_calibration_home, request_path


def test_request_path_ignores_image_cache_buster() -> None:
    assert request_path("/api/calibration/frame.jpg?t=1724840000") == (
        "/api/calibration/frame.jpg"
    )
    assert request_path("/api/calibration/preview.jpg?t=1724840001") == (
        "/api/calibration/preview.jpg"
    )


def test_move_to_calibration_home_uses_safe_route() -> None:
    class RecordingDriver:
        def __init__(self) -> None:
            self.moves: list[str] = []

        def move_to(self, pose_name: str) -> None:
            self.moves.append(pose_name)

        def open_gripper(self) -> None:
            return

        def close_gripper(self) -> None:
            return

        def stop(self) -> None:
            return

    driver = RecordingDriver()

    move_to_calibration_home(driver)

    assert driver.moves == ["transit", "home_high", "home"]
