"""State persistence — tracks which notices have already been sent."""

import logging
from bot.config import STATE_FILE, MAX_SAVED_NOTICES

log = logging.getLogger(__name__)


def load_saved_notices():
    """Load previously seen notice titles from disk. Returns a set of titles."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()
    except OSError as exc:
        log.warning("Could not read state file: %s – starting fresh", exc)
        return set()


def save_notices(titles):
    """Save notice titles to disk, capped at MAX_SAVED_NOTICES."""
    capped = list(titles)[-MAX_SAVED_NOTICES:]
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(capped) + "\n")
    except OSError as exc:
        log.error("Could not write state file: %s", exc)
