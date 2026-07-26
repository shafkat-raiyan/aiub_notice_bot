"""GitHub Actions entry point — runs every 30 minutes via cron.

Flow:
  1. Load previously seen notice titles from disk
  2. Scrape the AIUB notice page
  3. Find notices we haven't sent yet
  4. Send Telegram alerts for each new notice (oldest first)
  5. Save updated state to disk only if all alerts were delivered
"""

import sys
import time
import logging
import requests
from bot.config import BOT_TOKEN, CHAT_ID
from bot.scraper import get_notices
from bot.state import load_saved_notices, save_notices
from bot.notifier import send_alert

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def main():
    if not BOT_TOKEN or not CHAT_ID:
        log.error("BOT_TOKEN and CHAT_ID environment variables must be set.")
        sys.exit(1)

    saved = load_saved_notices()

    try:
        notices = get_notices()
    except requests.RequestException as exc:
        log.error("Failed to fetch notices: %s", exc)
        sys.exit(1)

    if not notices:
        log.info("No notices found – the page structure may have changed.")
        return

    current_titles = [t for t, _, _ in notices]
    new_notices = [(t, l, d) for t, l, d in notices if t not in saved]

    if not new_notices:
        log.info("No new notices.")
        return

    # Send oldest first (reversed), with a small delay to respect Telegram rate limits
    all_sent = True
    for i, (title, link, date) in enumerate(reversed(new_notices)):
        log.info("Sending alert: %s", title)
        if not send_alert(title, link, date):
            log.error("Failed to send alert for: %s", title)
            all_sent = False
        elif i < len(new_notices) - 1:
            time.sleep(0.5)

    # Only update state when every message was delivered,
    # so failed ones are retried on the next run.
    if all_sent:
        save_notices(set(current_titles) | saved)
    else:
        log.warning("Some alerts failed – state not updated, will retry next run.")


if __name__ == "__main__":
    main()
