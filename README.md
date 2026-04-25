# Lohbuilds

Build optimizer for the Diablo 4 *Lord of Hatred* expansion.

**Status:** scaffolding. Skill, passive, and itemization data are placeholders
sourced from a future scrape of [d4builds.gg](https://d4builds.gg). They are
shaped to exercise the schema, not to recommend actual builds. Every placeholder
entry carries `placeholder: true` and (where applicable) a `source_url` pointing
at the eventual d4builds.gg page so it is obvious what needs to be filled in.

## Initial scope

- Class: **Warlock**
- Level range: **1-70** leveling, no required uniques or aspects
- Platform: Windows 11
- Composite score weighting (hard-coded for now): **0.6 * DPS + 0.4 * EHP**

## Itemization model

The gear schema is built to absorb the expansion's itemization changes,
including the Horadric Cube. Items are decomposed into:

- `base_item` (slot, item power, intrinsic mods)
- `affixes` (rolled and tempered)
- `sockets` (gems, runes, or cube-granted sockets)
- `masterwork` rank
- `cube_imbue` — an optional reference to a `CubeRecipe` whose effect is
  applied while the item is equipped (or while the recipe is slotted in the
  cube, depending on what the expansion actually ships)

`CubeRecipe`s live in their own data file so we can model crafting,
transmutation, and any "active in cube" passive effects without touching the
item model itself.

## Install / run

Requires Python 3.11+.

### Linux / macOS (current local dev environment)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
lohbuild warlock --level 70
lohbuild warlock --level 70 --season-journey 13   # full 83-point pool
```

Or without activating:

```bash
.venv/bin/lohbuild warlock --level 70
```

### Windows 11 (target deployment)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
lohbuild warlock --level 70
```

### Iterating on data

The package is installed in editable mode, so edits to `src/lohbuild/**`
(including `data/classes/warlock.yaml`) are picked up on the next CLI
invocation — no reinstall needed.

## Layout

```
src/lohbuild/
  cli.py              CLI entry point
  model/              dataclasses for skills, gear, builds, stats, enemies
  data/               YAML data files (placeholders today)
  scoring.py          DPS / EHP / composite score
  optimizer.py        greedy 1-70 leveling allocator
```
