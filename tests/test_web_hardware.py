from raccoonbot_game.tools.web_hardware import request_path


def test_request_path_ignores_image_cache_buster() -> None:
    assert request_path("/api/calibration/frame.jpg?t=1724840000") == (
        "/api/calibration/frame.jpg"
    )
    assert request_path("/api/calibration/preview.jpg?t=1724840001") == (
        "/api/calibration/preview.jpg"
    )
