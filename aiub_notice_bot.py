import requests
from bs4 import BeautifulSoup
import os
import sys
import time
import logging
from urllib.parse import urljoin

# Configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = "https://www.aiub.edu/category/notices"
TIMEOUT = 30  # seconds for HTTP requests
MAX_RETRIES = 3  # retry count for transient failures
RETRY_DELAY = 5  # seconds between retries
MAX_SAVED_NOTICES = 200  # cap state file to avoid unbounded growth

# Resolve paths relative to the script's directory so the bot works
# regardless of the working directory it is invoked from.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "last_notice.txt")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# Helpers
def escape_markdown_v2(text):
    """Escape all special characters required by Telegram MarkdownV2."""
    special = r"_*[]()~`>#+-=|{}.!\\"
    return "".join(f"\\{ch}" if ch in special else ch for ch in text)


def _request_with_retry(method, url, *, retries=MAX_RETRIES, **kwargs):
    """Perform an HTTP request with retries on transient failures."""
    kwargs.setdefault("timeout", TIMEOUT)
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            resp = method(url, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < retries:
                log.warning(
                    "Request to %s failed (attempt %d/%d): %s – retrying in %ds",
                    url, attempt, retries, exc, RETRY_DELAY,
                )
                time.sleep(RETRY_DELAY)
            else:
                log.error(
                    "Request to %s failed after %d attempts: %s",
                    url, retries, exc,
                )
    raise last_exc


# Telegram
def send_telegram_msg(message):
    """Send a message via Telegram Bot API. Returns True on success."""
    send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "MarkdownV2",
    }
    try:
        resp = _request_with_retry(requests.post, send_url, data=payload)
        return resp.ok
    except requests.RequestException:
        return False


# Scraping
def get_all_notices():
    """Scrape ALL notices from the AIUB notices page.

    Returns a list of (title, link) tuples.  Raises on network errors so the
    caller can decide how to handle them.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AIUBNoticeBot/1.0; "
            "+https://github.com)"
        )
    }
    resp = _request_with_retry(requests.get, URL, headers=headers)
    soup = BeautifulSoup(resp.content, "html.parser")

    notices = []
    for title_element in soup.select("h2.title"):
        title = title_element.get_text().strip()
        if not title:
            continue
        link_tag = title_element.find_parent("a")
        if link_tag and link_tag.get("href"):
            link = urljoin("https://www.aiub.edu", link_tag["href"])
        else:
            link = URL
        notices.append((title, link))

    return notices


# State Persistence
def load_saved_notices():
    """Load previously seen notice titles from file (one title per line)."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()
    except OSError as exc:
        log.warning("Could not read state file: %s – starting fresh", exc)
        return set()


def save_notices(titles):
    """Save notice titles to file (one per line), capped at MAX_SAVED_NOTICES."""
    # Keep only the most recent titles to prevent unbounded growth.
    capped = list(titles)[-MAX_SAVED_NOTICES:]
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            for title in capped:
                f.write(title + "\n")
    except OSError as exc:
        log.error("Could not write state file: %s", exc)


# Main
def main():
    # ---- pre-flight checks ------------------------------------------------
    if not BOT_TOKEN or not CHAT_ID:
        log.error(
            "BOT_TOKEN and CHAT_ID environment variables must be set. "
            "Aborting."
        )
        sys.exit(1)

    # ---- fetch notices ----------------------------------------------------
    saved_titles = load_saved_notices()

    try:
        notices = get_all_notices()
    except requests.RequestException as exc:
        log.error("Failed to fetch notices: %s", exc)
        sys.exit(1)

    if not notices:
        log.info("No notices found on page – the page structure may have changed.")
        return

    current_titles = [title for title, _ in notices]
    new_notices = [(t, l) for t, l in notices if t not in saved_titles]

    if not new_notices:
        log.info("No new notices.")
        return

    # ---- send notifications (oldest first) --------------------------------
    all_sent = True
    for title, link in reversed(new_notices):
        log.info("New notice: %s", title)
        safe_title = escape_markdown_v2(title)
        safe_link = escape_markdown_v2(link)
        msg = (
            "\U0001f6a8 *New AIUB Notice\\!*\n\n"
            f"_{safe_title}_\n\n"
            f"[Click to Read]({safe_link})"
        )
        if not send_telegram_msg(msg):
            log.error("Failed to send notification for: %s", title)
            all_sent = False

    # ---- persist state only when every message was delivered ---------------
    if all_sent:
        save_notices(set(current_titles) | saved_titles)
    else:
        log.warning(
            "Some messages failed to send – state NOT updated so they "
            "will be retried on the next run."
        )


if __name__ == "__main__":
    main()
