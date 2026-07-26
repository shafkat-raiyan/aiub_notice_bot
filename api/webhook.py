"""Vercel serverless entry point — handles incoming Telegram webhook requests.

Responds to Telegram immediately (200 OK) BEFORE processing commands, preventing
webhook retry storms during slow AI model responses.
"""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from bot.commands import process_update
from bot.notifier import register_commands

log = logging.getLogger(__name__)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Receive a Telegram update and route it to the correct command handler.

        Reads the request body, immediately responds 200 OK to Telegram,
        then processes the update in a background thread so Telegram never
        retries the webhook due to slow AI model responses.
        """
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        self._respond(b"OK")

        # Process in background thread so Telegram gets instant 200 OK
        try:
            data = json.loads(body)
            thread = threading.Thread(target=self._safe_process, args=(data,), daemon=True)
            thread.start()
            thread.join(timeout=55)  # Vercel max execution is 60s on Hobby; leave 5s headroom
        except Exception:
            log.exception("Failed to parse Telegram update")

    @staticmethod
    def _safe_process(data):
        try:
            process_update(data)
        except Exception:
            log.exception("Failed to process Telegram update")

    def do_GET(self):
        """Health check endpoint. Pass ?action=setup to register bot commands."""
        params = parse_qs(urlparse(self.path).query)
        if params.get("action") == ["setup"]:
            ok = register_commands()
            self._respond(b"Commands registered!" if ok else b"Failed to register commands.")
        else:
            self._respond(b"AIUB Notice Bot webhook is running.")

    def _respond(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body)
