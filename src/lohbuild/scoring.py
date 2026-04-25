from __future__ import annotations

from dataclasses import dataclass

from .model import Build, EnemyProfile, Passive, Skill, StatBlock

# Hard-coded composite weighting for the leveling optimizer. Promote to a CLI
# flag once the model has real data to argue with.
DPS_WEIGHT = 0.6
EHP_WEIGHT = 0.4


def _armor_dr(armor: float, attacker_level: int) -> float:
    # D4-style approximation: DR = armor / (armor + 5.5 * level * 65).
    denom = armor + max(1.0, 5.5 * attacker_level * 65.0)
    return armor / denom if denom > 0 else 0.0


def _resist_dr(resist: float) -> float:
    return max(-0.5, min(resist, 0.7))


def effective_hp(stats: StatBlock, enemy: EnemyProfile) -> float:
    physical_share = 1.0 - enemy.elemental_damage_share
    armor_dr = _armor_dr(stats.armor, enemy.level)
    resist_dr = _resist_dr(stats.resist_all)

    incoming_multiplier = (
        physical_share * (1 - armor_dr)
        + enemy.elemental_damage_share * (1 - resist_dr)
    )
    incoming_multiplier *= 1 - stats.damage_reduction
    incoming_multiplier = max(incoming_multiplier, 0.05)
    return stats.life / incoming_multiplier


def hit_damage(skill: Skill, rank: int, stats: StatBlock) -> float:
    effect = skill.effect_at(rank)
    weapon = max(stats.weapon_damage, 1.0)
    base = effect.base_damage_pct * weapon
    additive = 1.0 + stats.additive_damage
    multiplicative = stats.multiplicative_damage
    crit = 1.0 + stats.crit_chance * (stats.crit_damage - 1.0)
    vuln = stats.vulnerable_damage if effect.applies_vulnerable else 1.0
    aoe_factor = effect.targets if effect.aoe else 1.0
    return base * additive * multiplicative * crit * vuln * aoe_factor


def skill_dps(skill: Skill, rank: int, stats: StatBlock) -> float:
    effect = skill.effect_at(rank)
    cycle = max(effect.cast_time / stats.attack_speed, 0.1)
    if effect.cooldown:
        cycle = max(cycle, effect.cooldown)
    return hit_damage(skill, rank, stats) / cycle


def rotation_dps(
    build: Build,
    skills: dict[str, Skill],
    stats: StatBlock,
) -> float:
    """Sum DPS across the build's skill bar.

    Cooldown skills are amortized at 1/cooldown; cast-time skills assume the
    player can keep one of them active each cycle. This will be replaced with
    a proper rotation simulator once skill resource costs are real.
    """

    if not build.skill_bar:
        # Default to all allocated active skills.
        bar = list(build.allocation.skill_ranks.keys())
    else:
        bar = build.skill_bar

    sustained_filler = 0.0
    cooldown_total = 0.0
    for sid in bar:
        skill = skills.get(sid)
        if skill is None:
            continue
        rank = build.allocation.skill_ranks.get(sid, 0)
        if rank <= 0:
            continue
        if skill.base_effect.cooldown > 0:
            cooldown_total += hit_damage(skill, rank, stats) / skill.base_effect.cooldown
        else:
            sustained_filler = max(sustained_filler, skill_dps(skill, rank, stats))
    return sustained_filler + cooldown_total


@dataclass
class Score:
    dps: float
    ehp: float
    composite: float


def score_build(
    build: Build,
    skills: dict[str, Skill],
    passives: dict[str, Passive],
    enemy: EnemyProfile | None = None,
) -> Score:
    enemy = enemy or EnemyProfile.at_level(build.level)
    stats = build.total_stats(skills, passives)
    dps = rotation_dps(build, skills, stats)
    ehp = effective_hp(stats, enemy)

    # Normalize against the enemy so the two terms are comparable: dps as
    # "fraction of enemy life per second", ehp as "enemy hits survived".
    dps_norm = dps / max(enemy.life, 1.0)
    ehp_norm = ehp / max(enemy.damage_per_hit, 1.0)
    composite = DPS_WEIGHT * dps_norm + EHP_WEIGHT * ehp_norm
    return Score(dps=dps, ehp=ehp, composite=composite)
