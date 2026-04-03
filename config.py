import os
from dotenv import load_dotenv

load_dotenv()

# Model used by all agents
MODEL = os.getenv("OPENCLAW_MODEL", "claude-opus-4-6")

# Working directory for file operations
CWD = os.getenv("OPENCLAW_CWD", ".")

# Max turns per agent before stopping
MAX_TURNS = int(os.getenv("OPENCLAW_MAX_TURNS", "30"))

# Agent team name
TEAM_NAME = "OpenClaw"
