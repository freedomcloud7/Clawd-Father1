#!/usr/bin/env python3
"""
OpenClaw Telegram Bot Controller
=================================
Run this to control your colony from your phone via Telegram.

  python3 telegram_bot.py

Send ANY message to your bot to run it as a colony task.
Special commands:
  /start   — welcome message
  /status  — show revenue status
  /help    — list commands
  /stop    — stop current task (note: tasks run in background)
"""
import asyncio
import json
import os
import sys
import threading
import time
from datetime import datetime

import aiohttp
from dotenv import load_dotenv, set_key

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "").strip()
ENV_FILE  = os.path.join(os.path.dirname(__file__), ".env")

if not BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not found in .env")
    print("Add it to your .env file:  TELEGRAM_BOT_TOKEN=your_token_here")
    sys.exit(1)

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ── Telegram API helpers ───────────────────────────────────────────────────────

async def tg_get(session: aiohttp.ClientSession, method: str, **params) -> dict:
    """Call a Telegram Bot API GET method."""
    try:
        async with session.get(f"{API}/{method}", params=params, timeout=aiohttp.ClientTimeout(total=30)) as r:
            return await r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def tg_post(session: aiohttp.ClientSession, method: str, **data) -> dict:
    """Call a Telegram Bot API POST method."""
    try:
        async with session.post(f"{API}/{method}", json=data, timeout=aiohttp.ClientTimeout(total=30)) as r:
            return await r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def send(session: aiohttp.ClientSession, chat_id: str | int, text: str, parse_mode: str = "HTML") -> None:
    """Send a message, splitting if over 4000 chars."""
    # Telegram max message length is 4096
    chunk_size = 4000
    for i in range(0, max(len(text), 1), chunk_size):
        chunk = text[i:i + chunk_size]
        await tg_post(session, "sendMessage",
                      chat_id=chat_id,
                      text=chunk,
                      parse_mode=parse_mode)
        if len(text) > chunk_size:
            await asyncio.sleep(0.3)


async def send_typing(session: aiohttp.ClientSession, chat_id: str | int) -> None:
    await tg_post(session, "sendChatAction", chat_id=chat_id, action="typing")

# ── Colony task runner (runs in thread to keep async loop free) ────────────────

def _run_colony_task(task: str) -> str:
    """Run the Godfather agent synchronously (called from thread pool)."""
    try:
        # Import here so startup is fast even if colony has issues
        from agents.team import run_godfather
        return run_godfather(task)
    except Exception as e:
        return f"Colony error: {e}"


def _get_status() -> str:
    """Get colony revenue status."""
    try:
        from colony.tracker import get_status_report
        return get_status_report()
    except Exception as e:
        return f"Status unavailable: {e}"

# ── Command handlers ───────────────────────────────────────────────────────────

HELP_TEXT = """<b>OpenClaw Colony Commands</b>

Just send any message and the colony will work on it.

<b>Commands:</b>
/start  — Welcome message
/status — Revenue status report
/help   — This message

<b>Examples:</b>
• <i>Find me 3 ways to make $500 this week</i>
• <i>Research AI tool niches with low competition</i>
• <i>What's the fastest path to $5,000/month?</i>
• <i>Scout for trending products on TikTok Shop</i>

The colony is always working. Send a goal and it will delegate to specialists, research opportunities, and report back."""

WELCOME_TEXT = """<b>OpenClaw Colony is online.</b>

Your autonomous money-making agents are ready.
Target: <b>$5,000/month</b> per team.

Send me a goal or task and I'll put the colony to work.
Type /help to see what I can do."""


async def handle_message(session: aiohttp.ClientSession, chat_id: int | str, text: str) -> None:
    """Route a message to the right handler."""
    text = text.strip()

    if text.startswith("/start"):
        await send(session, chat_id, WELCOME_TEXT)
        return

    if text.startswith("/help"):
        await send(session, chat_id, HELP_TEXT)
        return

    if text.startswith("/status"):
        await send(session, chat_id, "Checking colony status...")
        status = await asyncio.get_event_loop().run_in_executor(None, _get_status)
        await send(session, chat_id, f"<pre>{status}</pre>")
        return

    # Any other message → run as colony task
    await send(session, chat_id, f"Got it. Putting the colony to work on:\n<i>{text[:200]}</i>\n\nThis may take a minute...")

    # Keep sending typing indicator while task runs
    task_done = threading.Event()

    async def keep_typing():
        while not task_done.is_set():
            await send_typing(session, chat_id)
            await asyncio.sleep(4)

    typing_task = asyncio.create_task(keep_typing())

    try:
        result = await asyncio.get_event_loop().run_in_executor(None, _run_colony_task, text)
    finally:
        task_done.set()
        typing_task.cancel()

    if not result or not result.strip():
        result = "The colony finished but returned no output. Check your API key and try again."

    await send(session, chat_id, f"<b>Colony report:</b>\n\n{result}")

# ── Main polling loop ─────────────────────────────────────────────────────────

async def main():
    global CHAT_ID

    print("=" * 50)
    print("  OpenClaw Telegram Bot")
    print("=" * 50)

    async with aiohttp.ClientSession() as session:
        # Verify bot token
        me = await tg_get(session, "getMe")
        if not me.get("ok"):
            print(f"ERROR: Could not connect to Telegram. Check your BOT_TOKEN.")
            print(f"Detail: {me}")
            sys.exit(1)

        bot_name = me["result"].get("username", "your bot")
        print(f"Bot connected: @{bot_name}")

        if CHAT_ID:
            print(f"Chat ID loaded from .env: {CHAT_ID}")
            # Notify user the bot is back online
            try:
                await send(session, CHAT_ID, "OpenClaw Colony is back online. Send me a task.")
            except Exception:
                pass
        else:
            print("No CHAT_ID set. Waiting for first message to auto-detect...")
            print(f"Open Telegram, find @{bot_name}, and send /start")

        # Start polling
        offset = 0
        print("Listening for messages... (Ctrl+C to stop)\n")

        while True:
            try:
                updates = await tg_get(session, "getUpdates",
                                        offset=offset,
                                        timeout=20,
                                        allowed_updates="message")

                if not updates.get("ok"):
                    await asyncio.sleep(3)
                    continue

                for update in updates.get("result", []):
                    offset = update["update_id"] + 1

                    msg = update.get("message")
                    if not msg:
                        continue

                    incoming_chat_id = str(msg["chat"]["id"])
                    text = msg.get("text", "")
                    sender = msg["from"].get("first_name", "User")

                    if not text:
                        continue

                    # Auto-detect and save chat ID on first message
                    if not CHAT_ID:
                        CHAT_ID = incoming_chat_id
                        print(f"Auto-detected CHAT_ID: {CHAT_ID} (from {sender})")
                        # Save to .env so it persists
                        try:
                            set_key(ENV_FILE, "TELEGRAM_CHAT_ID", CHAT_ID)
                            print(f"Saved CHAT_ID to .env")
                        except Exception as e:
                            print(f"Could not save to .env: {e}")

                    # Only respond to the authorized chat
                    if incoming_chat_id != CHAT_ID:
                        await send(session, incoming_chat_id,
                                   "This bot is private. Unauthorized.")
                        continue

                    ts = datetime.now().strftime("%H:%M:%S")
                    print(f"[{ts}] {sender}: {text[:80]}")

                    # Handle in background so we don't block polling
                    asyncio.create_task(handle_message(session, CHAT_ID, text))

            except asyncio.CancelledError:
                break
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Polling error: {e}")
                await asyncio.sleep(3)

    print("\nBot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown.")
