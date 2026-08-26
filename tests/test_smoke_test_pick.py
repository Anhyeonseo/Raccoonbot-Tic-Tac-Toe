import pytest

from raccoonbot_game.tools.smoke_test_pick import pose_prefix_for, smoke_test


class FakeRobot:
    def __init__(self, *, port_name):
        self.angles = [0, -10, -140, 60]
        self.status = 0
        self.calls = []

    def battery(self):
        return 3.9

    def end_effector_device(self):
        return 4

    def end_effector_status(self):
        return self.status

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

    def set_speed_joints(self, *speeds):
        self.calls.append(("stop", speeds))

    def dispose(self):
        self.calls.append(("dispose",))


def test_pose_prefix_supports_board_cells_and_stock() -> None:
    assert pose_prefix_for(cell=None, stock=None) == "cell_1"
    assert pose_prefix_for(cell=9, stock=None) == "cell_9"
    assert pose_prefix_for(cell=None, stock=3) == "stock_3"
    with pytest.raises(ValueError, match="either cell or stock"):
        pose_prefix_for(cell=1, stock=1)


def test_pick_smoke_cycle_returns_to_transit_and_leaves_gripper_open() -> None:
    robot = FakeRobot(port_name="/dev/test")
    transit = [0, -10, -140, 60]
    hover = [38, -20, -118, -35]
    grasp = [38, -24, -110, -45]

    smoke_test(
        lambda **_kwargs: robot,
        port="/dev/test",
        transit=transit,
        hover=hover,
        grasp=grasp,
        speed=10,
        settle_s=0,
        gripper_settle_s=0,
        sleeper=lambda _: None,
    )

    assert robot.angles == transit
    assert robot.status == 0
    assert robot.calls.count(("pick",)) == 1
    assert robot.calls.count(("place",)) == 2
    assert robot.calls[-2:] == [("stop", (0, 0, 0, 0)), ("dispose",)]


def test_pick_smoke_cycle_accepts_another_cell_pose_prefix(capsys) -> None:
    robot = FakeRobot(port_name="/dev/test")

    smoke_test(
        lambda **_kwargs: robot,
        port="/dev/test",
        transit=[0, -10, -140, 60],
        hover=[0, -10, -126, -44],
        grasp=[0, -10, -132, -33],
        speed=10,
        pose_prefix="cell_2",
        settle_s=0,
        gripper_settle_s=0,
        sleeper=lambda _: None,
    )

    output = capsys.readouterr().out
    assert "reached cell_2_hover=" in output
    assert "reached cell_2_grasp=" in output


def test_pick_smoke_dry_run_does_not_actuate_gripper(capsys) -> None:
    robot = FakeRobot(port_name="/dev/test")

    smoke_test(
        lambda **_kwargs: robot,
        port="/dev/test",
        transit=[0, -10, -140, 60],
        hover=[10, -20, -120, 20],
        grasp=[10, -25, -115, 10],
        speed=10,
        actuate_gripper=False,
        settle_s=0,
        gripper_settle_s=0,
        sleeper=lambda _: None,
    )

    assert ("pick",) not in robot.calls
    assert ("place",) not in robot.calls
    assert "dry run: gripper remains unchanged" in capsys.readouterr().out
