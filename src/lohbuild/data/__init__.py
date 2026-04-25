from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from typing import Any

import yaml

from ..model import (
    BaseItem,
    CubeEffect,
    CubeRecipe,
    DamageType,
    GearSlot,
    Modifier,
    ModifierSlot,
    Passive,
    ResourceCost,
    Skill,
    SkillEffect,
    SkillTag,
    StatBlock,
)


def _statblock(d: dict[str, Any] | None) -> StatBlock:
    if not d:
        return StatBlock()
    resists = {DamageType(k): float(v) for k, v in (d.get("resists") or {}).items()}
    skill_ranks = {str(k): int(v) for k, v in (d.get("skill_ranks") or {}).items()}
    return StatBlock(
        life=float(d.get("life", 0.0)),
        armor=float(d.get("armor", 0.0)),
        resist_all=float(d.get("resist_all", 0.0)),
        resists=resists,
        damage_reduction=float(d.get("damage_reduction", 0.0)),
        dr_vs_close=float(d.get("dr_vs_close", 0.0)),
        dr_vs_distant=float(d.get("dr_vs_distant", 0.0)),
        weapon_damage=float(d.get("weapon_damage", 0.0)),
        attack_speed=float(d.get("attack_speed", 1.0)),
        crit_chance=float(d.get("crit_chance", 0.05)),
        crit_damage=float(d.get("crit_damage", 1.5)),
        additive_damage=float(d.get("additive_damage", 0.0)),
        multiplicative_damage=float(d.get("multiplicative_damage", 1.0)),
        vulnerable_damage=float(d.get("vulnerable_damage", 1.2)),
        skill_ranks=skill_ranks,
    )


def _skill_effect(d: dict[str, Any]) -> SkillEffect:
    return SkillEffect(
        base_damage_pct=float(d["base_damage_pct"]),
        damage_type=DamageType(d.get("damage_type", "shadow")),
        cooldown=float(d.get("cooldown", 0.0)),
        cast_time=float(d.get("cast_time", 0.5)),
        aoe=bool(d.get("aoe", False)),
        targets=int(d.get("targets", 1)),
        applies_vulnerable=bool(d.get("applies_vulnerable", False)),
        self_buff=_statblock(d.get("self_buff")) if d.get("self_buff") else None,
    )


def _modifier(d: dict[str, Any], parent_skill: str) -> Modifier:
    return Modifier(
        id=d["id"],
        name=d["name"],
        slot=ModifierSlot(d["slot"]),
        parent_skill=parent_skill,
        stats=_statblock(d.get("stats")),
        requires_rank=int(d.get("requires_rank", 1)),
        placeholder=bool(d.get("placeholder", False)),
        source_url=d.get("source_url"),
        notes=d.get("notes", ""),
    )


def _skill(d: dict[str, Any]) -> Skill:
    cost = None
    if d.get("cost"):
        cost = ResourceCost(resource=d["cost"]["resource"], amount=float(d["cost"]["amount"]))
    skill_id = d["id"]
    modifiers = [_modifier(m, parent_skill=skill_id) for m in d.get("modifiers", [])]
    return Skill(
        id=skill_id,
        name=d["name"],
        tag=SkillTag(d["tag"]),
        max_rank=int(d.get("max_rank", 5)),
        base_effect=_skill_effect(d["base_effect"]),
        per_rank_increment=float(d.get("per_rank_increment", 0.1)),
        cost=cost,
        min_level=int(d.get("min_level", 1)),
        placeholder=bool(d.get("placeholder", False)),
        source_url=d.get("source_url"),
        modifiers=modifiers,
    )


def _passive(d: dict[str, Any]) -> Passive:
    return Passive(
        id=d["id"],
        name=d["name"],
        max_rank=int(d.get("max_rank", 3)),
        per_rank=_statblock(d["per_rank"]),
        min_level=int(d.get("min_level", 1)),
        requires=list(d.get("requires", [])),
        placeholder=bool(d.get("placeholder", False)),
        source_url=d.get("source_url"),
    )


def _cube_recipe(d: dict[str, Any]) -> CubeRecipe:
    effect = None
    if d.get("effect"):
        effect = CubeEffect(
            stats=_statblock(d["effect"].get("stats")),
            notes=d["effect"].get("notes", ""),
        )
    return CubeRecipe(
        id=d["id"],
        name=d["name"],
        inputs=list(d.get("inputs", [])),
        output=d.get("output"),
        effect=effect,
        placeholder=bool(d.get("placeholder", False)),
        source_url=d.get("source_url"),
    )


def _base_item(d: dict[str, Any]) -> BaseItem:
    return BaseItem(
        id=d["id"],
        slot=GearSlot(d["slot"]),
        intrinsic=_statblock(d.get("intrinsic")),
        socket_count=int(d.get("socket_count", 0)),
        placeholder=bool(d.get("placeholder", False)),
    )


@dataclass
class ClassData:
    class_id: str
    name: str
    base_stats_per_level: StatBlock
    skills: dict[str, Skill]
    passives: dict[str, Passive]


@dataclass
class ItemizationData:
    base_items: dict[str, BaseItem]
    cube_recipes: dict[str, CubeRecipe]


def load_class(class_id: str) -> ClassData:
    raw = yaml.safe_load(files(__package__).joinpath(f"classes/{class_id}.yaml").read_text())
    skills = {s["id"]: _skill(s) for s in raw.get("skills", [])}
    passives = {p["id"]: _passive(p) for p in raw.get("passives", [])}
    return ClassData(
        class_id=raw["class_id"],
        name=raw["name"],
        base_stats_per_level=_statblock(raw.get("base_stats_per_level")),
        skills=skills,
        passives=passives,
    )


def load_itemization() -> ItemizationData:
    raw = yaml.safe_load(files(__package__).joinpath("itemization.yaml").read_text())
    return ItemizationData(
        base_items={b["id"]: _base_item(b) for b in raw.get("base_items", [])},
        cube_recipes={r["id"]: _cube_recipe(r) for r in raw.get("cube_recipes", [])},
    )
