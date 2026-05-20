from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


class VersionBump(str, Enum):
    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"


@dataclass(frozen=True, slots=True)
class VersionTriple:
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def bump(self, level: VersionBump) -> VersionTriple:
        if level is VersionBump.MAJOR:
            return VersionTriple(self.major + 1, 0, 0)
        if level is VersionBump.MINOR:
            return VersionTriple(self.major, self.minor + 1, 0)
        return VersionTriple(self.major, self.minor, self.patch + 1)


def parse_version(raw: str) -> VersionTriple:
    match = _VERSION_RE.match(raw.strip())
    if not match:
        raise ValueError(f"Invalid semver: {raw!r}")
    return VersionTriple(int(match.group(1)), int(match.group(2)), int(match.group(3)))


@dataclass(frozen=True, slots=True)
class AgentCompositionSnapshot:
    """Brick ids grouped by slot — used to decide PATCH vs MINOR vs MAJOR."""

    slots: dict[str, list[int]]


def bump_agent_version(
    current: str,
    *,
    previous: AgentCompositionSnapshot | None,
    current_composition: AgentCompositionSnapshot,
    runner_role_changed: bool,
    mission_scope_changed: bool,
    cosmetic_only: bool = False,
) -> str:
    """Return next semver string for a catalog agent version."""
    base = parse_version(current)
    if cosmetic_only and previous is not None and previous.slots == current_composition.slots:
        return str(base.bump(VersionBump.PATCH))

    if mission_scope_changed or runner_role_changed:
        return str(base.bump(VersionBump.MAJOR))

    if previous is None:
        return str(base)

    prev_slots = previous.slots
    curr_slots = current_composition.slots
    if prev_slots == curr_slots:
        return str(base.bump(VersionBump.PATCH))

    prev_flat = {(slot, brick_id) for slot, ids in prev_slots.items() for brick_id in ids}
    curr_flat = {(slot, brick_id) for slot, ids in curr_slots.items() for brick_id in ids}
    if curr_flat - prev_flat and not (prev_flat - curr_flat):
        return str(base.bump(VersionBump.MINOR))
    if prev_flat - curr_flat:
        return str(base.bump(VersionBump.MAJOR))
    return str(base.bump(VersionBump.MINOR))
