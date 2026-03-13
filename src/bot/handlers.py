from __future__ import annotations

import logging
import os
import tempfile

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.callbacks import build_action_keyboard
from src.bot.formatters import format_processed_reply
from src.bot.email_flow import (
    is_email_flow_active,
    handle_email_text_input,
    start_email_suggestions,
    clear_flow,
)
from src.core.email_suggestions import build_email_suggestions
from src.core.processor import MessageProcessor

log = logging.getLogger(__name__)


async def _get_processor(context: ContextTypes.DEFAULT_TYPE) -> MessageProcessor:
    return context.bot_data["processor"]


async def _trigger_email_suggestions(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    processed,
) -> None:
    """Check for email-worthy recipients and start the suggestion flow."""
    if is_email_flow_active(context):
        return  # don't start a new flow while one is active
    suggestions = build_email_suggestions(processed)
    if suggestions:
        await start_email_suggestions(
            update, context, suggestions, processed.category.value
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice notes (single-speaker audio)."""
    msg = update.message
    await msg.reply_text("Processing voice note...")

    voice = msg.voice
    file = await context.bot.get_file(voice.file_id)
    tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
    await file.download_to_drive(tmp.name)

    try:
        processor = await _get_processor(context)
        processed, item_ids = await processor.process(
            audio_path=tmp.name,
            text=None,
            source_type="voice_memo",
            telegram_msg_id=msg.message_id,
        )
        reply = format_processed_reply(processed)
        keyboard = build_action_keyboard(item_ids)
        await msg.reply_text(reply, reply_markup=keyboard)

        # Suggest emailing relevant people
        await _trigger_email_suggestions(update, context, processed)
    except Exception:
        log.exception("Error processing voice note")
        await msg.reply_text("Sorry, something went wrong processing that voice note.")
    finally:
        os.unlink(tmp.name)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle audio files (forwarded recordings, call recordings)."""
    msg = update.message
    await msg.reply_text("Processing audio file...")

    audio = msg.audio or msg.document
    if audio is None:
        await msg.reply_text("Could not read the audio file.")
        return

    file = await context.bot.get_file(audio.file_id)
    suffix = ".ogg"
    if hasattr(audio, "file_name") and audio.file_name:
        _, ext = os.path.splitext(audio.file_name)
        if ext:
            suffix = ext

    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    await file.download_to_drive(tmp.name)

    try:
        processor = await _get_processor(context)
        processed, item_ids = await processor.process(
            audio_path=tmp.name,
            text=None,
            source_type="audio_file",
            telegram_msg_id=msg.message_id,
        )
        reply = format_processed_reply(processed)
        keyboard = build_action_keyboard(item_ids)
        await msg.reply_text(reply, reply_markup=keyboard)

        # Suggest emailing relevant people
        await _trigger_email_suggestions(update, context, processed)
    except Exception:
        log.exception("Error processing audio file")
        await msg.reply_text("Sorry, something went wrong processing that audio.")
    finally:
        os.unlink(tmp.name)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages (notes, quick thoughts)."""
    msg = update.message
    text = msg.text
    if not text:
        return

    # Check if we are in the middle of an email flow
    if is_email_flow_active(context):
        handled = await handle_email_text_input(update, context)
        if handled:
            return

    await msg.reply_text("Processing...")

    try:
        processor = await _get_processor(context)
        processed, item_ids = await processor.process(
            audio_path=None,
            text=text,
            source_type="text_note",
            telegram_msg_id=msg.message_id,
        )
        reply = format_processed_reply(processed)
        keyboard = build_action_keyboard(item_ids)
        await msg.reply_text(reply, reply_markup=keyboard)

        # Suggest emailing relevant people
        await _trigger_email_suggestions(update, context, processed)
    except Exception:
        log.exception("Error processing text message")
        await msg.reply_text("Sorry, something went wrong processing that message.")


async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command — abort the active email flow."""
    if is_email_flow_active(context):
        clear_flow(context)
        await update.message.reply_text("Email flow cancelled.")
    else:
        await update.message.reply_text("Nothing to cancel.")


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    repo = context.bot_data["action_item_repo"]
    pending = await repo.get_pending()
    count = len(pending)
    await update.message.reply_text(
        f"DoNotes is running.\n"
        f"Pending action items: {count}"
    )


async def handle_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /pending command - list pending action items."""
    repo = context.bot_data["action_item_repo"]
    items = await repo.get_pending()

    if not items:
        await update.message.reply_text("No pending action items!")
        return

    lines = ["*Pending Action Items:*\n"]
    for i, item in enumerate(items, 1):
        line = f"{i}. [{item['priority']}] {item['description']}"
        if item.get("deadline"):
            line += f"\n   Due: {item['deadline']}"
        lines.append(line)

    await update.message.reply_text("\n".join(lines))
