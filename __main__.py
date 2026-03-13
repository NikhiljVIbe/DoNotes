"""DoNotes entry point: python __main__.py"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from src.ai.client import AIClient
from src.ai.extractor import MessageExtractor
from src.bot.app import create_application
from src.integrations.calendar import CalendarManager
from src.integrations.gmail import GmailSender
from src.integrations.google_auth import GoogleAuth
from src.integrations.sheets import SheetsManager
from src.storage.database import Database
from src.storage.repositories import (
    ActionItemRepo,
    CalendarEventRepo,
    ConversationRepo,
    PeopleRepo,
)
from src.transcription.pipeline import TranscriptionPipeline
from src.core.processor import MessageProcessor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("donotes")


async def main() -> None:
    log.info("Starting DoNotes...")

    # Validate critical settings
    if not settings.telegram_bot_token:
        log.error("DONOTES_TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)
    if not settings.openai_api_key:
        log.error("DONOTES_OPENAI_API_KEY not set")
        sys.exit(1)

    # Initialize database
    db = Database(settings.abs_database_path)
    await db.connect()
    log.info("Database connected: %s", settings.abs_database_path)

    # Initialize repositories
    conv_repo = ConversationRepo(db)
    item_repo = ActionItemRepo(db)
    event_repo = CalendarEventRepo(db)
    people_repo = PeopleRepo(db)

    # Initialize transcription (OpenAI Whisper API)
    transcription = TranscriptionPipeline(
        api_key=settings.openai_api_key,
        prompt=settings.whisper_prompt,
    )

    # Initialize AI
    ai_client = AIClient(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
    )
    extractor = MessageExtractor(ai_client, conv_repo, item_repo)

    # Initialize Google integrations
    google_auth = GoogleAuth(
        settings.abs_google_credentials_path,
        settings.abs_google_token_path,
    )
    gmail = GmailSender(
        google_auth=google_auth,
        sender_email=settings.gmail_sender_email,
        recipient_email=settings.gmail_recipient_email,
    )
    calendar = CalendarManager(google_auth=google_auth, settings=settings)
    sheets = SheetsManager(google_auth=google_auth, settings=settings)

    # Initialize processor
    processor = MessageProcessor(
        transcription=transcription,
        extractor=extractor,
        gmail=gmail,
        calendar=calendar,
        sheets=sheets,
        conv_repo=conv_repo,
        item_repo=item_repo,
        event_repo=event_repo,
        people_repo=people_repo,
    )

    # Build and run Telegram bot
    app = create_application(settings)

    # Inject dependencies into bot_data so handlers can access them
    app.bot_data["processor"] = processor
    app.bot_data["action_item_repo"] = item_repo
    app.bot_data["conversation_repo"] = conv_repo
    app.bot_data["sheets_manager"] = sheets
    app.bot_data["people_repo"] = people_repo
    app.bot_data["gmail"] = gmail
    app.bot_data["ai_client"] = ai_client

    # Write PID file for process detection by menu bar app / launchd
    pid_file = Path("data/donotes.pid")
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()))
    log.info("PID file written: %s (PID %d)", pid_file, os.getpid())

    log.info("DoNotes bot starting... Send a voice note or text to get started!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    # Keep running until interrupted
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down...")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await db.close()
        pid_file.unlink(missing_ok=True)
        log.info("DoNotes stopped.")


if __name__ == "__main__":
    asyncio.run(main())
