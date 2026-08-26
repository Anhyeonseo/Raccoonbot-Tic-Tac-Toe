import pytest

from raccoonbot_game.tools.smoke_test_gripper import smoke_test, wait_for_end_effector


class FakeRobot:
    def __init__(self, *, port_name):
        self.port_name = port_name
        self.calls = []
        self.status = 0

    def battery(self):
        return 3.9

    def end_effector_device(self):
        return 4

    def end_effector_status(self):
        return self.status

    def set_speed_joints(self, *speeds):
        self.calls.append(("stop", speeds))

    def place(self):
        self.status = 0
        self.calls.append(("place",))

    def pick(self):
        self.status = 1
        self.calls.append(("pick",))

    def dispose(self):
        self.calls.append(("dispose",))


def test_gripper_smoke_test_opens_closes_and_leaves_open() -> None:
    robots = []

    def factory(**kwargs):
        robot = FakeRobot(**kwargs)
        robots.append(robot)
        return robot

    statuses = smoke_test(factory, port="/dev/test", settle_s=0.5, sleeper=lambda _: None)

    assert statuses == (0, 1, 0)
    assert robots[0].calls == [
        ("stop", (0, 0, 0, 0)),
        ("place",),
        ("pick",),
        ("place",),
        ("stop", (0, 0, 0, 0)),
        ("dispose",),
    ]


def test_wait_for_end_effector_allows_sensor_packet_warmup() -> None:
    values = iter([0, 0, 4])
    robot = type("Robot", (), {"end_effector_device": lambda self: next(values)})()
    sleeps = []

    assert wait_for_end_effector(robot, sleeper=sleeps.append) == 4
    assert sleeps == [0.1, 0.1]


def test_gripper_smoke_test_rejects_other_device() -> None:
    robot = FakeRobot(port_name="/dev/test")
    robot.end_effector_device = lambda: 3

    with pytest.raises(RuntimeError, match="expected DC gripper device 4"):
        smoke_test(lambda **_kwargs: robot, port="/dev/test", sleeper=lambda _: None)

    assert robot.calls == [("stop", (0, 0, 0, 0)), ("dispose",)]
