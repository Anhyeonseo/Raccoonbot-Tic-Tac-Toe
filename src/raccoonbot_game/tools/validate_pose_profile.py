from __future__ import annotations

import argparse
from pathlib import Path

from raccoonbot_game.robot.pose_profile import RobotPoseProfile


def main() -> None:
    parser = argparse.ArgumentParser(description="RaccoonBot teaching 자세 JSON 검증")
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    try:
        profile = RobotPoseProfile.load(args.profile)
    except (KeyError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    print(f"OK: {len(profile.poses)} poses, max_speed={profile.max_speed}")


if __name__ == "__main__":
    main()
