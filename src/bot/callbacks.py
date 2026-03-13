from __future__ import annotations

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.storage.repositories import ActionItemRepo
from src.bot.email_flow import handle_email_callback

log = logging.getLogger(__name__)


def build_action_keyboard(action_item_ids: list[str]) -> InlineKeyboardMarkup | None:
    """Build inline keyboard with Done/Ignore buttons for each action item."""
    if not action_item_ids:
        return None

    buttons = []
    for item_id in action_item_ids:
        buttons.append([
            InlineKeyboardButton("Done", callback_data=f"done:{item_id}"),
            InlineKeyboardButton("Ignore", callback_data=f"ignore:{item_id}"),
        ])
    return InlineKeyboardMarkup(buttons)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses."""
    query = update.callback_query

    # Check email flow callbacks first (email_yes, email_skip, etc.)
    data = query.data
    if data and data.startswith("email_"):
        handled = await handle_email_callback(update, context)
        if handled:
            return

    await query.answer()

    if not data or ":" not in data:
        return

    action, item_id = data.split(":", 1)
    repo: ActionItemRepo = context.bot_data["action_item_repo"]

    if action == "done":
        await repo.update_status(item_id, "done")
        _update_sheet_status(context, item_id, "done")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"Marked as done.")
        log.info("Action item %s marked as done", item_id)

    elif action == "ignore":
        await repo.update_status(item_id, "ignored")
        _update_sheet_status(context, item_id, "ignored")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"Item ignored.")
        log.info("Action item %s ignored", item_id)


def _update_sheet_status(
    context: ContextTypes.DEFAULT_TYPE, item_id: str, status: str
) -> None:
    """Propagate status change to the Google Sheets tracker."""
    sheets_mgr = context.bot_data.get("sheets_manager")
    if not sheets_mgr:
        return
    try:
        sheets_mgr.update_action_item_status(item_id, status)
    except Exception:
        log.exception("Failed to update sheet status for %s", item_id)
