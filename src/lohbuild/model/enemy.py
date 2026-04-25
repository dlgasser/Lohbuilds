from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EnemyProfile:
    """Baseline enemy used for damage and EHP calculations at a given level."""

    level: int
    life: float
    armor: float
    damage_per_hit: float
    hits_per_second: float = 1.0
    elemental_damage_share: float = 0.4

    @classmethod
    def at_level(cls, level: int) -> "EnemyProfile":
        # Smooth placeholder curve until we have measured data.
        life = 100 * (1.0 + 0.18) ** level
        armor = 200 + 40 * level
        damage = 8 * (1.0 + 0.12) ** level
        return cls(level=level, life=life, armor=armor, damage_per_hit=damage)
