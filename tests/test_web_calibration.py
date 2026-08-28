from __future__ import annotations

import pytest

from raccoonbot_game.app.web_calibration import WebCalibrationController
from raccoonbot_game.calibration import VisionCalibration, default_synthetic_calibration
from raccoonbot_game.game import Player
from raccoonbot_game.vision.synthetic import render_board


def _frame():
    return render_board(
        [Player.HUMAN, None, None, None, None, None, None, None, Player.ROBOT],
        cell_size=200,
    )


def _points():
    return [
        [0, 0],
        [599, 0],
        [599, 599],
        [0, 599],
        [100, 100],
        [500, 500],
    ]


def test_capture_preview_and_explicit_save_with_backup(tmp_path) -> None:
    path = tmp_path / "vision.json"
    default_synthetic_calibration(600).save(path)
    controller = WebCalibrationController(path, _frame)

    captured = controller.capture()
    assert captured["width"] == 600
    assert controller.image().startswith(b"\xff\xd8")

    preview = controller.preview({"points": _points()})
    assert preview["cells"][0]["label"] == "human"
    assert preview["cells"][8]["label"] == "robot"
    assert controller.image(preview=True).startswith(b"\xff\xd8")

    saved = controller.save()
    assert saved["backup"] is not None
    assert VisionCalibration.load(path).board.corners == (
        (0.0, 0.0),
        (599.0, 0.0),
        (599.0, 599.0),
        (0.0, 599.0),
    )


def test_preview_rejects_wrong_corner_order(tmp_path) -> None:
    path = tmp_path / "vision.json"
    default_synthetic_calibration(600).save(path)
    controller = WebCalibrationController(path, _frame)
    controller.capture()
    points = _points()
    points[:4] = [[0, 0], [599, 599], [599, 0], [0, 599]]

    with pytest.raises(ValueError, match="TL, TR, BR, BL"):
        controller.preview({"points": points})


def test_save_requires_preview(tmp_path) -> None:
    path = tmp_path / "vision.json"
    default_synthetic_calibration(600).save(path)
    controller = WebCalibrationController(path, _frame)

    with pytest.raises(ValueError, match="미리보기를 먼저"):
        controller.save()
