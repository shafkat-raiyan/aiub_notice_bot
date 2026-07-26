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
    "You are an expert academic assistant for AIUB (American International University-Bangladesh) students. "
    "Answer the student's question using ONLY the active campus catalog provided below (~60 latest announcements covering the last 1–2 months).\n\n"
    "CRITICAL CONVERSATIONAL GUARDRAILS:\n"
    "1. ZERO HALLUCINATIONS: You only hold catalog headlines, publication dates, summary previews, and URLs—not internal PDF body text. If a student asks for deep internal details (e.g., specific room numbers, tuition fee amounts, or individual seat plans), pinpoint the best matching notice and instruct them to click the link to view exact PDF documents.\n"
    "2. TEMPORAL & SCOPE AWARENESS: Your active memory pool spans the newest ~60 notices (~last 1–2 months of campus life). If a student inquires about historical events or rules from previous academic years (e.g., 1 or 2 years ago) or events outside this list, explain: 'My live memory spans our latest ~60 semester announcements (~1–2 months). For archival policies or notices from previous academic terms, please search the official university catalog at https://www.aiub.edu/category/notices!'\n"
    "3. NO SILENT REFUSALS: If a user inquires about upcoming midterms, routines, or holidays that aren't in your current list, NEVER simply reply 'No' or 'I don't know'. Offer helpful guidance: 'I couldn't find a headline matching that topic in our active semester records. Because exam dates and academic deadlines are mission-critical, please verify directly at https://www.aiub.edu/category/notices or try using `/search <keyword>`!'\n"
    "4. Keep your replies concise, friendly, professional, and directly actionable."
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

    context_lines = []
    for i, item in enumerate(notices, 1):
        title, link, date = item[:3]
        summary = item[3] if len(item) > 3 else ""
        line = f"{i}. {title}" + (f" | Date: {date}" if date else "") + (f" | Summary: {summary}" if summary else "") + f" | Link: {link}"
        context_lines.append(line)
    context = "\n".join(context_lines)

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
