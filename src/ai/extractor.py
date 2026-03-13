from __future__ import annotations

import logging

from src.ai.client import AIClient
from src.ai.schemas import ProcessedMessage
from src.storage.repositories import ActionItemRepo, ConversationRepo

log = logging.getLogger(__name__)


class MessageExtractor:
    """Orchestrates AI extraction with DB context."""

    def __init__(
        self,
        ai_client: AIClient,
        conversation_repo: ConversationRepo,
        action_item_repo: ActionItemRepo,
    ):
        self._ai = ai_client
        self._conv_repo = conversation_repo
        self._item_repo = action_item_repo

    async def extract(
        self, transcript: str, source_type: str
    ) -> ProcessedMessage:
        recent = await self._conv_repo.get_recent(limit=5)
        pending = await self._item_repo.get_pending()

        log.info(
            "Extracting with context: %d recent convos, %d pending items",
            len(recent), len(pending),
        )

        return self._ai.process_message(
            transcript=transcript,
            source_type=source_type,
            recent_summaries=recent,
            pending_items=pending,
        )
