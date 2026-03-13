from __future__ import annotations

import logging
import uuid
from datetime import datetime

from src.ai.extractor import MessageExtractor
from src.ai.schemas import ProcessedMessage
from src.integrations.calendar import CalendarManager
from src.integrations.gmail import GmailSender
from src.integrations.sheets import SheetsManager
from src.storage.models import ActionItemRecord, Conversation
from src.storage.repositories import (
    ActionItemRepo,
    CalendarEventRepo,
    ConversationRepo,
    PeopleRepo,
)
from src.transcription.pipeline import TranscriptionPipeline

log = logging.getLogger(__name__)


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


class MessageProcessor:
    """Main pipeline: message → transcribe → AI → store → email → calendar."""

    def __init__(
        self,
        transcription: TranscriptionPipeline,
        extractor: MessageExtractor,
        gmail: GmailSender,
        calendar: CalendarManager,
        sheets: SheetsManager,
        conv_repo: ConversationRepo,
        item_repo: ActionItemRepo,
        event_repo: CalendarEventRepo,
        people_repo: PeopleRepo,
    ):
        self._transcription = transcription
        self._extractor = extractor
        self._gmail = gmail
        self._calendar = calendar
        self._sheets = sheets
        self._conv_repo = conv_repo
        self._item_repo = item_repo
        self._event_repo = event_repo
        self._people_repo = people_repo

    async def process(
        self,
        audio_path: str | None,
        text: str | None,
        source_type: str,
        telegram_msg_id: int,
    ) -> tuple[ProcessedMessage, list[str]]:
        """
        Process a message end-to-end.
        Returns (ProcessedMessage, list of action_item_ids for inline keyboard).
        """
        # Step 1: Transcribe audio (if applicable)
        transcript = text or ""
        duration = 0.0
        if audio_path:
            transcript, duration = await self._transcription.process(audio_path)
            if not transcript:
                log.warning("Empty transcription for %s", audio_path)
                transcript = "(empty transcription)"

        log.info("Processing %s: %d chars", source_type, len(transcript))

        # Step 2: AI extraction
        processed = await self._extractor.extract(transcript, source_type)

        # Step 3: Store conversation
        conv_id = _new_id()
        conv = Conversation(
            id=conv_id,
            timestamp=datetime.now(),
            source_type=source_type,
            category=processed.category.value,
            transcript=transcript,
            summary=processed.summary,
            urgency_score=processed.urgency_score,
            speaker_count=1,
            audio_duration=duration if duration else None,
            telegram_msg_id=telegram_msg_id,
            key_topics=processed.key_topics,
        )
        await self._conv_repo.insert(conv)

        # Step 4: Store action items
        action_item_ids: list[str] = []
        for item in processed.action_items:
            item_id = _new_id()
            record = ActionItemRecord(
                id=item_id,
                conversation_id=conv_id,
                description=item.description,
                category=item.category.value,
                priority=item.priority.value,
                deadline=item.deadline,
                assigned_to=item.assigned_to,
            )
            await self._item_repo.insert(record)
            action_item_ids.append(item_id)

        # Step 5: Create calendar events
        calendar_links: list[str] = []
        for event in processed.calendar_events:
            try:
                event_id, event_link = self._calendar.create_event(event)
                if event_id:
                    await self._event_repo.insert(
                        conversation_id=conv_id,
                        google_event_id=event_id,
                        google_event_link=event_link,
                        title=event.title,
                        start_time=event.start_time,
                        end_time=event.end_time,
                        category=event.category.value,
                        calendar_id="",
                    )
                    if event_link:
                        calendar_links.append(event_link)
            except Exception:
                log.exception("Failed to create calendar event: %s", event.title)

        # Step 6: Store people mentions
        for person in processed.people_mentioned:
            try:
                person_id = await self._people_repo.upsert_person(
                    name=person.name,
                    role=person.role,
                    category=processed.category.value,
                )
                await self._people_repo.add_mention(
                    person_id=person_id,
                    conversation_id=conv_id,
                    context=person.context or processed.summary,
                )
            except Exception:
                log.exception("Failed to store person: %s", person.name)

        # Step 7: Send email digest
        try:
            self._gmail.send_digest(processed, transcript, calendar_links)
        except Exception:
            log.exception("Failed to send digest email")

        # Step 8: Update Google Sheets tracker
        try:
            self._sheets.append_processed_message(
                processed=processed,
                summary=processed.summary,
                source_type=source_type,
                action_item_ids=action_item_ids,
            )
        except Exception:
            log.exception("Failed to update Google Sheets tracker")

        log.info(
            "Processed %s: %d action items, %d events, %d people",
            source_type,
            len(processed.action_items),
            len(processed.calendar_events),
            len(processed.people_mentioned),
        )

        return processed, action_item_ids
