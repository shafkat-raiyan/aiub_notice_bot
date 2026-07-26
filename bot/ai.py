"""OpenRouter AI integration for the /ask command (Hybrid Smart-RAG Pattern).

How it works:
  1. Receive a question from the user
  2. Check in-memory answer deduplication cache (shields free tier from simultaneous traffic bursts)
  3. Pre-filter 200-item historical database down to ~35 high-signal notices (~85% token reduction)
  4. Try high-speed free flash models in order with 10s timeouts for ultra-fast failover
  5. Sanitize and cache the answer as clean conversational prose for Telegram rendering
"""

import time
import re
import logging
import requests
from bot.config import OPENROUTER_API_KEY

log = logging.getLogger(__name__)

_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# In-memory answer deduplication cache to eliminate OpenRouter API load on viral repeat queries
_ANSWER_CACHE = {}  # format: {normalized_question: (timestamp, answer)}
_CACHE_TTL_SECONDS = 600  # 10 minutes time-to-live

# Free models ranked by responsiveness and instruction quality — fast flash/instruction models first!
_FREE_MODELS = [
    "google/gemini-2.5-flash:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-4-26b-a4b:free",
    "nvidia/nemotron-3-super:free",
    "openai/gpt-oss-20b:free",
]

# Static module-level set of common stop words to optimize keyword matching runtime
_STOP_WORDS = {
    "is", "the", "when", "what", "where", "how", "who", "why", "can", "will", "would", "should",
    "could", "do", "does", "did", "are", "was", "were", "of", "in", "and", "on", "to", "by",
    "with", "from", "at", "as", "for", "about", "any", "all", "some", "my", "our", "your",
    "notice", "notices", "aiub", "university", "please", "tell", "me", "know", "out", "published"
}

_SYSTEM_PROMPT = (
    "You are an expert academic assistant for AIUB (American International University-Bangladesh) students. "
    "Answer the student's question using ONLY the active campus catalog provided below (~200 historical announcements covering the full current academic semester, ~last 4 to 6 months).\n\n"
    "CRITICAL CONVERSATIONAL GUARDRAILS:\n"
    "1. ZERO HALLUCINATIONS: You only hold catalog headlines, publication dates, summary previews, and URLs—not internal PDF body text. If a student asks for deep internal details (e.g., specific room numbers, tuition fee amounts, or individual seat plans), pinpoint the best matching notice and instruct them to click the link to view exact PDF documents.\n"
    "2. TEMPORAL & SCOPE AWARENESS: Your active memory pool spans our newest ~200 notices (the current academic term, ~last 4 to 6 months). If a student inquires about historical events or rules from previous academic years (e.g., 1 or 2 years ago) or events outside this list, explain: 'My live memory covers our latest ~200 semester announcements (~4 to 6 months). For archival policies from previous academic years, please search the official university catalog at https://www.aiub.edu/category/notices!'\n"
    "3. NO SILENT REFUSALS: If a user inquires about upcoming midterms, routines, or holidays that aren't in your current list, NEVER simply reply 'No' or 'I don't know'. Offer helpful guidance: 'I couldn't find a headline matching that topic in our active semester records. Because exam dates and academic deadlines are mission-critical, please verify directly at https://www.aiub.edu/category/notices or try using `/search <keyword>`!'\n"
    "4. STRICT CHAT FORMATTING: Do NOT generate Markdown tables, ASCII grids, horizontal dividers, or double asterisks (`**bold**`). Write your response in warm, natural conversational paragraphs or simple bullet points so it renders cleanly on mobile chat screens. Keep your replies clear, helpful, and concise.\n"
    "5. PRIORITIZE CURRENT SEMESTER: When a student inquires about exam sets, routines, or announcements without naming a specific term, ALWAYS assume they mean the currently active semester (the most recent notices in the catalog). Do NOT volunteer information about past terms (such as previous Spring, Fall, or Summer semesters) unless explicitly requested."
)


def _filter_relevant_notices(question, notices, max_items=35):
    """Pre-filter up to 200 database records down to ~35 high-signal items to protect Free-Tier TPM limits.

    Combines top keyword matches across historical records with newest baseline notices,
    reducing token bandwidth by ~85% while preserving full-semester search reach.
    """
    if len(notices) <= max_items:
        return notices

    query_words = set(re.findall(r"\w+", question.lower())) - _STOP_WORDS

    # If no significant domain keywords remain (e.g., general "what is new?"), serve newest 35 items
    if not query_words:
        return notices[:max_items]

    # Score each record by keyword hits in title + summary
    scored = []
    for idx, item in enumerate(notices):
        title = item[0]
        summary = item[3] if len(item) > 3 else ""
        text = f"{title} {summary}".lower()
        score = sum(1 for w in query_words if w in text)
        scored.append((score, -idx, item))  # Prefer higher score; tie-break by newer notice (-idx)

    # Select top 20 most keyword-relevant records across the full semester history
    scored.sort(reverse=True)
    top_relevant = [item for score, _, item in scored[:20] if score > 0]

    # Always combine with newest 15 notices for real-time baseline awareness
    newest_baseline = notices[:15]

    # Merge and deduplicate while preserving accurate chronological sequence (newest first)
    seen_titles = set()
    final_list = []
    for item in (newest_baseline + top_relevant):
        if item[0] not in seen_titles:
            seen_titles.add(item[0])
            final_list.append(item)

    return final_list[:max_items]


def _call_openrouter(model, messages):
    """Make a single API call to OpenRouter. Returns the response text or raises."""
    resp = requests.post(
        _API_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": model, "messages": messages},
        timeout=10,  # Strict 10s timeout ensures rapid failover to fast alternative models during queue delays
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def ask_about_notices(question, notices):
    """Ask the LLM a question grounded in the provided notices with defensive caching and RAG filtering.

    Tries high-speed free models in order. If one is queued, rate-limited, or down, falls back to the next automatically.
    """
    if not OPENROUTER_API_KEY:
        return "AI feature is not configured. The developer needs to set OPENROUTER_API_KEY."

    # 1. Check answer deduplication cache to shield free tiers from simultaneous traffic spikes
    norm_q = " ".join(re.findall(r"\w+", question.lower()))
    now = time.time()
    if norm_q in _ANSWER_CACHE:
        ts, cached_ans = _ANSWER_CACHE[norm_q]
        if now - ts < _CACHE_TTL_SECONDS:
            log.info("Serving instant cached AI response for: %s", norm_q)
            return cached_ans

    # 2. Pre-filter notices to reduce token payload by 85%
    filtered_notices = _filter_relevant_notices(question, notices, max_items=35)

    context_lines = []
    for i, item in enumerate(filtered_notices, 1):
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
            raw_answer = _call_openrouter(model, messages)
            log.info("Got answer from %s", model)
            
            # Sanitize response text so Telegram's escape_markdown_v2 renders clean prose without raw asterisks
            clean_answer = raw_answer.replace("**", "").replace("### ", "").strip()
            
            # 3. Store verified clean answer in TTL cache before returning
            _ANSWER_CACHE[norm_q] = (now, clean_answer)
            return clean_answer
        except Exception as exc:
            log.warning("Model %s failed or timed out (%s) — switching to next fast model", model, exc)
            continue

    return "All AI models are currently busy due to high campus traffic. Please try again in a couple of minutes."
