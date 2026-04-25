from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DamageType(str, Enum):
    PHYSICAL = "physical"
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    POISON = "poison"
    SHADOW = "shadow"


@dataclass
class StatBlock:
    """Aggregate stats for a build at a given level.

    Multiplicative buckets are stored as multipliers (1.0 == no bonus); flat
    buckets are stored in the natural unit. Resists and DR are clamped at the
    scoring layer, not here.
    """

    life: float = 0.0
    armor: float = 0.0

    resist_all: float = 0.0
    resists: dict[DamageType, float] = field(default_factory=dict)

    damage_reduction: float = 0.0
    dr_vs_close: float = 0.0
    dr_vs_distant: float = 0.0

    weapon_damage: float = 0.0
    attack_speed: float = 1.0

    crit_chance: float = 0.05
    crit_damage: float = 1.5

    additive_damage: float = 0.0
    multiplicative_damage: float = 1.0
    vulnerable_damage: float = 1.2

    skill_ranks: dict[str, int] = field(default_factory=dict)

    def merge(self, other: "StatBlock") -> "StatBlock":
        out = StatBlock(
            life=self.life + other.life,
            armor=self.armor + other.armor,
            resist_all=self.resist_all + other.resist_all,
            damage_reduction=1 - (1 - self.damage_reduction) * (1 - other.damage_reduction),
            dr_vs_close=1 - (1 - self.dr_vs_close) * (1 - other.dr_vs_close),
            dr_vs_distant=1 - (1 - self.dr_vs_distant) * (1 - other.dr_vs_distant),
            weapon_damage=self.weapon_damage + other.weapon_damage,
            attack_speed=self.attack_speed * other.attack_speed,
            crit_chance=self.crit_chance + (other.crit_chance - 0.05),
            crit_damage=self.crit_damage + (other.crit_damage - 1.5),
            additive_damage=self.additive_damage + other.additive_damage,
            multiplicative_damage=self.multiplicative_damage * other.multiplicative_damage,
            vulnerable_damage=self.vulnerable_damage + (other.vulnerable_damage - 1.2),
        )
        for dt, v in self.resists.items():
            out.resists[dt] = out.resists.get(dt, 0.0) + v
        for dt, v in other.resists.items():
            out.resists[dt] = out.resists.get(dt, 0.0) + v
        for k, v in self.skill_ranks.items():
            out.skill_ranks[k] = out.skill_ranks.get(k, 0) + v
        for k, v in other.skill_ranks.items():
            out.skill_ranks[k] = out.skill_ranks.get(k, 0) + v
        return out
