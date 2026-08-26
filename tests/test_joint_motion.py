import pytest

from raccoonbot_game.robot.joint_motion import (
    DEFAULT_MAX_JOINT_STEP_DEGREES,
    interpolate_joint_path,
    move_joints_interpolated,
)


class FakeRobot:
    def __init__(self) -> None:
        self.angles = [0.0, -10.0, -140.0, 60.0]
        self.commands = []

    def encoder(self):
        return self.angles.copy()

    def set_angle_joints(self, *angles, wait):
        self.angles = list(angles)
        self.commands.append((angles, wait))


def test_default_step_is_fast_booth_profile() -> None:
    assert DEFAULT_MAX_JOINT_STEP_DEGREES == 6.0
    path = interpolate_joint_path([0, 0, 0, 0], [10, 0, 0, 0])
    assert len(path) == 2


def test_interpolated_path_limits_every_joint_step_and_ends_exactly() -> None:
    start = [0, -10, -140, 60]
    target = [10, -17, -137, 54]

    path = interpolate_joint_path(start, target, max_step_degrees=2)

    assert len(path) == 5
    assert path[-1] == [float(value) for value in target]
    previous = start
    for waypoint in path:
        assert max(abs(a - b) for a, b in zip(previous, waypoint)) <= 2.0
        previous = waypoint


def test_interpolated_move_sends_all_waypoints_with_wait() -> None:
    robot = FakeRobot()

    steps = move_joints_interpolated(
        robot,
        [5, -14, -138, 58],
        max_step_degrees=2,
    )

    assert steps == 3
    assert robot.angles == [5.0, -14.0, -138.0, 58.0]
    assert all(wait is True for _, wait in robot.commands)


@pytest.mark.parametrize("step", [0, -1])
def test_interpolated_path_rejects_nonpositive_step(step) -> None:
    with pytest.raises(ValueError, match="positive"):
        interpolate_joint_path([0, 0, 0, 0], [1, 1, 1, 1], max_step_degrees=step)
