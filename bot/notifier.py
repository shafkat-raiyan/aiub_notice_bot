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


def send_alert(title, link, date):
    """Send a new-notice alert to the configured CHAT_ID (used by the cron job).

    Retries up to MAX_RETRIES times on failure.
    Returns True if the message was sent successfully.
    """
    safe_title = escape_markdown_v2(title)
    safe_link = escape_markdown_v2(link)
    date_str = f"\U0001f4c5 {escape_markdown_v2(date)}\n\n" if date else ""
    msg = (
        "\U0001f6a8 *New AIUB Notice\\!*\n\n"
        f"{date_str}"
        f"_{safe_title}_\n\n"
        f"[Click to Read]({safe_link})"
    )
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "MarkdownV2"}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(_telegram_url("sendMessage"), data=payload, timeout=10)
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
