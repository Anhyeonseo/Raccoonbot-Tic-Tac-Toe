import json

import pytest

from raccoonbot_game.calibration import (
    BoardSettings,
    ColorSettings,
    VisionCalibration,
    default_synthetic_calibration,
)


def test_calibration_round_trip(tmp_path) -> None:
    calibration = default_synthetic_calibration(300)
    path = tmp_path / "venue.json"

    calibration.save(path)
    loaded = VisionCalibration.load(path)

    assert loaded == calibration
    assert json.loads(path.read_text(encoding="utf-8"))["board"]["canonical_size"] == 300


def test_invalid_board_rotation_is_rejected() -> None:
    with pytest.raises(ValueError):
        BoardSettings(corners=((0, 0), (1, 0), (1, 1), (0, 1)), rotation=4)


def test_invalid_hue_interval_is_rejected() -> None:
    with pytest.raises(ValueError):
        ColorSettings(hue_intervals=((170, 10),))

