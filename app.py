#!/usr/bin/env python3
"""
OpenClaw — Mac App Entry Point
Run this to launch the native Mac dashboard.
  python3 app.py
"""
import sys
import os

# Ensure .env is loaded before anything else
from dotenv import load_dotenv
load_dotenv()

import config

if not config.ANTHROPIC_API_KEY or config.ANTHROPIC_API_KEY == "your_anthropic_api_key_here":
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "OpenClaw Setup Required",
        "ANTHROPIC_API_KEY not found.\n\nOpen the .env file in your OpenClaw folder and add your Anthropic API key."
    )
    sys.exit(1)

from gui.dashboard import Dashboard, log
from agents.team import run_godfather


def on_run_task(task: str) -> str:
    log(f"Godfather received: {task}")
    result = run_godfather(task)
    return result


def on_stop():
    log("Colony paused.")


def main():
    log("OpenClaw Colony starting...")
    log(f"Model: {config.MODEL}")
    log(f"Monthly target: ${config.MONTHLY_GOAL:,}")
    log("Ready. Enter a task above to start.")

    app = Dashboard(on_run_task=on_run_task, on_stop=on_stop)
    app.mainloop()


if __name__ == "__main__":
    main()
