import cv2
import numpy as np

from raccoonbot_game.tools.create_calibration import _hue_settings


def _solid_bgr(hue: int) -> np.ndarray:
    hsv = np.full((40, 40, 3), (hue, 240, 220), dtype=np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def test_hue_sampling_builds_regular_interval() -> None:
    settings = _hue_settings(_solid_bgr(28), (20, 20))
    assert settings.hue_intervals == ((18, 38),)


def test_hue_sampling_wraps_red_around_zero() -> None:
    settings = _hue_settings(_solid_bgr(2), (20, 20))
    assert settings.hue_intervals == ((0, 12), (172, 179))
