#!/usr/bin/env python3
"""
OpenClaw — Autonomous Claude Agent Team
========================================
Usage:
  python main.py                         # interactive mode
  python main.py "Your task here"        # single task
  python main.py -i                      # force interactive mode
"""
import argparse
import sys
import anyio

from agents.team import OpenClawTeam
import config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="openclaw",
        description="OpenClaw: Autonomous Claude Agent Team",
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="Task to run (omit for interactive mode)",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in interactive REPL mode",
    )
    parser.add_argument(
        "--cwd",
        default=config.CWD,
        help=f"Working directory for file operations (default: {config.CWD})",
    )
    parser.add_argument(
        "--model",
        default=config.MODEL,
        help=f"Claude model to use (default: {config.MODEL})",
    )
    return parser.parse_args()


async def run(args: argparse.Namespace) -> None:
    team = OpenClawTeam(cwd=args.cwd, model=args.model)

    if args.interactive or not args.task:
        await team.run_interactive()
    else:
        result = await team.run_task(args.task)
        if not result:
            sys.exit(1)


def main() -> None:
    args = parse_args()
    try:
        anyio.run(run, args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)


if __name__ == "__main__":
    main()
