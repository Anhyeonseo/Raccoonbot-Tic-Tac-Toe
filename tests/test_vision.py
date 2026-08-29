import cv2
import numpy as np

from raccoonbot_game.calibration import (
    BoardSettings,
    CameraSettings,
    ColorSettings,
    VisionCalibration,
    default_synthetic_calibration,
)
from raccoonbot_game.game import Player
from raccoonbot_game.vision.board_observer import BoardObserver, BoardStateStabilizer
from raccoonbot_game.vision.perspective import cell_bounds
from raccoonbot_game.vision.synthetic import project_board, render_board


E = None
H = Player.HUMAN
R = Player.ROBOT


def test_detects_red_yellow_and_empty_cells() -> None:
    state = (H, E, R, E, H, E, R, E, H)
    image = render_board(state, cell_size=200)
    observer = BoardObserver(default_synthetic_calibration(600))

    observation = observer.observe(image)

    assert observation.is_complete
    assert observation.as_game_board() == state


def test_recovers_board_after_perspective_projection() -> None:
    state = (E, H, R, R, E, H, H, R, E)
    canonical = render_board(state, cell_size=200)
    corners = ((180.0, 90.0), (760.0, 130.0), (700.0, 640.0), (120.0, 590.0))
    projected = project_board(canonical, corners)
    calibration = VisionCalibration(
        camera=CameraSettings(width=900, height=700),
        board=BoardSettings(corners=corners, canonical_size=600),
        human_color=ColorSettings(hue_intervals=((0, 10), (170, 179))),
        robot_color=ColorSettings(hue_intervals=((20, 38),)),
    )

    observation = BoardObserver(calibration).observe(projected)

    assert observation.as_game_board() == state


def test_detects_piece_placed_near_cell_edge() -> None:
    image = render_board([E] * 9, cell_size=200)
    cv2.circle(image, (35, 35), 25, (0, 0, 255), -1)
    observer = BoardObserver(default_synthetic_calibration(600))

    observation = observer.observe(image)

    assert observation.cells[0].label.value == "human"
    assert all(cell.label.value == "empty" for cell in observation.cells[1:])


def test_stabilizer_requires_repeated_matching_states() -> None:
    state = (H, E, R, E, H, E, R, E, H)
    observer = BoardObserver(default_synthetic_calibration(600))
    observation = observer.observe(render_board(state, cell_size=200))
    stabilizer = BoardStateStabilizer(window_size=5, required_matches=3)

    assert stabilizer.update(observation) is None
    assert stabilizer.update(observation) is None
    assert stabilizer.update(observation) == state


def test_cell_bounds_use_only_center_region() -> None:
    x0, y0, x1, y1 = cell_bounds(4, board_size=600, margin_ratio=0.2)

    assert (x0, y0, x1, y1) == (240, 240, 360, 360)


def test_invalid_image_shape_is_rejected() -> None:
    observer = BoardObserver(default_synthetic_calibration(600))

    try:
        observer.observe(np.zeros((600, 600), dtype=np.uint8))
    except ValueError as error:
        assert "BGR" in str(error)
    else:
        raise AssertionError("grayscale image should be rejected")
