import json

import pytest

from raccoonbot_game.tools.teach_pose import load_pose, save_pose, teach_pose, validate_angles


class FakeRobot:
    def __init__(self, *, port_name):
        self.port_name = port_name
        self.calls = []
        self.angles = [1.2344, -10, -140, 60]

    def battery(self):
        return 3.9

    def encoder(self):
        return self.angles

    def angle_max_speed(self, speed):
        self.calls.append(("speed", speed))

    def set_angle_joints(self, *angles, wait):
        self.angles = list(angles)
        self.calls.append(("angles", self.angles, wait))

    def button(self, name, event):
        return True

    def set_speed_joints(self, *speeds):
        self.calls.append(("stop", speeds))

    def motor(self, joint, on):
        self.calls.append(("motor", joint, on))

    def dispose(self):
        self.calls.append(("dispose",))


def make_template(path) -> None:
    path.write_text(
        json.dumps({"_warning": "template", "max_speed": 20, "poses": {"home": None}}),
        encoding="utf-8",
    )


def test_validate_angles_rounds_and_checks_limits() -> None:
    assert validate_angles([1.2344, -10, -140, 60]) == [1.234, -10.0, -140.0, 60.0]
    with pytest.raises(RuntimeError, match="J1"):
        validate_angles([121, -10, -140, 60])


def test_save_pose_creates_and_updates_partial_profile(tmp_path) -> None:
    template = tmp_path / "template.json"
    output = tmp_path / "poses.json"
    make_template(template)

    save_pose(template, output, "home", [1.2344, -10, -140, 60])

    raw = json.loads(output.read_text(encoding="utf-8"))
    assert raw["poses"]["home"] == [1.234, -10.0, -140.0, 60.0]
    assert not output.with_suffix(".json.tmp").exists()


def test_save_pose_clears_matching_provisional_marker(tmp_path) -> None:
    template = tmp_path / "template.json"
    output = tmp_path / "poses.json"
    make_template(template)
    raw = json.loads(template.read_text(encoding="utf-8"))
    raw["_provisional_poses"] = ["home"]
    output.write_text(json.dumps(raw), encoding="utf-8")

    save_pose(template, output, "home", [1, -10, -140, 60])

    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["_provisional_poses"] == []


def test_load_pose_reads_a_taught_pose(tmp_path) -> None:
    profile = tmp_path / "poses.json"
    profile.write_text(json.dumps({"poses": {"hover": [1, -20, -100, -40]}}), encoding="utf-8")

    assert load_pose(profile, "hover") == [1.0, -20.0, -100.0, -40.0]


def test_manual_teaching_can_move_to_saved_start_pose_before_release(tmp_path) -> None:
    template = tmp_path / "template.json"
    output = tmp_path / "poses.json"
    make_template(template)
    robot = FakeRobot(port_name="/dev/test")

    teach_pose(
        lambda **_kwargs: robot,
        template=template,
        output=output,
        pose_name="home",
        port="/dev/test",
        capture_current=False,
        timeout_s=1,
        start_pose=[2, -11, -139, 59],
        start_speed=8,
    )

    assert ("speed", 8) in robot.calls
    assert ("motor", -1, False) in robot.calls
    assert robot.calls.index(("speed", 8)) < robot.calls.index(("motor", -1, False))


def test_capture_current_never_releases_motors(tmp_path) -> None:
    template = tmp_path / "template.json"
    output = tmp_path / "poses.json"
    make_template(template)
    robot = FakeRobot(port_name="/dev/test")

    angles = teach_pose(
        lambda **_kwargs: robot,
        template=template,
        output=output,
        pose_name="home",
        port="/dev/test",
        capture_current=True,
        timeout_s=1,
    )

    assert angles == [1.234, -10.0, -140.0, 60.0]
    assert robot.calls == [
        ("stop", (0, 0, 0, 0)),
        ("stop", (0, 0, 0, 0)),
        ("dispose",),
    ]
