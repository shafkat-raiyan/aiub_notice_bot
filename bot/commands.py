"""Bot command handlers — one function per Telegram command.

Each handle_* function:
  - Receives a chat_id and optional argument
  - Does its work (read 4-field JSON DB / query AI / etc.)
  - Sends a response via notifier.send_message()

process_update() is the router — it reads the incoming Telegram message,
manages two-step conversational state prompts, and calls the right handler.
"""

import logging
from bot.scraper import get_notices
from bot.state import load_notices_db
from bot.notifier import send_message, escape_markdown_v2
from bot.ai import ask_about_notices

log = logging.getLogger(__name__)

# In-memory conversational state tracking for mobile two-step menu button commands
_USER_STATES = {}


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
        "/help \\- Show this message\n\n"
        "ℹ️ *Database & Memory Coverage:*\n"
        "• 🤖 `/ask` analyzes our newest ~60 notices \\(~last 1–2 months\\)\\.\n"
        "• 🔍 `/search` checks across our stored database of ~200 notices \\(current semester\\)\\.\n"
        "• 🏛️ For archival notices over 6 months old, please visit aiub\\.edu directly\\."
    )
    send_message(chat_id, msg)


def handle_notice(chat_id):
    try:
        notices = get_cached_or_live_notices(limit=5)
        if not notices:
            send_message(chat_id, "No notices found\\.")
            return
        lines = ["📋 *Latest AIUB Notices*\n"]
        for i, item in enumerate(notices, 1):
            title, link, date = item[:3]
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
        item = notices[0]
        title, link, date = item[:3]
        summary = item[3] if len(item) > 3 else ""
        
        date_str = f"📅 {escape_markdown_v2(date)}\n\n" if date else ""
        summary_str = f"\n\n💬 _{escape_markdown_v2(summary)}_" if summary else ""
        msg = f"🔔 *Latest Notice*\n\n{date_str}*{escape_markdown_v2(title)}*{summary_str}\n\n[Click to Read]({escape_markdown_v2(link)})"
        send_message(chat_id, msg, preview=True)
    except Exception:
        log.exception("Error in /latest")
        _send_error(chat_id, "/latest")


def handle_search(chat_id, query):
    try:
        # Search across ALL historical records in notices_db.json!
        notices = get_cached_or_live_notices(limit=None)
        matches = [item for item in notices if query.lower() in item[0].lower() or (len(item) > 3 and query.lower() in item[3].lower())]
        if not matches:
            msg = (
                f"No matches found for *{escape_markdown_v2(query)}* in our active semester database \\(latest 200 announcements\\)\\.\n\n"
                "ℹ️ _For archival notices from previous academic years \\(1–2 years ago\\), please search directly at [aiub\\.edu/category/notices](https://www.aiub.edu/category/notices)\\._"
            )
            send_message(chat_id, msg)
            return
        lines = [f"🔍 *Results for \"{escape_markdown_v2(query)}\"*\n"]
        for i, item in enumerate(matches[:5], 1):
            title, link, date = item[:3]
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
# Router & Two-Step State Machine
# ---------------------------------------------------------------------------

def process_update(body):
    """Parse a Telegram update, manage interactive prompt states, and route to command handlers."""
    if not body or "message" not in body:
        return

    message = body["message"]
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return

    # Check if the user is triggering a command starting with "/"
    if text.startswith("/"):
        cmd = text.split()[0].lower().split("@")[0]
        arg = text.split(maxsplit=1)[1] if " " in text else ""
        
        # Clear any existing conversational prompt state when a new command is invoked
        _USER_STATES.pop(chat_id, None)

        if cmd in ("/start", "/help"):
            handle_start(chat_id)
        elif cmd == "/notice":
            handle_notice(chat_id)
        elif cmd == "/latest":
            handle_latest(chat_id)
        elif cmd == "/search":
            if not arg:
                _USER_STATES[chat_id] = "search"
                msg = (
                    "🔍 *What keyword would you like to search for?*\n\n"
                    "ℹ️ _Note: Search scans our active semester database \\(~200 announcements covering the last 4–6 months\\)\\. "
                    "For archival records older than 6 months, please visit aiub\\.edu directly\\._\n\n"
                    "👉 *Type your search keyword below:*"
                )
                send_message(chat_id, msg)
            else:
                handle_search(chat_id, arg)
        elif cmd == "/ask":
            if not arg:
                _USER_STATES[chat_id] = "ask"
                msg = (
                    "🤖 *What would you like to ask about AIUB notices?*\n\n"
                    "ℹ️ _Note: My AI awareness covers our newest ~60 announcements \\(~last 1–2 months of campus events\\)\\. "
                    "For policies from previous academic years, please check aiub\\.edu directly\\._\n\n"
                    "👉 *Type your question below:*"
                )
                send_message(chat_id, msg)
            else:
                handle_ask(chat_id, arg)
        elif cmd == "/devinfo":
            handle_devinfo(chat_id)
    else:
        # Plain text input without "/" prefix: check if user is replying to our interactive prompt!
        state = _USER_STATES.pop(chat_id, None)
        if state == "ask":
            handle_ask(chat_id, text)
        elif state == "search":
            handle_search(chat_id, text)
        else:
            # Helpful guidance if text is sent outside of an active prompt
            send_message(chat_id, "Please tap a command from the menu button or type /help to explore available tools\\!")
