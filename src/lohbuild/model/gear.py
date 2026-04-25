from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .stats import StatBlock


class GearSlot(str, Enum):
    HELM = "helm"
    CHEST = "chest"
    GLOVES = "gloves"
    PANTS = "pants"
    BOOTS = "boots"
    AMULET = "amulet"
    RING_1 = "ring_1"
    RING_2 = "ring_2"
    WEAPON_MAIN = "weapon_main"
    WEAPON_OFF = "weapon_off"
    FOCUS = "focus"


@dataclass
class Affix:
    id: str
    stats: StatBlock
    tempered: bool = False


@dataclass
class Socket:
    """A gem / rune / cube-granted socket. Empty by default."""

    kind: str = "gem"
    fill_id: str | None = None
    stats: StatBlock = field(default_factory=StatBlock)


@dataclass
class CubeEffect:
    """The runtime effect produced by a CubeRecipe.

    Modeled as flat stat additions today; once the expansion lands we will
    extend this to support conditional triggers (on-hit, on-cooldown, etc.)
    without breaking callers that only read .stats.
    """

    stats: StatBlock = field(default_factory=StatBlock)
    notes: str = ""


@dataclass
class CubeRecipe:
    """Horadric Cube recipe.

    Inputs/outputs are intentionally loose strings until itemization data is
    available. Each recipe optionally produces a passive `effect` that the
    build can benefit from while the recipe is "active" (whatever active turns
    out to mean — equipped output, cube-resident, etc.).
    """

    id: str
    name: str
    inputs: list[str] = field(default_factory=list)
    output: str | None = None
    effect: CubeEffect | None = None
    placeholder: bool = False
    source_url: str | None = None


@dataclass
class BaseItem:
    id: str
    slot: GearSlot
    intrinsic: StatBlock = field(default_factory=StatBlock)
    socket_count: int = 0
    placeholder: bool = False


@dataclass
class Item:
    base: BaseItem
    item_power: int = 1
    affixes: list[Affix] = field(default_factory=list)
    sockets: list[Socket] = field(default_factory=list)
    masterwork: int = 0
    cube_imbue: CubeRecipe | None = None

    def aggregate_stats(self) -> StatBlock:
        out = self.base.intrinsic
        for a in self.affixes:
            out = out.merge(a.stats)
        for s in self.sockets:
            out = out.merge(s.stats)
        if self.cube_imbue and self.cube_imbue.effect:
            out = out.merge(self.cube_imbue.effect.stats)
        if self.masterwork:
            mw = StatBlock(multiplicative_damage=1.0 + 0.005 * self.masterwork)
            out = out.merge(mw)
        return out


@dataclass
class Loadout:
    """Equipped gear plus any cube-resident recipes.

    `cube_residents` carries CubeRecipes whose effect applies even though they
    are not imbued into a specific item — a hedge against the expansion
    shipping a "powers parked in the cube" mechanic similar to D3's Kanai's
    Cube.
    """

    items: dict[GearSlot, Item] = field(default_factory=dict)
    cube_residents: list[CubeRecipe] = field(default_factory=list)

    def aggregate_stats(self) -> StatBlock:
        out = StatBlock()
        for item in self.items.values():
            out = out.merge(item.aggregate_stats())
        for recipe in self.cube_residents:
            if recipe.effect:
                out = out.merge(recipe.effect.stats)
        return out
