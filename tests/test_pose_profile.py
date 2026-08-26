import json

import pytest

from raccoonbot_game.robot.pose_profile import REQUIRED_POSES, RobotPoseProfile


def valid_poses() -> dict[str, tuple[float, float, float, float]]:
    return {name: (0.0, -10.0, -100.0, 20.0) for name in REQUIRED_POSES}


def test_profile_round_trip(tmp_path) -> None:
    path = tmp_path / "poses.json"
    original = RobotPoseProfile(valid_poses(), max_speed=18)
    original.save(path)
    assert RobotPoseProfile.load(path) == original


def test_profile_requires_every_physical_pose() -> None:
    poses = valid_poses()
    del poses["cell_9_grasp"]
    with pytest.raises(ValueError, match="cell_9_grasp"):
        RobotPoseProfile(poses)


def test_profile_rejects_joint_limit_violation() -> None:
    poses = valid_poses()
    poses["home"] = (121.0, -10.0, -100.0, 20.0)
    with pytest.raises(ValueError, match="joint 1"):
        RobotPoseProfile(poses)


def test_provisional_pose_file_is_rejected(tmp_path) -> None:
    poses = {name: list(values) for name, values in valid_poses().items()}
    path = tmp_path / "poses.json"
    path.write_text(
        json.dumps({"_provisional_poses": ["home"], "poses": poses}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="provisional robot poses"):
        RobotPoseProfile.load(path)
