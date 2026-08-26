import sys
from types import SimpleNamespace

import pytest

from raccoonbot_game.robot.pose_profile import REQUIRED_POSES, RobotPoseProfile
from raccoonbot_game.robot.robomation_driver import RobomationDriver


class FakeRaccoonBot:
    def __init__(self) -> None:
        self.calls = []
        self.angles = [0.0, -10.0, -140.0, 60.0]

    def encoder(self):
        return self.angles.copy()

    def angle_max_speed(self, speed):
        self.calls.append(("speed", speed))

    def set_angle_joints(self, *angles, wait):
        self.angles = list(angles)
        self.calls.append(("angles", angles, wait))

    def pick(self):
        self.calls.append(("pick",))

    def place(self):
        self.calls.append(("place",))

    def set_speed_joints(self, *speeds):
        self.calls.append(("stop", speeds))

    def dispose(self):
        self.calls.append(("dispose",))


def test_official_api_mapping() -> None:
    poses = {name: (1.0, -20.0, -100.0, 30.0) for name in REQUIRED_POSES}
    fake = FakeRaccoonBot()
    sleeps = []
    driver = RobomationDriver(
        RobotPoseProfile(poses, max_speed=15),
        robot=fake,
        gripper_settle_s=0.5,
        joint_step_degrees=180,
        sleeper=sleeps.append,
    )

    driver.move_to("cell_5_hover")
    driver.close_gripper()
    driver.open_gripper()
    driver.stop()
    driver.dispose()

    assert fake.calls == [
        ("speed", 15),
        ("angles", (1.0, -20.0, -100.0, 30.0), True),
        ("pick",),
        ("place",),
        ("stop", (0, 0, 0, 0)),
        ("dispose",),
    ]
    assert sleeps == [0.5, 0.5]


def test_constructor_omits_unsupported_address_when_not_requested(monkeypatch) -> None:
    constructed = []

    class WheelRaccoonBot(FakeRaccoonBot):
        def __init__(self, index=0, port_name=None) -> None:
            super().__init__()
            constructed.append((index, port_name))

    monkeypatch.setitem(sys.modules, "robomation", SimpleNamespace(RaccoonBot=WheelRaccoonBot))
    poses = {name: (1.0, -20.0, -100.0, 30.0) for name in REQUIRED_POSES}

    driver = RobomationDriver(
        RobotPoseProfile(poses, max_speed=10),
        port_name="/dev/ttyACM0",
    )

    assert constructed == [(0, "/dev/ttyACM0")]
    driver.dispose()


def test_constructor_rejects_address_when_installed_api_lacks_it(monkeypatch) -> None:
    class WheelRaccoonBot(FakeRaccoonBot):
        def __init__(self, index=0, port_name=None) -> None:
            super().__init__()

    monkeypatch.setitem(sys.modules, "robomation", SimpleNamespace(RaccoonBot=WheelRaccoonBot))
    poses = {name: (1.0, -20.0, -100.0, 30.0) for name in REQUIRED_POSES}

    with pytest.raises(RuntimeError, match="does not support address selection"):
        RobomationDriver(
            RobotPoseProfile(poses, max_speed=10),
            address="AA:BB:CC:DD:EE:FF",
        )
