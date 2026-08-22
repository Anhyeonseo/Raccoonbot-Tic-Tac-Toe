from pathlib import Path

import pytest

from raccoonbot_game.robot.pose_profile import RobotPoseProfile


def test_shipped_template_cannot_be_used_before_teaching() -> None:
    template = Path(__file__).parents[1] / "config" / "robot_poses.template.json"
    with pytest.raises(ValueError, match="teaching values are still null"):
        RobotPoseProfile.load(template)
