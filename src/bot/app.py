from __future__ import annotations

import logging

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config.settings import Settings
from src.bot.callbacks import handle_callback
from src.bot.handlers import (
    handle_audio,
    handle_cancel,
    handle_pending,
    handle_status,
    handle_text,
    handle_voice,
)

log = logging.getLogger(__name__)


def create_application(settings: Settings):
    """Build and configure the Telegram bot application."""
    app = ApplicationBuilder().token(settings.telegram_bot_token).build()

    # Security filter: only accept messages from allowed users
    if settings.telegram_allowed_user_ids:
        user_filter = filters.User(user_id=settings.telegram_allowed_user_ids)
    else:
        log.warning("No allowed user IDs configured - bot will accept messages from anyone!")
        user_filter = filters.ALL

    # Voice notes
    app.add_handler(
        MessageHandler(filters.VOICE & user_filter, handle_voice)
    )

    # Audio files (music/recordings sent as audio)
    app.add_handler(
        MessageHandler(filters.AUDIO & user_filter, handle_audio)
    )

    # Audio documents (.mp3, .wav, .m4a sent as files)
    app.add_handler(
        MessageHandler(filters.Document.AUDIO & user_filter, handle_audio)
    )

    # Text messages (not commands)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, handle_text)
    )

    # Commands
    app.add_handler(CommandHandler("status", handle_status))
    app.add_handler(CommandHandler("pending", handle_pending))
    app.add_handler(CommandHandler("cancel", handle_cancel))

    # Inline keyboard callbacks
    app.add_handler(CallbackQueryHandler(handle_callback))

    return app
