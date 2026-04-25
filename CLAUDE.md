# CLAUDE.md — project memory for Lohbuilds

## What this project is

A Python build optimizer for the Diablo 4 *Lord of Hatred* expansion (release
2026-04-28). Initial scope is a **Warlock 1-70 leveling build** that does not
require unique drops. Target runtime is Windows 11.

## Branch convention

All development happens on `claude/diablo4-warlock-optimizer-5G7BW`. Do not
push other branches without explicit user approval.

## Repo layout

```
src/lohbuild/
  cli.py                 entry point: lohbuild warlock --level 70
  scoring.py             DPS / EHP / composite score
  optimizer.py           greedy 1-70 leveling allocator
  model/                 dataclasses (stats, skills, gear, build, enemy)
  data/                  YAML data + loader
    classes/warlock.yaml
    itemization.yaml
```

## Hard-coded design choices (re-evaluate before changing)

- **Composite score:** `0.6 * normalized_DPS + 0.4 * normalized_EHP`. Promote
  to a CLI flag once real data is in. Live in `scoring.py`.
- **Skill point schedule: 1 per character level + Season Journey rewards**,
  total cap 83 (user-confirmed). `points_at_level(level, season_journey)`
  returns `min(level, 70) + max(season_journey, 0)` clamped to 83. CLI flag
  `--season-journey N` controls how many journey points to assume; default 0.
  Source: `news.blizzard.com/en-us/article/24267729/prepare-for-the-reckoning-lord-of-hatred-draws-near`.
- **Skill bar cap:** 6.
- **Allocator:** pure greedy per-level, no backtracking. Adequate for
  scaffolding; will likely need beam search or local-search polish once
  resource costs and rotations matter.

## Data source policy

- Primary source for class data: **maxroll.gg** (specifically
  `https://maxroll.gg/d4/getting-started/warlock-class-overview`) and
  `d4builds.gg`.
- **Both sites currently return HTTP 403 to WebFetch (Cloudflare).** Do not
  attempt to bypass. Use WebSearch summaries when possible, otherwise ask the
  user to paste the data, or have them run a local scrape and commit the YAML.
- Every YAML entry that is not directly verified must carry `placeholder: true`
  and a `source_url` pointing at where the real data should come from. The
  optimizer report surfaces `[placeholder]` next to any name pulled from such
  an entry.

## Itemization model

Built to absorb the Lord of Hatred itemization changes including the
Horadric Cube. See `src/lohbuild/model/gear.py`.

- `Item.cube_imbue: CubeRecipe | None` — recipe imbued into an equipped item.
- `Loadout.cube_residents: list[CubeRecipe]` — recipes active because they
  sit in the cube (D3 Kanai's Cube–style hedge; flip the field to a single
  slot once the actual mechanic is documented).
- `CubeEffect.stats` is a flat StatBlock today. Extend to conditional
  triggers (on-hit, on-cooldown) when the recipe grammar is documented.

## Confirmed Lord of Hatred facts (from WebSearch snippets, 2026-04)

- Two resources: **Wrath** (offensive Hellfire / Abyss skills) and
  **Dominance** (summoning Greater Demons).
- Class mechanic: **Soul Shards** (pick 1 of 4 primary Shards + 1 of 3
  Fragments).
- Skill schools: **Hellfire** (interacts with *Volatility* — random empower
  for x50% next-cast damage) and **Abyss** (interacts with *Shadowform* —
  x30% damage and movespeed per stack).
- Status effects: **Hex** (+15% crit chance per stack, max 45%),
  **Eviscerate** (instant 20% of bleed life, plus 12s DoT).
- Skill categories shipped: Basic, Core, Defensive, Archfiend (summon), Sigil,
  Ultimate.
- **User-confirmed rules (2026-04-25):**
  - Every active skill has **max rank 15** (was 5). Modifier / variant nodes
    are *not* raised — they keep their pre-LoH caps. We do not model variant
    nodes yet.
  - **Total available skill points: 83.** Per-level schedule unknown;
    distributed linearly in `optimizer.points_at_level()` until datamined.
- **Passive nodes are removed from every class skill tree in LoH.** Passive
  power moved to Legendary Aspects, Uniques, and the new **Talisman + Charms**
  system (charms socket into a Talisman to grant passive effects). None of
  those three sources are modeled yet — the `Passive` model class still
  exists and can be reused for Talisman/Charms when the schema lands.
- **Per-skill modifier system (modeled):** each active skill exposes four
  modifier slots — `left`, `right`, `middle` (transformative variant), and
  `bonus` (build-defining unlock deeper in the tree). Each pick costs 1
  point, has no rank, and is mutually exclusive within its (skill, slot).
  Modifiers can require a minimum rank in the parent skill (`requires_rank`).
  Data lives under each skill's `modifiers:` block in `warlock.yaml`; the
  selection lives in `SkillAllocation.modifier_ids` and is applied via
  `Build.total_stats()`. Modifier *names and stats* are placeholders — only
  the structural rules are real.

## Skill names known (source: WebSearch snippets, not page-verified)

- Basic: Command Fallen, Doom, Hellion Sting, Molten Bomb
- Core: Blazing Scream, Bombardment, Dread Claws, Hell Fracture, Umbral Chains
- Defensive: Dark Prison, Nether Step, Tortured Wretch, Wall of Agony
- Archfiend: Infernal Breath, Profane Sentinel, Rampage, Tyrant's Grasp
- Sigil: Sigil of Chaos, Sigil of Subversion, Sigil of Summons
- Ultimate: Apocalypse, Fiend of Abaddon, Metamorphosis, Terror Swarm

Numbers I have from snippets (treat as best-effort, not page-verified):

- Hellion Sting: 66% weapon damage, 5% chance to apply Eviscerate (660% on
  proc).
- Hell Fracture: 180% damage, chains up to 2 additional explosions.
- Dread Claws: 4 claws × 65% damage each.

## Local commands

```bash
PYTHONPATH=src python3 -m lohbuild.cli warlock --level 70
PYTHONPATH=src python3 -m lohbuild.cli warlock --level 25
```

## Known calibration issues (track before adding features)

1. Composite score collapses at higher levels because the placeholder enemy
   life curve (`100 * 1.18^level` in `model/enemy.py`) outruns placeholder
   weapon scaling. Co-calibrate enemy and player curves once real numbers
   land.
2. Gear stats are flat — no item-power scaling. Add scaling when itemization
   data is available.
3. Skill bar at 70 includes everything because the optimizer has no rotation
   simulator. Add resource tracking + cooldown-phase rotation before trusting
   bar choices.
