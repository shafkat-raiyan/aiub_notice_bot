"""Scrapes AIUB notice board and returns structured notice data."""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from bot.config import AIUB_URL, TIMEOUT

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AIUBNoticeBot/1.0; +https://github.com)"}


def get_notices(limit=None):
    """Fetch notices from the AIUB website.

    Args:
        limit: Max notices to return. None means return all.

    Returns:
        List of (title, link, date) tuples, newest first.

    Raises:
        requests.RequestException: On network or HTTP errors.
    """
    resp = requests.get(AIUB_URL, headers=_HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    notices = []
    for item in soup.select(".event-item, .notice-item, article"):
        title_el = item.select_one("h2.title")
        if not title_el:
            continue
        title = title_el.get_text().strip()
        if not title:
            continue
        link_tag = title_el.find_parent("a") or item.select_one("a[href]")
        link = urljoin(AIUB_URL, link_tag["href"]) if link_tag else AIUB_URL
        date_el = item.select_one(".date, time, .event-date")
        date = date_el.get_text().strip() if date_el else ""
        notices.append((title, link, date))
        if limit and len(notices) >= limit:
            return notices

    # Fallback: simpler selector if the structured approach yields nothing
    if not notices:
        for title_el in soup.select("h2.title"):
            title = title_el.get_text().strip()
            if not title:
                continue
            link_tag = title_el.find_parent("a")
            link = urljoin(AIUB_URL, link_tag["href"]) if link_tag else AIUB_URL
            notices.append((title, link, ""))
            if limit and len(notices) >= limit:
                return notices

    return notices
