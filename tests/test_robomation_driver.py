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


def test_move_to_stops_and_raises_when_pose_is_not_reached() -> None:
    class StalledRaccoonBot(FakeRaccoonBot):
        def set_angle_joints(self, *angles, wait):
            self.calls.append(("angles", angles, wait))

    poses = {name: (1.0, -20.0, -100.0, 30.0) for name in REQUIRED_POSES}
    fake = StalledRaccoonBot()
    driver = RobomationDriver(
        RobotPoseProfile(poses, max_speed=15),
        robot=fake,
        joint_step_degrees=180,
    )

    with pytest.raises(RuntimeError, match="did not reach pose 'home'"):
        driver.move_to("home")

    angle_calls = [call for call in fake.calls if call[0] == "angles"]
    assert len(angle_calls) == 3
    assert fake.calls[-1] == ("stop", (0, 0, 0, 0))


def test_move_to_retries_twice_and_recovers(capsys) -> None:
    class EventuallyReachedRaccoonBot(FakeRaccoonBot):
        def __init__(self) -> None:
            super().__init__()
            self.move_attempts = 0

        def set_angle_joints(self, *angles, wait):
            self.move_attempts += 1
            self.calls.append(("angles", angles, wait))
            if self.move_attempts == 3:
                self.angles = list(angles)

    poses = {name: (1.0, -20.0, -100.0, 30.0) for name in REQUIRED_POSES}
    fake = EventuallyReachedRaccoonBot()
    driver = RobomationDriver(
        RobotPoseProfile(poses, max_speed=15),
        robot=fake,
    )

    driver.move_to("cell_2_hover")

    angle_calls = [call for call in fake.calls if call[0] == "angles"]
    assert len(angle_calls) == 3
    assert not any(call[0] == "stop" for call in fake.calls)
    output = capsys.readouterr().out
    assert "attempt=1/3" in output
    assert "attempt=2/3" in output
    assert "motion retry recovered" in output
    assert "attempt=3/3" in output


def test_direct_motion_sends_one_official_joint_command() -> None:
    poses = {name: (1.0, -20.0, -100.0, 30.0) for name in REQUIRED_POSES}
    fake = FakeRaccoonBot()
    driver = RobomationDriver(
        RobotPoseProfile(poses, max_speed=15),
        robot=fake,
        interpolate_moves=False,
    )

    driver.move_to("cell_5_hover")

    angle_calls = [call for call in fake.calls if call[0] == "angles"]
    assert angle_calls == [("angles", (1.0, -20.0, -100.0, 30.0), True)]


def test_before_action_guard_runs_before_pose_and_gripper_commands() -> None:
    poses = {name: (1.0, -20.0, -100.0, 30.0) for name in REQUIRED_POSES}
    fake = FakeRaccoonBot()
    guarded = []
    driver = RobomationDriver(
        RobotPoseProfile(poses, max_speed=15),
        robot=fake,
        interpolate_moves=False,
        before_action=lambda: guarded.append("check"),
        sleeper=lambda _seconds: None,
    )

    driver.move_to("home")
    driver.open_gripper()
    driver.close_gripper()

    assert guarded == ["check", "check", "check"]


def test_constructor_rejects_non_positive_reached_tolerance() -> None:
    poses = {name: (1.0, -20.0, -100.0, 30.0) for name in REQUIRED_POSES}

    with pytest.raises(ValueError, match="reached_tolerance_degrees must be positive"):
        RobomationDriver(
            RobotPoseProfile(poses, max_speed=15),
            robot=FakeRaccoonBot(),
            reached_tolerance_degrees=0,
        )


@pytest.mark.parametrize("move_retries", [-1, 1.5, True])
def test_constructor_rejects_invalid_move_retries(move_retries) -> None:
    poses = {name: (1.0, -20.0, -100.0, 30.0) for name in REQUIRED_POSES}

    with pytest.raises((TypeError, ValueError), match="move_retries"):
        RobomationDriver(
            RobotPoseProfile(poses, max_speed=15),
            robot=FakeRaccoonBot(),
            move_retries=move_retries,
        )


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
