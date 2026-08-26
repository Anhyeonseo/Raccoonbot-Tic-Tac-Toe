import json

import pytest

from raccoonbot_game.tools.smoke_test_transition import (
    load_taught_pose,
    minimum_joint_limit_margin,
    smoke_test,
)


class FakeRobot:
    def __init__(self, *, port_name):
        self.angles = [0, -10, -140, 60]
        self.calls = []

    def battery(self):
        return 3.9

    def encoder(self):
        return self.angles.copy()

    def angle_max_speed(self, speed):
        self.calls.append(("speed", speed))

    def set_angle_joints(self, *angles, wait):
        self.angles = list(angles)
        self.calls.append(("angles", angles, wait))

    def set_speed_joints(self, *speeds):
        self.calls.append(("stop", speeds))

    def dispose(self):
        self.calls.append(("dispose",))


def test_transition_moves_to_target_and_returns() -> None:
    robot = FakeRobot(port_name="/dev/test")
    start = [0, -10, -140, 60]
    target = [1, 20, -40, -80]

    actual_start, reached, returned = smoke_test(
        lambda **_kwargs: robot,
        port="/dev/test",
        start_pose=start,
        target_pose=target,
        speed=5,
        settle_s=0,
    )

    assert actual_start == start
    assert reached == target
    assert returned == start
    assert robot.calls[-2:] == [("stop", (0, 0, 0, 0)), ("dispose",)]


def test_transition_rejects_wrong_physical_start_before_motion() -> None:
    robot = FakeRobot(port_name="/dev/test")

    with pytest.raises(RuntimeError, match="not near"):
        smoke_test(
            lambda **_kwargs: robot,
            port="/dev/test",
            start_pose=[30, -10, -140, 60],
            target_pose=[1, 20, -40, -80],
            speed=5,
            settle_s=0,
        )

    assert not any(call[0] == "angles" for call in robot.calls)


def test_load_taught_pose_rejects_provisional(tmp_path) -> None:
    path = tmp_path / "poses.json"
    path.write_text(
        json.dumps(
            {
                "_provisional_poses": ["home"],
                "poses": {"home": [1, 20, -40, -80]},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="provisional"):
        load_taught_pose(path, "home")

    assert load_taught_pose(path, "home", allow_provisional=True) == [1, 20, -40, -80]


def test_minimum_joint_limit_margin() -> None:
    assert minimum_joint_limit_margin([0, 25, -40, -90]) == 5
