"""State and historical memory persistence using a structured JSON database."""

import json
import logging
from bot.config import DB_FILE, MAX_SAVED_NOTICES

log = logging.getLogger(__name__)


def load_notices_db():
    """Load historical notice records (title, link, date) from local disk database.

    Returns:
        List of (title, link, date) tuples, newest first.
    """
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [
                (item.get("title", ""), item.get("link", ""), item.get("date", ""))
                for item in data if item.get("title")
            ]
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        log.warning("Could not read database file: %s – starting fresh", exc)
        return []


def load_saved_titles():
    """Load previously seen notice titles as a set for O(1) deduplication during cron checks."""
    return {title for title, _, _ in load_notices_db()}


def save_notices_db(new_notices, existing_notices=None):
    """Merge newest scraped notices with existing database records and save to disk.

    Caps storage at MAX_SAVED_NOTICES to maintain peak Git & Vercel I/O efficiency.
    """
    if existing_notices is None:
        existing_notices = load_notices_db()

    merged = []
    seen_titles = set()

    # Process newer items first, followed by historical records
    for title, link, date in (new_notices + existing_notices):
        if title and title not in seen_titles:
            seen_titles.add(title)
            merged.append({"title": title, "link": link, "date": date})

    capped = merged[:MAX_SAVED_NOTICES]
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(capped, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        log.error("Could not write database file: %s", exc)
