"""
Multi-step email suggestion flow.

States:
  - None (no flow active): normal bot behavior
  - "suggest": bot has shown a suggestion, waiting for Yes/Skip
  - "confirm_email": bot found a saved email, waiting for Confirm/Change/Skip
  - "awaiting_email_input": bot asked user to type an email address
  - "composing": bot is auto-composing via GPT (transient)
  - "preview": bot showed composed email, waiting for Send/Recompose/Cancel

Transitions are driven by:
  - Callback queries (button presses) for suggest/confirm_email/preview steps
  - Text messages for awaiting_email_input step
"""

from __future__ import annotations

import logging
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.core.email_suggestions import EmailSuggestion
from src.ai.email_composer import compose_email

log = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


# ── Helpers ──────────────────────────────────────────────────────────


def is_email_flow_active(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if an email flow is currently active for this user."""
    return "email_flow" in context.user_data


def get_flow_step(context: ContextTypes.DEFAULT_TYPE) -> str | None:
    flow = context.user_data.get("email_flow")
    return flow["step"] if flow else None


def clear_flow(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("email_flow", None)


# ── Step 1: Start the flow after processing ─────────────────────────


async def start_email_suggestions(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    suggestions: list[EmailSuggestion],
    category: str,
) -> None:
    """
    Called from handlers.py after processing a message.
    Stores the suggestion queue and shows the first suggestion.
    """
    if not suggestions:
        return

    # Look up emails from contact book for all suggestions
    people_repo = context.bot_data["people_repo"]
    for suggestion in suggestions:
        person = await people_repo.find_person_by_name(suggestion.person_name)
        if person:
            suggestion.person_id = person["id"]
            suggestion.email = person.get("email")

    context.user_data["email_flow"] = {
        "step": "suggest",
        "queue": suggestions,
        "current_index": 0,
        "confirmed_email": None,
        "category": category,
        "composed": None,  # will hold {subject, body} after GPT composition
    }

    await _show_current_suggestion(update, context)


async def _show_current_suggestion(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Display the suggestion for the current person in the queue."""
    flow = context.user_data["email_flow"]
    idx = flow["current_index"]
    suggestion: EmailSuggestion = flow["queue"][idx]

    lines = [f"\U0001f4e7 Want to email *{suggestion.person_name}*?"]
    if suggestion.action_items:
        lines.append("\n*Action items:*")
        for item in suggestion.action_items:
            lines.append(f"  \u2022 {item}")
    if suggestion.commitments:
        lines.append("\n*Commitments:*")
        for c in suggestion.commitments:
            lines.append(f"  \u2022 {c}")
    if suggestion.context and not suggestion.action_items and not suggestion.commitments:
        lines.append(f"\n_{suggestion.context}_")

    text = "\n".join(lines)
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("\u2709\ufe0f Yes", callback_data="email_yes"),
            InlineKeyboardButton("Skip", callback_data="email_skip"),
        ]
    ])

    msg = update.effective_message or update.callback_query.message
    await msg.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
    flow["step"] = "suggest"


# ── Auto-compose helper ──────────────────────────────────────────────


async def _compose_and_preview(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Auto-compose an email via GPT and show preview with Send/Recompose/Cancel."""
    flow = context.user_data["email_flow"]
    suggestion = flow["queue"][flow["current_index"]]

    # Show composing indicator
    msg = update.callback_query.message if update.callback_query else update.effective_message
    composing_msg = await msg.reply_text("\u270d\ufe0f Composing email...")

    ai_client = context.bot_data["ai_client"]
    composed = await compose_email(
        ai_client=ai_client,
        recipient_name=suggestion.person_name,
        action_items=suggestion.action_items,
        commitments=suggestion.commitments,
        category=flow["category"],
        context=suggestion.context,
    )
    flow["composed"] = composed

    # Show preview
    preview = (
        f"\U0001f4e8 *Email Preview*\n\n"
        f"*To:* {flow['confirmed_email']}\n"
        f"*Subject:* {composed['subject']}\n\n"
        f"{composed['body']}"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("\u2709\ufe0f Send", callback_data="email_send"),
            InlineKeyboardButton("\U0001f504 Recompose", callback_data="email_recompose"),
            InlineKeyboardButton("Cancel", callback_data="email_cancel"),
        ]
    ])
    flow["step"] = "preview"

    # Delete the "Composing..." message and show the preview
    try:
        await composing_msg.delete()
    except Exception:
        pass  # non-critical if delete fails

    await msg.reply_text(preview, reply_markup=keyboard, parse_mode="Markdown")


# ── Step 2: Handle callback button presses ───────────────────────────


async def handle_email_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """
    Handle email-flow callback queries.
    Returns True if this callback was handled, False otherwise.
    """
    query = update.callback_query
    data = query.data

    if not data or not data.startswith("email_"):
        return False

    flow = context.user_data.get("email_flow")
    if not flow:
        return False

    await query.answer()
    step = flow["step"]
    suggestion = flow["queue"][flow["current_index"]]

    # ── Yes: user wants to email this person ──
    if data == "email_yes" and step == "suggest":
        if suggestion.email:
            flow["step"] = "confirm_email"
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Confirm", callback_data="email_confirm"),
                    InlineKeyboardButton("Change Email", callback_data="email_change"),
                    InlineKeyboardButton("Skip", callback_data="email_skip"),
                ]
            ])
            await query.message.reply_text(
                f"Send to *{suggestion.email}*?",
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
        else:
            flow["step"] = "awaiting_email_input"
            await query.message.reply_text(
                f"Enter {suggestion.person_name}'s email address:"
            )
        return True

    # ── Skip: move to next person ──
    if data == "email_skip":
        await _advance_to_next(update, context)
        return True

    # ── Confirm: user confirmed the saved email → auto-compose ──
    if data == "email_confirm" and step == "confirm_email":
        flow["confirmed_email"] = suggestion.email
        await _compose_and_preview(update, context)
        return True

    # ── Change Email: user wants to enter a different email ──
    if data == "email_change" and step == "confirm_email":
        flow["step"] = "awaiting_email_input"
        await query.message.reply_text(
            f"Enter {suggestion.person_name}'s email address:"
        )
        return True

    # ── Send: user approved the composed email ──
    if data == "email_send" and step == "preview":
        composed = flow["composed"]
        to_email = flow["confirmed_email"]
        gmail = context.bot_data["gmail"]

        try:
            gmail.send_composed_email(
                to_email=to_email,
                subject=composed["subject"],
                body_text=composed["body"],
                category=flow["category"],
            )
            await query.message.reply_text(
                f"\u2705 Email sent to {to_email}"
            )
        except Exception:
            log.exception("Failed to send email to %s", to_email)
            await query.message.reply_text(
                f"\u274c Failed to send email to {to_email}. Try again later."
            )

        await _advance_to_next(update, context)
        return True

    # ── Recompose: regenerate a fresh draft ──
    if data == "email_recompose" and step == "preview":
        flow["composed"] = None
        await _compose_and_preview(update, context)
        return True

    # ── Cancel: user cancels this email ──
    if data == "email_cancel" and step == "preview":
        await _advance_to_next(update, context)
        return True

    return False


# ── Step 3: Handle text input during email flow ─────────────────────


async def handle_email_text_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """
    Handle text input when email flow is in awaiting_email_input step.
    Returns True if handled, False if no active flow.
    """
    flow = context.user_data.get("email_flow")
    if not flow:
        return False

    step = flow["step"]
    text = update.message.text.strip()
    suggestion = flow["queue"][flow["current_index"]]

    if step == "awaiting_email_input":
        # Validate email format
        if not EMAIL_RE.match(text):
            await update.message.reply_text(
                "That doesn't look like a valid email. Please try again:"
            )
            return True

        # Save to contact book
        people_repo = context.bot_data["people_repo"]
        if suggestion.person_id:
            await people_repo.update_email(suggestion.person_id, text)
            log.info("Saved email %s for %s", text, suggestion.person_name)

        flow["confirmed_email"] = text
        suggestion.email = text

        # Auto-compose immediately after email is entered
        await _compose_and_preview(update, context)
        return True

    return False


# ── Flow control ─────────────────────────────────────────────────────


async def _advance_to_next(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Move to the next person in the queue, or end the flow."""
    flow = context.user_data.get("email_flow")
    if not flow:
        return

    flow["current_index"] += 1
    flow["confirmed_email"] = None
    flow["composed"] = None

    if flow["current_index"] < len(flow["queue"]):
        await _show_current_suggestion(update, context)
    else:
        clear_flow(context)
