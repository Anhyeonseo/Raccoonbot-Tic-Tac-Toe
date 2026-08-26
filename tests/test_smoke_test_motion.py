import pytest

from raccoonbot_game.tools.smoke_test_motion import build_target, smoke_test, wait_for_battery


class FakeRobot:
    def __init__(self, *, port_name):
        self.port_name = port_name
        self.angles = [1.0, -10.0, -140.0, 60.0]
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


def test_build_target_changes_only_selected_joint() -> None:
    assert build_target([1, -10, -140, 60], 1, 3) == [4, -10, -140, 60]


@pytest.mark.parametrize("delta", [0, 5.1, -5.1])
def test_build_target_rejects_unsafe_delta(delta) -> None:
    with pytest.raises(ValueError, match="delta"):
        build_target([1, -10, -140, 60], 1, delta)


def test_smoke_test_moves_and_returns_then_stops() -> None:
    robots = []

    def factory(**kwargs):
        robot = FakeRobot(**kwargs)
        robots.append(robot)
        return robot

    start, reached, returned = smoke_test(
        factory,
        port="/dev/test",
        joint=1,
        delta=3,
        speed=5,
        settle_s=0,
    )

    assert start == [1, -10, -140, 60]
    assert reached == [4, -10, -140, 60]
    assert returned == start
    assert robots[0].calls == [
        ("speed", 5),
        ("angles", (4, -10, -140, 60), True),
        ("angles", (1, -10, -140, 60), True),
        ("stop", (0, 0, 0, 0)),
        ("dispose",),
    ]


def test_wait_for_battery_allows_sensor_packet_warmup() -> None:
    values = iter([0.0, 0.0, 3.95])
    robot = type("Robot", (), {"battery": lambda self: next(values)})()
    sleeps = []

    assert wait_for_battery(robot, sleeper=sleeps.append) == 3.95
    assert sleeps == [0.1, 0.1]
