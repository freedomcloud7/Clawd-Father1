"""
Telegram notifier — sends colony updates to your Telegram bot.
"""
import aiohttp
import asyncio
import config


async def send_message(text: str) -> bool:
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return False

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                return resp.status == 200
    except Exception:
        return False


def notify(text: str) -> bool:
    """Sync wrapper for sending Telegram messages."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(send_message(text))
            return True
        else:
            return loop.run_until_complete(send_message(text))
    except Exception:
        return False


def notify_revenue(amount: float, stream: str, team_id: str = "team_001"):
    notify(
        f"💰 *Revenue Alert*\n"
        f"Team: {team_id}\n"
        f"Stream: {stream}\n"
        f"Amount: ${amount:,.2f}\n"
    )


def notify_spawn(team_id: str, strategy: str):
    notify(
        f"🚀 *New Team Spawned*\n"
        f"Team: {team_id}\n"
        f"Strategy: {strategy}\n"
    )


def notify_kill(team_id: str, stream: str, reason: str):
    notify(
        f"☠️ *Stream Killed*\n"
        f"Team: {team_id}\n"
        f"Stream: {stream}\n"
        f"Reason: {reason}\n"
    )


def notify_status(report: str):
    notify(f"📊 *Daily Report*\n```\n{report}\n```")
