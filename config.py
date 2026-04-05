import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

MODEL = os.getenv("OPENCLAW_MODEL", "claude-opus-4-6")
CWD = os.getenv("OPENCLAW_CWD", ".")
MAX_TURNS = int(os.getenv("OPENCLAW_MAX_TURNS", "20"))

MONTHLY_GOAL = 5000
SPAWN_THRESHOLD = 500     # weekly revenue to trigger team spawn
KILL_THRESHOLD = 50       # weekly revenue below which to kill a stream

DB_PATH = os.path.join(os.path.dirname(__file__), "colony.db")
