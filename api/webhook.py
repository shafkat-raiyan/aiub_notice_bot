from http.server import BaseHTTPRequestHandler
import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BOT_TOKEN = os.environ.get("BOT_TOKEN")
AIUB_URL = "https://www.aiub.edu/category/notices"


def escape_markdown_v2(text):
    """Escape all special characters required by Telegram MarkdownV2."""
    special = r"_*[]()~`>#+-=|{}.!\\"
    return "".join(f"\\{ch}" if ch in special else ch for ch in text)


def get_notices(limit=10):
    """Scrape notices from AIUB website."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AIUBNoticeBot/1.0)"
    }
    resp = requests.get(AIUB_URL, headers=headers, timeout=30)
    resp.raise_for_status()
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
            link = AIUB_URL
        notices.append((title, link))
        if len(notices) >= limit:
            break

    return notices


def send_message(chat_id, text, parse_mode="MarkdownV2"):
    """Send a message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    requests.post(url, json=payload, timeout=10)


def handle_notice_command(chat_id):
    """Handle /notice command - show latest 5 notices."""
    try:
        notices = get_notices(limit=5)
        if not notices:
            send_message(chat_id, "No notices found\\.", "MarkdownV2")
            return

        lines = ["📋 *Latest AIUB Notices*\n"]
        for i, (title, link) in enumerate(notices, 1):
            safe_title = escape_markdown_v2(title)
            safe_link = escape_markdown_v2(link)
            lines.append(f"{i}\\. [{safe_title}]({safe_link})\n")

        send_message(chat_id, "\n".join(lines))
    except Exception as e:
        send_message(chat_id, f"Error fetching notices: {escape_markdown_v2(str(e))}")


def handle_latest_command(chat_id):
    """Handle /latest command - show the most recent notice."""
    try:
        notices = get_notices(limit=1)
        if not notices:
            send_message(chat_id, "No notices found\\.", "MarkdownV2")
            return

        title, link = notices[0]
        safe_title = escape_markdown_v2(title)
        safe_link = escape_markdown_v2(link)
        msg = f"🔔 *Latest Notice*\n\n_{safe_title}_\n\n[Click to Read]({safe_link})"
        send_message(chat_id, msg)
    except Exception as e:
        send_message(chat_id, f"Error: {escape_markdown_v2(str(e))}")


def handle_start_command(chat_id):
    """Handle /start command - show welcome message."""
    msg = (
        "👋 *Welcome to AIUB Notice Bot\\!*\n\n"
        "Available commands:\n"
        "/notice \\- Show latest 5 notices\n"
        "/latest \\- Show the most recent notice\n"
        "/help \\- Show this message"
    )
    send_message(chat_id, msg)


def process_update(body):
    """Process a Telegram update."""
    if not body or "message" not in body:
        return

    message = body["message"]
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return

    # Route commands
    if text == "/notice" or text.startswith("/notice@"):
        handle_notice_command(chat_id)
    elif text == "/latest" or text.startswith("/latest@"):
        handle_latest_command(chat_id)
    elif text in ("/start", "/help") or text.startswith(("/start@", "/help@")):
        handle_start_command(chat_id)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body)
            process_update(data)
        except:
            pass

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"AIUB Notice Bot Webhook is running")
