"""Scrapes AIUB notice board and returns structured 4-field metadata records."""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from bot.config import AIUB_URL, TIMEOUT

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AIUBNoticeBot/2.0; +https://github.com)"}


def get_notices(limit=None):
    """Fetch structured notices from the AIUB website.

    Args:
        limit: Max notices to return. None means return all available on the page.

    Returns:
        List of (title, link, date, summary) tuples, newest first.

    Raises:
        requests.RequestException: On network or HTTP errors.
    """
    resp = requests.get(AIUB_URL, headers=_HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    notices = []
    
    # AIUB stores notice items inside <div class="notification"> blocks
    for item in soup.select("div.notification, .notice-item, article"):
        title_el = item.select_one("h2.title")
        if not title_el:
            continue
        title = " ".join(title_el.get_text().split())
        if not title:
            continue
            
        link_tag = item.select_one("a.info-link, a[href]") or title_el.find_parent("a")
        link = urljoin(AIUB_URL, link_tag["href"]) if link_tag and "href" in link_tag.attrs else AIUB_URL

        # AIUB timestamp selector (.date-custom)
        date_el = item.select_one(".date-custom, .date, time")
        date = " ".join(date_el.get_text().split()) if date_el else ""

        # AIUB description snippet selector (p.desc)
        desc_el = item.select_one("p.desc, .description")
        summary = " ".join(desc_el.get_text().split()) if desc_el else ""
        # Ignore boilerplate placeholder text
        if summary.lower() in ("please click here for more details", "click here for more details", ""):
            summary = ""

        notices.append((title, link, date, summary))
        if limit and len(notices) >= limit:
            return notices

    # Fallback: simpler title selector if structure changes in the future
    if not notices:
        for title_el in soup.select("h2.title"):
            title = " ".join(title_el.get_text().split())
            if not title:
                continue
            link_tag = title_el.find_parent("a")
            link = urljoin(AIUB_URL, link_tag["href"]) if link_tag else AIUB_URL
            notices.append((title, link, "", ""))
            if limit and len(notices) >= limit:
                return notices

    return notices
