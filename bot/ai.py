"""OpenRouter AI integration for the /ask command (RAG pattern).

How it works:
  1. Receive a question from the user
  2. Pass the scraped notices as context to the LLM
  3. Try free models in order — if one fails, fall back to the next
  4. Return the answer as a plain string
"""

import logging
import requests
from bot.config import OPENROUTER_API_KEY

log = logging.getLogger(__name__)

_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free models ranked by quality — tries best first, falls back on failure
_FREE_MODELS = [
    "google/gemma-4-31b:free",
    "google/gemma-4-26b-a4b:free",
    "nvidia/nemotron-3-super:free",
    "nvidia/nemotron-3-ultra:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "poolside/laguna-m.1:free",
    "openai/gpt-oss-20b:free",
]

_SYSTEM_PROMPT = (
    "You are a helpful assistant for AIUB (American International University-Bangladesh) students. "
    "Answer the student's question using ONLY the notices listed below. "
    "If the answer is not in the notices, say so clearly. "
    "Keep your answer short and direct. "
    "If relevant, mention the notice link."
)


def _call_openrouter(model, messages):
    """Make a single API call to OpenRouter. Returns the response text or raises."""
    resp = requests.post(
        _API_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": model, "messages": messages},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def ask_about_notices(question, notices):
    """Ask the LLM a question grounded in the provided notices.

    Tries each free model in order. If one is rate-limited or down,
    falls back to the next automatically.
    """
    if not OPENROUTER_API_KEY:
        return "AI feature is not configured. The developer needs to set OPENROUTER_API_KEY."

    context = "\n".join(
        f"{i}. {title}" + (f" | Date: {date}" if date else "") + f" | Link: {link}"
        for i, (title, link, date) in enumerate(notices, 1)
    )

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"Notices:\n{context}\n\nQuestion: {question}"},
    ]

    for model in _FREE_MODELS:
        try:
            answer = _call_openrouter(model, messages)
            log.info("Got answer from %s", model)
            return answer
        except Exception as exc:
            log.warning("Model %s failed: %s — trying next", model, exc)
            continue

    return "All AI models are currently busy. Please try again in a minute."
