import pytest

from raccoonbot_game.tools.probe_robot import format_snapshot, official_connection_state, probe


class FakeRobot:
    def __init__(self, *, port_name):
        self.port_name = port_name
        self.disposed = False

    def encoder(self):
        return [1.0, -2.0, -3.0, 4.0]

    def battery(self):
        return 4.1

    def signal_strength(self):
        return -42

    def end_effector_device(self):
        return 1

    def end_effector_status(self):
        return 0

    def dispose(self):
        self.disposed = True


def test_probe_reads_sensors_and_disposes(capsys) -> None:
    robots = []

    def factory(**kwargs):
        robot = FakeRobot(**kwargs)
        robots.append(robot)
        return robot

    snapshots = probe(
        factory,
        port="/dev/test-dongle",
        samples=2,
        interval_s=0,
    )

    assert len(snapshots) == 2
    assert robots[0].port_name == "/dev/test-dongle"
    assert robots[0].disposed is True
    assert "sample=2 encoders=[1.0, -2.0, -3.0, 4.0]" in capsys.readouterr().out


def test_format_snapshot() -> None:
    text = format_snapshot(
        3,
        {
            "encoders": [0, -10, -140, 60],
            "battery_v": 4.0,
            "signal_dbm": -30,
            "end_effector_device": 1,
            "end_effector_status": 0,
        },
    )
    assert text == (
        "sample=3 encoders=[0, -10, -140, 60] battery=4.0V signal=-30dBm "
        "end_effector=1 status=0"
    )


def test_probe_rejects_official_disconnected_state_and_disposes() -> None:
    class Connector:
        def is_connected(self):
            return False

    robot = FakeRobot(port_name="/dev/test-dongle")
    robot._roboid = type("Roboid", (), {"_connector": Connector()})()

    with pytest.raises(RuntimeError, match="no RaccoonBot is paired"):
        probe(
            lambda **_kwargs: robot,
            port="/dev/test-dongle",
            samples=1,
            interval_s=0,
        )

    assert robot.disposed is True
    assert official_connection_state(robot) is False
