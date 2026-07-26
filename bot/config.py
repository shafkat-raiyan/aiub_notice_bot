"""All configuration constants and environment variables in one place."""

import os

# --- Telegram ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# --- Gemini AI ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# --- Scraper ---
AIUB_URL = "https://www.aiub.edu/category/notices"
TIMEOUT = 30  # seconds

# --- Retry logic (for sending alerts) ---
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds between retries

# --- State file ---
MAX_SAVED_NOTICES = 200  # cap to prevent unbounded growth
# Resolve to repo root (one level above this bot/ package)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(_REPO_ROOT, "last_notice.txt")
