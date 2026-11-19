"""Command line entry: python -m loto build <yaml> [--out file]."""
from __future__ import annotations

import argparse
import sys

from .core import ProcedureError, load_procedure, render


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Exit code 0 on success, 2 on invalid input."""
    parser = argparse.ArgumentParser(prog="loto", description="Build a LOTO procedure sheet.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="render a Markdown sheet")
    b.add_argument("yaml")
    b.add_argument("--out", help="write to this file instead of printing")
    args = parser.parse_args(argv)
    try:
        sheet = render(load_procedure(args.yaml))
    except (ProcedureError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(sheet)
    else:
        print(sheet, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
