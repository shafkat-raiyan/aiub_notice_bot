"""Vercel serverless entry point — handles incoming Telegram webhook requests.

This file is intentionally thin: it only deals with HTTP.
All bot logic lives in bot/commands.py.
"""

import json
import logging
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from bot.commands import process_update
from bot.notifier import register_commands

log = logging.getLogger(__name__)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Receive a Telegram update and route it to the correct command handler."""
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            process_update(json.loads(body))
        except Exception:
            log.exception("Failed to process Telegram update")
        self._respond(b"OK")

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
