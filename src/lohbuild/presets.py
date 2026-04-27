"""
Known community build presets for comparison against the greedy optimizer.

Modifier stat values in warlock.yaml are placeholder approximations; preset
scores will shift once real conditional-trigger values are modeled. Preset
sources are noted per-entry.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from .data import ClassData, ItemizationData
from .model import Build, Loadout, SkillAllocation, StatBlock
from .model.skills import Skill
from .optimizer import _level_base_stats, _starter_loadout
from .scoring import Score, score_build


@dataclass
class Preset:
    id: str
    name: str
    description: str
    source: str
    # skill id -> target rank at cap
    skill_ranks: dict[str, int] = field(default_factory=dict)
    # modifier ids to take (binary — no rank)
    modifier_ids: set[str] = field(default_factory=set)
    # explicit skill bar order (up to 6); filled left-to-right
    skill_bar: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Shadow Claw / Dread Claws leveling preset (Mobalytics community guide)
# Source: mobalytics.gg/diablo-4/builds/shadow-claw-levelling-build-1-70
# Point budget: 83 (level-70 + 13 Season Journey)
# Modifier stat values are placeholder — real effects are conditional triggers.
# ---------------------------------------------------------------------------

SHADOW_CLAW = Preset(
    id="shadow_claw",
    name="Shadow Claw (Dread Claws leveling)",
    description=(
        "Abyss-school Dread Claws as the primary damage skill. "
        "Hellion Sting for Wrath generation, Metamorphosis as the ultimate. "
        "Infernal Breath + Wall of Agony round out damage and survivability."
    ),
    source="mobalytics.gg/diablo-4/builds/shadow-claw-levelling-build-1-70 (community, not verified)",
    skill_ranks={
        "dread_claws":     15,  # 15 pts — core, main Abyss damage skill
        "hellion_sting":   10,  # 10 pts — basic, Wrath generator
        "metamorphosis":   15,  # 15 pts — ultimate
        "wall_of_agony":   10,  # 10 pts — defensive
        "infernal_breath": 12,  # 12 pts — archfiend, Abyss cleave
        "nether_step":      7,  #  7 pts — mobility
    },
    modifier_ids={
        # Dread Claws
        "dc_e1_damage",   # Damage (+20% mult)
        "dc_e2_vuln",     # Vulnerable (+40% vuln — Shadowform synergy)
        "dc_v_cascade",   # Cascading Dread (+30% mult, highest ST)
        # Hellion Sting
        "hs_e1_damage",   # Damage (+20% mult)
        "hs_e2_evis",     # Eviscerate (+10% mult)
        "hs_v_swipe",     # Demonic Swipe (+20% mult)
        # Metamorphosis
        "meta_e1_scale",  # Damage Scaling (+10% mult)
        "meta_e2_phase",  # Phase 2 Enrage (+20% mult)
        "meta_v_destruc", # Destruction Demon (+30% mult)
        # Wall of Agony
        "wa_e1_knock",    # Knock Down (+5% mult)
        "wa_e2_damage",   # Damage (+10% mult)
        # Infernal Breath
        "ib_e1_ramping",  # Ramping Damage (+15% mult)
        "ib_e2_heavy",    # Heavy Impact Damage (+40% mult)
        # Nether Step
        "ns_e1_dr",       # Damage Reduction (+10% DR)
    },
    skill_bar=[
        "hellion_sting",
        "dread_claws",
        "infernal_breath",
        "wall_of_agony",
        "nether_step",
        "metamorphosis",
    ],
)

PRESETS: dict[str, Preset] = {
    SHADOW_CLAW.id: SHADOW_CLAW,
}


def build_from_preset(
    preset: Preset,
    cls: ClassData,
    items: ItemizationData,
    level: int = 70,
    season_journey: int = 0,
) -> Build:
    build = Build(class_id=cls.class_id, level=level)
    build.loadout = _starter_loadout(items)
    build.base_stats = _level_base_stats(cls, level)

    alloc = SkillAllocation()
    for sid, rank in preset.skill_ranks.items():
        if sid in cls.skills:
            alloc.skill_ranks[sid] = min(rank, cls.skills[sid].max_rank)
    for mid in preset.modifier_ids:
        alloc.modifier_ids.add(mid)
    build.allocation = alloc

    bar = [sid for sid in preset.skill_bar if sid in cls.skills]
    build.skill_bar = bar[:6]

    return build


def report_preset(
    preset: Preset,
    build: Build,
    cls: ClassData,
) -> str:
    score = score_build(build, cls.skills, cls.passives)
    points_spent = (
        sum(build.allocation.skill_ranks.values())
        + len(build.allocation.modifier_ids)
    )
    lines = [
        f"Preset: {preset.name}",
        f"Source: {preset.source}",
        f"",
        f"Skill points: {points_spent} spent",
        "",
        "Skill bar:",
    ]
    mods_by_skill: dict[str, list] = {}
    for skill in cls.skills.values():
        for mod in skill.modifiers:
            if mod.id in build.allocation.modifier_ids:
                mods_by_skill.setdefault(skill.id, []).append(mod)

    for sid in build.skill_bar:
        rank = build.allocation.skill_ranks.get(sid, 0)
        skill = cls.skills.get(sid)
        if not skill:
            continue
        lines.append(f"  - {skill.name} ({sid}) rank {rank}/{skill.max_rank}")
        for mod in mods_by_skill.get(sid, []):
            mod_tag = "[placeholder]" if mod.placeholder else ""
            lines.append(f"      • [{mod.slot.value}] {mod.name} {mod_tag}")

    from .model.enemy import EnemyProfile
    enemy = EnemyProfile.at_level(build.level)
    lines += [
        "",
        f"Score vs. baseline enemy at level {enemy.level}:",
        f"  DPS:       {score.dps:>12,.0f}",
        f"  EHP:       {score.ehp:>12,.0f}",
        f"  Composite: {score.composite:>12.3f} (0.6*DPS + 0.4*EHP, normalized)",
    ]
    return "\n".join(lines)
