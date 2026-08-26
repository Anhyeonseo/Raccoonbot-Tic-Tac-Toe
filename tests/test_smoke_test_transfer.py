import pytest

from raccoonbot_game.tools.smoke_test_transfer import source_name_for, transfer_test


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
        self.calls.append(("angles", tuple(angles), wait))

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


def test_source_name_supports_stock_and_board_cell() -> None:
    assert source_name_for(stock=2, from_cell=None) == "stock_2"
    assert source_name_for(stock=None, from_cell=5) == "cell_5"
    with pytest.raises(ValueError, match="either stock or from-cell"):
        source_name_for(stock=1, from_cell=5)
    with pytest.raises(ValueError, match="source is required"):
        source_name_for(stock=None, from_cell=None)


def test_transfer_moves_piece_from_stock_to_cell_and_returns_to_transit(capsys) -> None:
    robot = FakeRobot(port_name="/dev/test")
    transit = [0, -10, -140, 60]

    transfer_test(
        lambda **_kwargs: robot,
        port="/dev/test",
        transit=transit,
        source_hover=[40, -30, -90, -40],
        source_grasp=[40, -40, -100, -40],
        target_hover=[0, -20, -100, -40],
        target_grasp=[0, -30, -105, -45],
        speed=10,
        source_name="stock_1",
        target_name="cell_5",
        settle_s=0,
        gripper_settle_s=0,
        sleeper=lambda _: None,
    )

    assert robot.angles == transit
    assert robot.status == 0
    assert robot.calls.count(("pick",)) == 1
    assert robot.calls.count(("place",)) == 2
    assert robot.calls[-2:] == [("stop", (0, 0, 0, 0)), ("dispose",)]
    output = capsys.readouterr().out
    assert "transfer=stock_1->cell_5" in output
    assert "reached stock_1_grasp=" in output
    assert "reached transit_with_piece=" in output
    assert "reached cell_5_grasp=" in output
