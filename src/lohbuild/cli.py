from __future__ import annotations

import argparse
import sys

from .data import load_class, load_itemization
from .optimizer import optimize_leveling, report
from .presets import PRESETS, build_from_preset, report_preset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lohbuild",
        description="Diablo 4 Lord of Hatred build optimizer (placeholder data).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    leveling = sub.add_parser("warlock", help="Optimize a Warlock leveling build.")
    leveling.add_argument("--level", type=int, default=70, help="Target level (default 70).")
    leveling.add_argument(
        "--season-journey",
        type=int,
        default=0,
        help=(
            "Extra skill points earned from the Season Journey on top of the 1/level "
            "leveling pool (cap 70). Total is hard-capped at 83. Default 0."
        ),
    )
    leveling.add_argument(
        "--compare",
        metavar="PRESET",
        help=(
            "Compare optimizer output against a community preset. "
            f"Available: {', '.join(PRESETS)}."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "warlock":
        cls = load_class("warlock")
        items = load_itemization()
        result = optimize_leveling(
            cls,
            items,
            level_cap=args.level,
            season_journey=args.season_journey,
        )
        print(report(result, cls, season_journey=args.season_journey))

        if args.compare:
            preset = PRESETS.get(args.compare)
            if preset is None:
                print(
                    f"\nUnknown preset '{args.compare}'. "
                    f"Available: {', '.join(PRESETS)}.",
                    file=sys.stderr,
                )
                return 1
            print()
            print("=" * 60)
            print()
            preset_build = build_from_preset(
                preset, cls, items,
                level=args.level,
                season_journey=args.season_journey,
            )
            print(report_preset(preset, preset_build, cls))

        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
