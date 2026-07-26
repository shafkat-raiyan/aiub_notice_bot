"""Gemini AI integration for the /ask command (RAG pattern).

How it works:
  1. Receive a question from the user
  2. Pass the scraped notices as context to Gemini
  3. Gemini answers strictly based on those notices
  4. Return the answer as a plain string
"""

import logging
import google.generativeai as genai
from bot.config import GEMINI_API_KEY

log = logging.getLogger(__name__)

_MODEL = "gemini-1.5-flash"  # free tier

_SYSTEM_PROMPT = (
    "You are a helpful assistant for AIUB (American International University-Bangladesh) students. "
    "Answer the student's question using ONLY the notices listed below. "
    "If the answer is not in the notices, say so clearly. "
    "Keep your answer short and direct. "
    "If relevant, mention the notice link."
)


def ask_about_notices(question, notices):
    """Ask Gemini a question grounded in the provided notices.

    Args:
        question: The student's question as a plain string.
        notices: List of (title, link, date) tuples from the scraper.

    Returns:
        Gemini's answer as a plain string.
    """
    if not GEMINI_API_KEY:
        return "AI feature is not configured. The developer needs to set GEMINI_API_KEY."

    # Build a numbered list of notices as context for Gemini
    context = "\n".join(
        f"{i}. {title}" + (f" | Date: {date}" if date else "") + f" | Link: {link}"
        for i, (title, link, date) in enumerate(notices, 1)
    )

    prompt = f"{_SYSTEM_PROMPT}\n\nNotices:\n{context}\n\nStudent question: {question}"

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(_MODEL)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as exc:
        log.error("Gemini API error: %s", exc)
        return f"Error: {exc}"
