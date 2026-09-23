"""
Main entry point for autogenrec CLI.

Usage:
    python -m autogenrec --demo
    python -m autogenrec
    autogenrec --demo
    autogenrec
"""

import argparse
import sys
from typing import NoReturn


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="autogenrec",
        description="AutoGenRec: Recursive-Generative Organizational Body",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the full 10-subsystem research-to-revenue pipeline demo",
    )

    args, _unknown = parser.parse_known_args()

    if args.demo:
        from autogenrec.demo import run_demo

        run_demo()
        sys.exit(0)

    from autogenrec.runtime.__main__ import main as runtime_main

    runtime_main()


if __name__ == "__main__":
    main()
