from __future__ import annotations

import copy
from dataclasses import dataclass, field

from .data import ClassData, ItemizationData
from .model import (
    BaseItem,
    Build,
    GearSlot,
    Item,
    Loadout,
    ModifierSlot,
    SkillAllocation,
)
from .model.enemy import EnemyProfile
from .scoring import Score, score_build


# Lord of Hatred grants 1 skill point per character level (cap 70). The total
# pool is 83; the remaining 13 come from the Season Journey (similar to the
# patch 2.5 model). Pass --season-journey N at the CLI to model journey
# rewards on top of leveling. Override these constants if datamines reveal
# a different schedule.
SKILL_POINTS_TOTAL = 83
LEVELING_POINT_CAP = 70
MAX_BAR = 6


def points_at_level(level: int, season_journey: int = 0) -> int:
    leveling = max(0, min(level, LEVELING_POINT_CAP))
    journey = max(0, season_journey)
    return min(leveling + journey, SKILL_POINTS_TOTAL)


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
    by_slot: dict[GearSlot, BaseItem] = {}
    for base in items.base_items.values():
        by_slot.setdefault(base.slot, base)
    loadout = Loadout()
    for slot, base in by_slot.items():
        loadout.items[slot] = Item(base=base, item_power=1)
    warding = items.cube_recipes.get("cube_warding_imbue")
    if warding:
        loadout.cube_residents.append(warding)
    return loadout


def _candidate_targets(build: Build, cls: ClassData) -> list[str]:
    """Skill ranks, passives, and modifier picks the build could spend on."""

    from .model import SkillTag

    # Per Maxroll: "Only one ultimate can be chosen". Once any ultimate has
    # rank > 0, lock out the others (and their modifiers).
    chosen_ultimate = next(
        (
            sid
            for sid, rank in build.allocation.skill_ranks.items()
            if rank > 0 and cls.skills.get(sid) and cls.skills[sid].tag == SkillTag.ULTIMATE
        ),
        None,
    )

    out: list[str] = []
    for skill in cls.skills.values():
        if skill.min_level > build.level:
            continue
        if (
            skill.tag == SkillTag.ULTIMATE
            and chosen_ultimate is not None
            and skill.id != chosen_ultimate
        ):
            continue
        rank = build.allocation.skill_ranks.get(skill.id, 0)
        if rank < skill.max_rank:
            out.append(skill.id)
        # Modifier candidates require the parent skill to be at the prereq
        # rank and the (skill, slot) to be unfilled.
        taken_slots = {
            mod.slot
            for mod in skill.modifiers
            if mod.id in build.allocation.modifier_ids
        }
        for mod in skill.modifiers:
            if mod.id in build.allocation.modifier_ids:
                continue
            if rank < mod.requires_rank:
                continue
            if mod.slot in taken_slots:
                continue
            out.append(mod.id)
    for passive in cls.passives.values():
        if passive.min_level > build.level:
            continue
        if any(
            build.allocation.passive_ranks.get(req, 0) == 0
            for req in passive.requires
        ):
            continue
        if build.allocation.passive_ranks.get(passive.id, 0) < passive.max_rank:
            out.append(passive.id)
    return out


def _apply_point(build: Build, cls: ClassData, target_id: str) -> None:
    if target_id in cls.skills:
        build.allocation.skill_ranks[target_id] = (
            build.allocation.skill_ranks.get(target_id, 0) + 1
        )
        if target_id not in build.skill_bar and len(build.skill_bar) < MAX_BAR:
            build.skill_bar.append(target_id)
        return
    if target_id in cls.passives:
        build.allocation.passive_ranks[target_id] = (
            build.allocation.passive_ranks.get(target_id, 0) + 1
        )
        return
    # Modifier id — find it on its parent skill.
    for skill in cls.skills.values():
        for mod in skill.modifiers:
            if mod.id == target_id:
                build.allocation.modifier_ids.add(target_id)
                return


def _trial_score(build: Build, cls: ClassData, target_id: str) -> Score:
    trial = copy.deepcopy(build)
    _apply_point(trial, cls, target_id)
    return score_build(trial, cls.skills, cls.passives)


def optimize_leveling(
    cls: ClassData,
    items: ItemizationData,
    level_cap: int = 70,
    season_journey: int = 0,
) -> OptimizerResult:
    build = Build(class_id=cls.class_id, level=1)
    build.loadout = _starter_loadout(items)
    history: list[LevelStep] = []
    spent = 0

    for level in range(1, level_cap + 1):
        build.level = level
        build.base_stats = _level_base_stats(cls, level)
        target = points_at_level(level, season_journey=season_journey)
        while spent < target:
            candidates = _candidate_targets(build, cls)
            if not candidates:
                break
            best = max(
                candidates,
                key=lambda c: _trial_score(build, cls, c).composite,
            )
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
    from .model import StatBlock

    total = StatBlock()
    for _ in range(level):
        total = total.merge(out)
    return total


def report(
    result: OptimizerResult,
    cls: ClassData,
    season_journey: int = 0,
) -> str:
    final = result.final_build
    final_score = score_build(final, cls.skills, cls.passives)
    points_spent = (
        sum(final.allocation.skill_ranks.values())
        + sum(final.allocation.passive_ranks.values())
        + len(final.allocation.modifier_ids)
    )
    available = points_at_level(final.level, season_journey=season_journey)
    lines = [
        f"Class: {cls.name} ({cls.class_id})",
        f"Level: {final.level}",
        (
            f"Skill points: {points_spent}/{available} spent "
            f"(leveling cap {LEVELING_POINT_CAP}, journey +{season_journey}, total cap {SKILL_POINTS_TOTAL})"
        ),
        "",
        "Skill bar:",
    ]
    # Group modifiers by their parent skill so we can list them under it.
    mods_by_skill: dict[str, list] = {}
    for skill in cls.skills.values():
        for mod in skill.modifiers:
            if mod.id in final.allocation.modifier_ids:
                mods_by_skill.setdefault(skill.id, []).append(mod)

    for sid in final.skill_bar:
        rank = final.allocation.skill_ranks.get(sid, 0)
        skill = cls.skills.get(sid)
        if not skill:
            continue
        tag = "[placeholder]" if skill.placeholder else ""
        lines.append(f"  - {skill.name} ({sid}) rank {rank}/{skill.max_rank} {tag}")
        for mod in mods_by_skill.get(sid, []):
            mod_tag = "[placeholder]" if mod.placeholder else ""
            lines.append(f"      • [{mod.slot.value}] {mod.name} {mod_tag}")

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
