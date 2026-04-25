from __future__ import annotations

from dataclasses import dataclass, field

from .gear import Loadout
from .skills import Passive, Skill
from .stats import StatBlock


@dataclass
class SkillAllocation:
    skill_ranks: dict[str, int] = field(default_factory=dict)
    passive_ranks: dict[str, int] = field(default_factory=dict)


@dataclass
class Build:
    class_id: str
    level: int
    allocation: SkillAllocation = field(default_factory=SkillAllocation)
    skill_bar: list[str] = field(default_factory=list)
    loadout: Loadout = field(default_factory=Loadout)
    base_stats: StatBlock = field(default_factory=StatBlock)

    def total_stats(
        self,
        skills: dict[str, Skill],
        passives: dict[str, Passive],
    ) -> StatBlock:
        out = self.base_stats
        for pid, rank in self.allocation.passive_ranks.items():
            passive = passives.get(pid)
            if passive is None:
                continue
            out = out.merge(passive.stats_at(rank))
        out = out.merge(self.loadout.aggregate_stats())
        return out
