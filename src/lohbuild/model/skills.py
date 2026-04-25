from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .stats import DamageType, StatBlock


class SkillTag(str, Enum):
    BASIC = "basic"
    CORE = "core"
    DEFENSIVE = "defensive"
    MOBILITY = "mobility"
    CONJURATION = "conjuration"
    MASTERY = "mastery"
    ULTIMATE = "ultimate"
    PASSIVE = "passive"


@dataclass
class ResourceCost:
    resource: str
    amount: float


@dataclass
class SkillEffect:
    """Per-rank damage and behavior numbers for a single active skill."""

    base_damage_pct: float
    damage_type: DamageType
    cooldown: float = 0.0
    cast_time: float = 0.5
    aoe: bool = False
    targets: int = 1
    applies_vulnerable: bool = False
    self_buff: StatBlock | None = None


@dataclass
class Skill:
    id: str
    name: str
    tag: SkillTag
    max_rank: int
    base_effect: SkillEffect
    per_rank_increment: float = 0.1
    cost: ResourceCost | None = None
    min_level: int = 1
    placeholder: bool = False
    source_url: str | None = None

    def effect_at(self, rank: int) -> SkillEffect:
        if rank <= 0:
            raise ValueError("rank must be >= 1")
        rank = min(rank, self.max_rank)
        scaled = SkillEffect(
            base_damage_pct=self.base_effect.base_damage_pct
            * (1 + self.per_rank_increment * (rank - 1)),
            damage_type=self.base_effect.damage_type,
            cooldown=self.base_effect.cooldown,
            cast_time=self.base_effect.cast_time,
            aoe=self.base_effect.aoe,
            targets=self.base_effect.targets,
            applies_vulnerable=self.base_effect.applies_vulnerable,
            self_buff=self.base_effect.self_buff,
        )
        return scaled


@dataclass
class Passive:
    id: str
    name: str
    max_rank: int
    per_rank: StatBlock
    min_level: int = 1
    requires: list[str] = field(default_factory=list)
    placeholder: bool = False
    source_url: str | None = None

    def stats_at(self, rank: int) -> StatBlock:
        if rank <= 0:
            return StatBlock()
        rank = min(rank, self.max_rank)
        out = StatBlock()
        for _ in range(rank):
            out = out.merge(self.per_rank)
        return out
