"""Use GPT to auto-compose human-like emails from transcript context."""

from __future__ import annotations

import json
import logging

from src.ai.client import AIClient
from config.prompts import COMPOSE_EMAIL_SYSTEM

log = logging.getLogger(__name__)

TONE_DESCRIPTIONS = {
    "work": (
        "Professional but warm. Use 'Hi {name}' as greeting. "
        "Be clear and direct, sound like a real person. "
        "End with 'Thanks' or 'Best'."
    ),
    "personal": (
        "Casual and friendly. Use 'Hey {name}' as greeting. "
        "Conversational, relaxed. "
        "End with 'Cheers' or 'See you!'."
    ),
    "mixed": (
        "Semi-formal. Use 'Hi {name}' as greeting. "
        "Friendly but clear. "
        "End with 'Thanks!' or 'Cheers'."
    ),
}

# Few-shot examples per category — placed in the USER message for
# stronger instruction-following than system-prompt examples.
FEW_SHOT_EXAMPLES = {
    "personal": (
        "Example:\n"
        "Recipient: Alex\n"
        "<context>\n"
        "The user plans a family dinner at Helen's place at 5:30 PM today "
        "with Alex and families. They need to leave by 4:30 PM and will "
        "pick up Alex on the way.\n"
        "</context>\n"
        'Output: {{"subject": "Dinner at Helen\'s place — 5:30 PM today", '
        '"body": "Hey Alex,\\n\\nExcited about dinner today! I\'ll swing by '
        "your place and pick you up on the way to Helen's — we should be there "
        'by 5:30. Going to be a great time with the families!\\n\\nSee you soon"}}'
    ),
    "work": (
        "Example:\n"
        "Recipient: Sarah\n"
        "<context>\n"
        "The user discussed the dashboard project with Sarah. They will send "
        "mockups by Thursday. Sarah wants the mobile version prioritized.\n"
        "</context>\n"
        'Output: {{"subject": "Dashboard mockups — sharing by Thursday", '
        '"body": "Hi Sarah,\\n\\nJust confirming — I\'ll have the dashboard '
        "mockups ready by Thursday. Will prioritize the mobile version as "
        'discussed and ping you once they\'re up for review.\\n\\nThanks"}}'
    ),
    "mixed": (
        "Example:\n"
        "Recipient: Jordan\n"
        "<context>\n"
        "The user and Jordan discussed the quarterly report at office. "
        "They also plan to catch up over coffee this weekend with families.\n"
        "</context>\n"
        'Output: {{"subject": "Weekend coffee plan + quarterly report", '
        '"body": "Hi Jordan,\\n\\nLooking forward to coffee this weekend with '
        "the families! Also, I'll wrap up my section of the quarterly report "
        'by Friday so we\'re all set.\\n\\nCheers"}}'
    ),
}


async def compose_email(
    ai_client: AIClient,
    recipient_name: str,
    action_items: list[str],
    commitments: list[str],
    category: str,
    context: str | None = None,
) -> dict:
    """
    Auto-compose a human-like email using GPT from transcript context.

    No user message needed — the AI writes directly from the summary,
    action items, and commitments extracted from the voice note / text.

    Returns dict with 'subject' and 'body' keys.
    """
    tone_key = category if category in TONE_DESCRIPTIONS else "mixed"
    tone_desc = TONE_DESCRIPTIONS[tone_key].format(name=recipient_name)

    system_prompt = COMPOSE_EMAIL_SYSTEM.format(
        tone_description=tone_desc,
    )

    # ── Build user prompt with clear structure ──
    parts = []

    # 1. Few-shot example (matching category)
    example_key = tone_key if tone_key in FEW_SHOT_EXAMPLES else "mixed"
    parts.append(FEW_SHOT_EXAMPLES[example_key])
    parts.append("")

    # 2. Actual task
    parts.append("---")
    parts.append(f"Now write an email to: {recipient_name}")

    # 3. Context as clearly-labeled reference material
    if context:
        parts.append(f"\n<context>\n{context}\n</context>")

    # 4. Action items and commitments (if any)
    if action_items:
        parts.append("\nAction items:")
        for item in action_items:
            parts.append(f"  - {item}")

    if commitments:
        parts.append("\nCommitments:")
        for c in commitments:
            parts.append(f"  - {c}")

    if not context and not action_items and not commitments:
        parts.append("\nJust a quick, friendly check-in.")

    # 5. Final instruction — recipient-aware
    parts.append(
        f"\nWrite the email. Only include what matters to {recipient_name} "
        f"— skip your own logistics. Output JSON only."
    )

    user_prompt = "\n".join(parts)

    # Debug logging to trace what GPT receives
    log.debug("Email compose prompt for %s:\n%s", recipient_name, user_prompt)

    try:
        # AIClient uses synchronous OpenAI — no await
        response = ai_client._client.chat.completions.create(
            model=ai_client._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
        )
        raw = response.choices[0].message.content
        log.info("Email composed for %s: %s", recipient_name, raw)

        result = json.loads(raw)
        return {
            "subject": result.get("subject", f"Hey {recipient_name}"),
            "body": result.get("body", context or ""),
        }
    except Exception:
        log.exception("Failed to compose email via GPT, using fallback")
        fallback_body = context or "Wanted to touch base with you."
        return {
            "subject": f"Hey {recipient_name}",
            "body": fallback_body,
        }
