from __future__ import annotations

import copy
from dataclasses import dataclass, field

from .data import ClassData, ItemizationData
from .model import (
    Build,
    BaseItem,
    GearSlot,
    Item,
    Loadout,
    SkillAllocation,
)
from .model.enemy import EnemyProfile
from .scoring import Score, score_build


# Lord of Hatred ships with 83 total skill points. The exact per-level
# schedule is not public; we distribute linearly from level 2 to LEVEL_CAP_FOR_POINTS
# until datamines land. Override `points_at_level` if you have a real curve.
SKILL_POINTS_TOTAL = 83
LEVEL_CAP_FOR_POINTS = 70
MAX_BAR = 6


def points_at_level(level: int) -> int:
    if level <= 1:
        return 0
    if level >= LEVEL_CAP_FOR_POINTS:
        return SKILL_POINTS_TOTAL
    return round(SKILL_POINTS_TOTAL * (level - 1) / (LEVEL_CAP_FOR_POINTS - 1))


@dataclass
class LevelStep:
    level: int
    spent_on: str
    score: Score


@dataclass
class OptimizerResult:
    final_build: Build
    history: list[LevelStep] = field(default_factory=list)


def _starter_loadout(items: ItemizationData) -> Loadout:
    """Pick one placeholder item per slot. Real gear logic comes later."""

    by_slot: dict[GearSlot, BaseItem] = {}
    for base in items.base_items.values():
        by_slot.setdefault(base.slot, base)
    loadout = Loadout()
    for slot, base in by_slot.items():
        loadout.items[slot] = Item(base=base, item_power=1)
    # Park the defensive cube recipe in the cube as a generic placeholder.
    warding = items.cube_recipes.get("cube_warding_imbue")
    if warding:
        loadout.cube_residents.append(warding)
    return loadout


def _candidate_skill_targets(
    build: Build,
    cls: ClassData,
) -> list[str]:
    """Skills/passives the build could spend a point on at this level."""

    out: list[str] = []
    for skill in cls.skills.values():
        if skill.min_level > build.level:
            continue
        current = build.allocation.skill_ranks.get(skill.id, 0)
        if current < skill.max_rank:
            out.append(skill.id)
    for passive in cls.passives.values():
        if passive.min_level > build.level:
            continue
        # Honor prerequisite chain.
        if any(
            build.allocation.passive_ranks.get(req, 0) == 0 for req in passive.requires
        ):
            continue
        current = build.allocation.passive_ranks.get(passive.id, 0)
        if current < passive.max_rank:
            out.append(passive.id)
    return out


def _apply_point(build: Build, cls: ClassData, target_id: str) -> None:
    if target_id in cls.skills:
        build.allocation.skill_ranks[target_id] = (
            build.allocation.skill_ranks.get(target_id, 0) + 1
        )
        if target_id not in build.skill_bar and len(build.skill_bar) < MAX_BAR:
            build.skill_bar.append(target_id)
    elif target_id in cls.passives:
        build.allocation.passive_ranks[target_id] = (
            build.allocation.passive_ranks.get(target_id, 0) + 1
        )


def _trial_score(build: Build, cls: ClassData, target_id: str) -> Score:
    trial = copy.deepcopy(build)
    _apply_point(trial, cls, target_id)
    return score_build(trial, cls.skills, cls.passives)


def optimize_leveling(
    cls: ClassData,
    items: ItemizationData,
    level_cap: int = 70,
) -> OptimizerResult:
    build = Build(class_id=cls.class_id, level=1)
    build.loadout = _starter_loadout(items)
    history: list[LevelStep] = []
    spent = 0

    for level in range(1, level_cap + 1):
        build.level = level
        build.base_stats = _level_base_stats(cls, level)
        target = min(points_at_level(level), SKILL_POINTS_TOTAL)
        while spent < target:
            candidates = _candidate_skill_targets(build, cls)
            if not candidates:
                break
            best = max(candidates, key=lambda c: _trial_score(build, cls, c).composite)
            _apply_point(build, cls, best)
            spent += 1
            history.append(
                LevelStep(
                    level=level,
                    spent_on=best,
                    score=score_build(build, cls.skills, cls.passives),
                )
            )

    return OptimizerResult(final_build=build, history=history)


def _level_base_stats(cls: ClassData, level: int):
    out = cls.base_stats_per_level
    # Multiply the per-level block by `level` via repeated merge for
    # simplicity. A handful of merges per level is cheap.
    from .model import StatBlock

    total = StatBlock()
    for _ in range(level):
        total = total.merge(out)
    return total


def report(result: OptimizerResult, cls: ClassData) -> str:
    final = result.final_build
    final_score = score_build(final, cls.skills, cls.passives)
    points_spent = sum(final.allocation.skill_ranks.values()) + sum(
        final.allocation.passive_ranks.values()
    )
    lines = [
        f"Class: {cls.name} ({cls.class_id})",
        f"Level: {final.level}",
        f"Skill points: {points_spent}/{SKILL_POINTS_TOTAL} (cap reached at level {LEVEL_CAP_FOR_POINTS})",
        "",
        "Skill bar:",
    ]
    for sid in final.skill_bar:
        rank = final.allocation.skill_ranks.get(sid, 0)
        skill = cls.skills.get(sid)
        if skill:
            tag = "[placeholder]" if skill.placeholder else ""
            lines.append(f"  - {skill.name} ({sid}) rank {rank}/{skill.max_rank} {tag}")
    if final.allocation.passive_ranks:
        lines.append("")
        lines.append("Passives (legacy — removed from class tree in LoH):")
        for pid, rank in final.allocation.passive_ranks.items():
            passive = cls.passives.get(pid)
            if passive:
                tag = "[placeholder]" if passive.placeholder else ""
                lines.append(
                    f"  - {passive.name} ({pid}) rank {rank}/{passive.max_rank} {tag}"
                )
    lines.append("")
    lines.append("Cube residents:")
    if not final.loadout.cube_residents:
        lines.append("  (none)")
    for recipe in final.loadout.cube_residents:
        tag = "[placeholder]" if recipe.placeholder else ""
        lines.append(f"  - {recipe.name} ({recipe.id}) {tag}")
    enemy = EnemyProfile.at_level(final.level)
    lines.append("")
    lines.append("Score vs. baseline enemy at level {0}:".format(enemy.level))
    lines.append(f"  DPS:       {final_score.dps:>12,.0f}")
    lines.append(f"  EHP:       {final_score.ehp:>12,.0f}")
    lines.append(f"  Composite: {final_score.composite:>12.3f} (0.6*DPS + 0.4*EHP, normalized)")
    return "\n".join(lines)
