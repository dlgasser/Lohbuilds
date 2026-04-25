from __future__ import annotations

import argparse
import sys

from .data import load_class, load_itemization
from .optimizer import optimize_leveling, report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lohbuild",
        description="Diablo 4 Lord of Hatred build optimizer (placeholder data).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    leveling = sub.add_parser("warlock", help="Optimize a Warlock leveling build.")
    leveling.add_argument("--level", type=int, default=70, help="Target level (default 70).")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "warlock":
        cls = load_class("warlock")
        items = load_itemization()
        result = optimize_leveling(cls, items, level_cap=args.level)
        print(report(result, cls))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
