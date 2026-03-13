"""
Vocabulary for Whisper transcription hints and GPT extraction context.

Loads personalized data from config/user_profile.py (gitignored).
Falls back to empty defaults if user_profile.py doesn't exist.

Whisper prompt (~224 token limit): compact, high-priority terms only.
GPT system prompt (flexible): categorized, detailed context.
"""

import logging

log = logging.getLogger(__name__)

# ── Load from user profile (with fallbacks) ──────────────────────────

try:
    from config.user_profile import USER_NAME
except ImportError:
    USER_NAME = ""

try:
    from config.user_profile import KNOWN_PEOPLE
except ImportError:
    KNOWN_PEOPLE = []

try:
    from config.user_profile import WHISPER_PLACES
except ImportError:
    WHISPER_PLACES = []

try:
    from config.user_profile import WHISPER_COMPANIES
except ImportError:
    WHISPER_COMPANIES = []

try:
    from config.user_profile import WHISPER_NAMES
except ImportError:
    WHISPER_NAMES = []

try:
    from config.user_profile import GPT_PLACE_CONTEXT
except ImportError:
    GPT_PLACE_CONTEXT = {}

try:
    from config.user_profile import GPT_COMPANY_CONTEXT
except ImportError:
    GPT_COMPANY_CONTEXT = {}


# ── Builder functions ────────────────────────────────────────────────

def build_whisper_prompt() -> str:
    """
    Build a compact Whisper prompt that fits within ~224 tokens.

    Includes known people, top-priority places, companies,
    and common names as vocabulary hints.
    """
    parts = []

    if USER_NAME:
        parts.append(f"Conversation involving {USER_NAME}.")
    else:
        parts.append("Conversation transcript.")

    if KNOWN_PEOPLE:
        people_str = ", ".join(KNOWN_PEOPLE)
        parts.append(f"Speakers: {people_str}.")

    if WHISPER_PLACES:
        places_str = ", ".join(WHISPER_PLACES[:18])
        parts.append(f"Places: {places_str}.")

    if WHISPER_COMPANIES:
        companies_str = ", ".join(WHISPER_COMPANIES[:18])
        parts.append(f"Companies: {companies_str}.")

    if WHISPER_NAMES:
        names_str = ", ".join(WHISPER_NAMES[:12])
        parts.append(f"Names: {names_str}.")

    parts.append("When multiple speakers are present, note speaker transitions.")

    prompt = " ".join(parts)

    # Safety: rough token estimate (1 token ~ 4 chars for English)
    estimated_tokens = len(prompt) // 4
    if estimated_tokens > 200:
        log.warning(
            "Whisper prompt estimated at %d tokens (limit ~224). "
            "Consider trimming vocabulary lists.",
            estimated_tokens,
        )

    return prompt


def build_gpt_context_block() -> str:
    """Build the local context block for the GPT system prompt."""
    if not GPT_PLACE_CONTEXT and not GPT_COMPANY_CONTEXT:
        return ""

    lines = ["Local context (for identifying places, companies, and people in transcripts):"]

    if GPT_PLACE_CONTEXT:
        lines.append("Known places and venues:")
        for category, places in GPT_PLACE_CONTEXT.items():
            label = category.title()
            lines.append(f"  - {label}: {', '.join(places)}")

    if GPT_COMPANY_CONTEXT:
        lines.append("Known companies:")
        for category, companies in GPT_COMPANY_CONTEXT.items():
            label = category.title()
            lines.append(f"  - {label}: {', '.join(companies)}")

    lines.append(
        "Use these references to correctly identify place names, "
        "recognize company names, classify work vs personal context, "
        "and set accurate locations for calendar events."
    )

    return "\n".join(lines)
