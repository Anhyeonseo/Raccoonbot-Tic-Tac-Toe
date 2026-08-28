from raccoonbot_game.robot.pose_profile import REQUIRED_POSES, RobotPoseProfile
from raccoonbot_game.robot.robomation_driver import RobomationDriver
from raccoonbot_game.tools.smoke_test_cell_sweep import (
    cell_sweep_pose_sequence,
    execute_cell_sweep,
)


class FakeRobot:
    def __init__(self) -> None:
        self.angles = [0.0, -10.0, -140.0, 60.0]
        self.status = 0
        self.calls = []

    def encoder(self):
        return self.angles.copy()

    def angle_max_speed(self, speed):
        self.calls.append(("speed", speed))

    def set_angle_joints(self, *angles, wait):
        self.angles = list(angles)
        self.calls.append(("angles", angles, wait))

    def pick(self):
        self.status = 1
        self.calls.append(("pick",))

    def place(self):
        self.status = 0
        self.calls.append(("place",))

    def end_effector_status(self):
        return self.status

    def set_speed_joints(self, *speeds):
        self.calls.append(("stop", speeds))


def test_cell_sweep_sequence_uses_transit_between_every_cell() -> None:
    sequence = cell_sweep_pose_sequence()

    assert sequence[:10] == [
        ("move", "cell_1_hover"),
        ("move", "cell_1_grasp"),
        ("gripper", "close"),
        ("move", "cell_1_hover"),
        ("move", "transit"),
        ("move", "cell_2_hover"),
        ("move", "cell_2_grasp"),
        ("gripper", "open"),
        ("move", "cell_2_hover"),
        ("move", "transit"),
    ]
    assert len(sequence) == 80
    assert sequence[-10:] == [
        ("move", "cell_8_hover"),
        ("move", "cell_8_grasp"),
        ("gripper", "close"),
        ("move", "cell_8_hover"),
        ("move", "transit"),
        ("move", "cell_9_hover"),
        ("move", "cell_9_grasp"),
        ("gripper", "open"),
        ("move", "cell_9_hover"),
        ("move", "transit"),
    ]


def test_execute_cell_sweep_moves_one_piece_through_all_cells() -> None:
    poses = {
        name: (float(index), -10.0, -140.0, 60.0)
        for index, name in enumerate(sorted(REQUIRED_POSES))
    }
    fake = FakeRobot()
    driver = RobomationDriver(
        RobotPoseProfile(poses, max_speed=60),
        robot=fake,
        gripper_settle_s=0,
        sleeper=lambda _seconds: None,
    )
    reports = []

    execute_cell_sweep(
        driver,
        status_reader=lambda: fake.status,
        reporter=reports.append,
    )

    assert fake.calls.count(("pick",)) == 8
    assert fake.calls.count(("place",)) == 8
    assert reports[0] == "[1/8] cell_1 -> cell_2"
    assert reports[-1] == "[8/8] cell_8 -> cell_9 complete"
