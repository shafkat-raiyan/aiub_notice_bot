"""Bot command handlers — one function per Telegram command.

Each handle_* function:
  - Receives a chat_id
  - Does its work (read JSON DB / query AI / etc.)
  - Sends a response via notifier.send_message()

process_update() is the router — it reads the incoming Telegram message
and calls the right handler.
"""

import logging
from bot.scraper import get_notices
from bot.state import load_notices_db
from bot.notifier import send_message, escape_markdown_v2
from bot.ai import ask_about_notices

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers & Zero-Cost Cache Reader
# ---------------------------------------------------------------------------

def get_cached_or_live_notices(limit=30, force_live=False):
    """Read historical notices straight from local git-backed JSON disk storage.

    If the database is empty or missing, falls back to a live web scrape.
    This eliminates third-party HTTP traffic on user interactions and prevents server rate-limit bans.
    """
    if not force_live:
        db_notices = load_notices_db()
        if db_notices:
            return db_notices[:limit] if limit else db_notices
    return get_notices(limit=limit)


def _send_error(chat_id, command):
    send_message(chat_id, f"Something went wrong with {escape_markdown_v2(command)}\\. Please try again later\\.")


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def handle_start(chat_id):
    msg = (
        "👋 *Welcome to AIUB Notice Bot\\!*\n\n"
        "/notice \\- Show latest 5 notices\n"
        "/latest \\- Show the most recent notice\n"
        "/search \\<keyword\\> \\- Search notices across historical database\n"
        "/ask \\<question\\> \\- Ask AI about campus announcements\n"
        "/devinfo \\- Developer information\n"
        "/help \\- Show this message"
    )
    send_message(chat_id, msg)


def handle_notice(chat_id):
    try:
        notices = get_cached_or_live_notices(limit=5)
        if not notices:
            send_message(chat_id, "No notices found\\.")
            return
        lines = ["📋 *Latest AIUB Notices*\n"]
        for i, (title, link, date) in enumerate(notices, 1):
            date_str = f" \\({escape_markdown_v2(date)}\\)" if date else ""
            lines.append(f"{i}\\. [{escape_markdown_v2(title)}]({escape_markdown_v2(link)}){date_str}\n")
        send_message(chat_id, "\n".join(lines))
    except Exception:
        log.exception("Error in /notice")
        _send_error(chat_id, "/notice")


def handle_latest(chat_id):
    try:
        notices = get_cached_or_live_notices(limit=1)
        if not notices:
            send_message(chat_id, "No notices found\\.")
            return
        title, link, date = notices[0]
        date_str = f"📅 {escape_markdown_v2(date)}\n\n" if date else ""
        msg = f"🔔 *Latest Notice*\n\n{date_str}_{escape_markdown_v2(title)}_\n\n[Click to Read]({escape_markdown_v2(link)})"
        send_message(chat_id, msg, preview=True)
    except Exception:
        log.exception("Error in /latest")
        _send_error(chat_id, "/latest")


def handle_search(chat_id, query):
    if not query:
        send_message(chat_id, "Usage: /search \\<keyword\\>\nExample: /search exam")
        return
    try:
        # Search across ALL historical records in notices_db.json!
        notices = get_cached_or_live_notices(limit=None)
        matches = [(t, l, d) for t, l, d in notices if query.lower() in t.lower()]
        if not matches:
            send_message(chat_id, f"No notices found for *{escape_markdown_v2(query)}* in our historical database\\.")
            return
        lines = [f"🔍 *Results for \"{escape_markdown_v2(query)}\"*\n"]
        for i, (title, link, date) in enumerate(matches[:5], 1):
            date_str = f" \\({escape_markdown_v2(date)}\\)" if date else ""
            lines.append(f"{i}\\. [{escape_markdown_v2(title)}]({escape_markdown_v2(link)}){date_str}\n")
        if len(matches) > 5:
            lines.append(f"\n_\\+{len(matches) - 5} more historical matches found_")
        send_message(chat_id, "\n".join(lines))
    except Exception:
        log.exception("Error in /search")
        _send_error(chat_id, "/search")


def handle_ask(chat_id, question):
    """RAG-based Q&A: read up to 60 historical database records → feed to LLM → answer instantly with zero server load."""
    if not question:
        send_message(chat_id, "Usage: /ask \\<question\\>\nExample: /ask when is the next exam\\?")
        return
    try:
        send_message(chat_id, "🤔 Thinking\\.\\.\\.")
        notices = get_cached_or_live_notices(limit=60)
        answer = ask_about_notices(question, notices)
        send_message(chat_id, f"🤖 {escape_markdown_v2(answer)}")
    except Exception:
        log.exception("Error in /ask")
        _send_error(chat_id, "/ask")


def handle_devinfo(chat_id):
    msg = (
        "👨‍💻 *Developer Information*\n\n"
        "*Name:* Syed Shafkat Raiyan\n\n"
        "🔗 *Connect with me:*\n"
        "[GitHub](https://github.com/shafkat\\-raiyan)\n"
        "[LinkedIn](https://www.linkedin.com/in/shafkat\\-raiyan)"
    )
    send_message(chat_id, msg)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def process_update(body):
    """Parse a Telegram update and route it to the correct command handler."""
    if not body or "message" not in body:
        return

    message = body["message"]
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return

    # Normalize: strip "@BotName" suffix and lowercase for comparison
    cmd = text.split()[0].lower().split("@")[0]
    # Extract everything after the command as the argument
    arg = text.split(maxsplit=1)[1] if " " in text else ""

    if cmd in ("/start", "/help"):
        handle_start(chat_id)
    elif cmd == "/notice":
        handle_notice(chat_id)
    elif cmd == "/latest":
        handle_latest(chat_id)
    elif cmd == "/search":
        handle_search(chat_id, arg)
    elif cmd == "/ask":
        handle_ask(chat_id, arg)
    elif cmd == "/devinfo":
        handle_devinfo(chat_id)
