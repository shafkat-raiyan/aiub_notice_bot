"""All Telegram API calls and message formatting."""

import time
import logging
import requests
from bot.config import BOT_TOKEN, CHAT_ID, MAX_RETRIES, RETRY_DELAY

log = logging.getLogger(__name__)


def _telegram_url(endpoint):
    return f"https://api.telegram.org/bot{BOT_TOKEN}/{endpoint}"


def escape_markdown_v2(text):
    """Escape special characters required by Telegram MarkdownV2."""
    special = r"_*[]()~`>#+-=|{}.!\\"
    return "".join(f"\\{ch}" if ch in special else ch for ch in text)


def send_message(chat_id, text, parse_mode="MarkdownV2", preview=False):
    """Send a message to any Telegram chat (used by command handlers)."""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": not preview,
    }
    requests.post(_telegram_url("sendMessage"), json=payload, timeout=10)


_bot_username = None


def get_bot_username():
    """Dynamically discover and cache the bot's username via Telegram's getMe API."""
    global _bot_username
    if _bot_username:
        return _bot_username
    try:
        resp = requests.get(_telegram_url("getMe"), timeout=5)
        if resp.ok:
            _bot_username = resp.json().get("result", {}).get("username")
    except Exception as exc:
        log.warning("Could not fetch bot username: %s", exc)
    return _bot_username or "r_aiub_notice_bot"


def send_alert(title, link, date, summary=""):
    """Send a new-notice alert to the configured CHAT_ID (used by the cron job).

    Retries up to MAX_RETRIES times on failure.
    Returns True if the message was sent successfully.
    """
    safe_title = escape_markdown_v2(title)
    date_str = f"\U0001f4c5 {escape_markdown_v2(date)}\n\n" if date else ""
    summary_str = f"\n\n💬 _{escape_markdown_v2(summary)}_" if summary else ""
    msg = (
        "\U0001f6a8 *New AIUB Notice\\!*\n\n"
        f"{date_str}"
        f"*{safe_title}*"
        f"{summary_str}"
    )

    bot_url = f"https://t.me/{get_bot_username()}"
    inline_keyboard = [
        [{"text": "\U0001f4d6 Read on AIUB Website", "url": link}],
        [{"text": "\U0001f916 Use AI Enabled Notice Bot", "url": bot_url}],
    ]
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "MarkdownV2",
        "reply_markup": {"inline_keyboard": inline_keyboard},
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(_telegram_url("sendMessage"), json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except requests.RequestException as exc:
            if attempt < MAX_RETRIES:
                log.warning("Send attempt %d/%d failed: %s – retrying in %ds", attempt, MAX_RETRIES, exc, RETRY_DELAY)
                time.sleep(RETRY_DELAY)
            else:
                log.error("Failed to send alert after %d attempts: %s", MAX_RETRIES, exc)
    return False


def register_commands():
    """Register bot commands so they appear in Telegram's command menu."""
    commands = [
        {"command": "notice",  "description": "Show latest 5 notices"},
        {"command": "latest",  "description": "Show the most recent notice"},
        {"command": "search",  "description": "Search notices by keyword"},
        {"command": "ask",     "description": "Ask AI a question about notices"},
        {"command": "devinfo", "description": "Developer information"},
        {"command": "help",    "description": "Show available commands"},
    ]
    resp = requests.post(_telegram_url("setMyCommands"), json={"commands": commands}, timeout=10)
    return resp.ok
