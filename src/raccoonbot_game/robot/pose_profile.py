from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


JointPose = tuple[float, float, float, float]
JOINT_LIMITS = ((-120.0, 120.0), (-90.0, 30.0), (-150.0, 0.0), (-105.0, 105.0))
REQUIRED_POSES = frozenset(
    {"home", "transit"}
    | {f"cell_{cell}_{level}" for cell in range(1, 10) for level in ("hover", "grasp")}
    | {f"stock_{stock}_{level}" for stock in range(1, 4) for level in ("hover", "grasp")}
)


@dataclass(frozen=True, slots=True)
class RobotPoseProfile:
    poses: dict[str, JointPose]
    max_speed: float = 30.0

    def __post_init__(self) -> None:
        missing = REQUIRED_POSES - self.poses.keys()
        if missing:
            raise ValueError(f"missing robot poses: {sorted(missing)}")
        if not 1.0 <= self.max_speed <= 100.0:
            raise ValueError("max_speed must be within 1..100")
        for name, angles in self.poses.items():
            if len(angles) != 4:
                raise ValueError(f"{name} must contain four joint angles")
            for joint, (angle, (low, high)) in enumerate(zip(angles, JOINT_LIMITS), start=1):
                if not low <= angle <= high:
                    raise ValueError(f"{name} joint {joint} is outside {low}..{high}: {angle}")

    def pose(self, name: str) -> JointPose:
        try:
            return self.poses[name]
        except KeyError as exc:
            raise KeyError(f"unknown taught pose: {name}") from exc

    @classmethod
    def load(cls, path: str | Path) -> "RobotPoseProfile":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        provisional = raw.get("_provisional_poses", [])
        if provisional:
            raise ValueError(f"provisional robot poses must be retaught: {sorted(provisional)}")
        unfinished = [name for name, values in raw["poses"].items() if values is None]
        if unfinished:
            raise ValueError(f"teaching values are still null: {unfinished}")
        poses = {name: tuple(float(value) for value in values) for name, values in raw["poses"].items()}
        return cls(poses=poses, max_speed=float(raw.get("max_speed", 30.0)))

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps({"max_speed": self.max_speed, "poses": self.poses}, indent=2),
            encoding="utf-8",
        )
