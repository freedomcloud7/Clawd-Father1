#!/usr/bin/env python3
"""
OpenClaw — Autonomous Money-Making Colony
==========================================
Usage:
  python3 main.py                    # interactive mode
  python3 main.py "find me revenue opportunities"
  python3 main.py --status           # show colony revenue status
"""
import sys
import argparse

import config
from agents.team import OpenClawTeam
from colony.tracker import get_status_report
from colony.telegram_notifier import notify_status


def parse_args():
    parser = argparse.ArgumentParser(
        prog="openclaw",
        description="OpenClaw: Autonomous Money-Making Colony"
    )
    parser.add_argument("task", nargs="?", help="Task to run")
    parser.add_argument("-i", "--interactive", action="store_true")
    parser.add_argument("--status", action="store_true", help="Show revenue status")
    return parser.parse_args()


def main():
    if not config.ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set in .env file")
        sys.exit(1)

    args = parse_args()

    if args.status:
        report = get_status_report()
        print(report)
        notify_status(report)
        return

    team = OpenClawTeam()

    if args.interactive or not args.task:
        team.run_interactive()
    else:
        result = team.run_task(args.task)
        if not result:
            sys.exit(1)


if __name__ == "__main__":
    main()
