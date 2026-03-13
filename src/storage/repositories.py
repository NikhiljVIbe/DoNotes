from __future__ import annotations

import json
import uuid
from datetime import datetime

from src.storage.database import Database
from src.storage.models import ActionItemRecord, Conversation


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


def _now_iso() -> str:
    return datetime.now().isoformat()


class ConversationRepo:
    def __init__(self, db: Database):
        self._db = db

    async def insert(self, conv: Conversation) -> str:
        await self._db.conn.execute(
            """INSERT INTO conversations
               (id, timestamp, source_type, category, transcript, summary,
                urgency_score, speaker_count, audio_duration, raw_audio_path,
                telegram_msg_id, key_topics, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                conv.id,
                conv.timestamp.isoformat(),
                conv.source_type,
                conv.category,
                conv.transcript,
                conv.summary,
                conv.urgency_score,
                conv.speaker_count,
                conv.audio_duration,
                conv.raw_audio_path,
                conv.telegram_msg_id,
                json.dumps(conv.key_topics),
                _now_iso(),
            ),
        )
        await self._db.conn.commit()
        return conv.id

    async def get_recent(self, limit: int = 5) -> list[dict]:
        async with self._db.conn.execute(
            "SELECT id, summary, category, key_topics, timestamp "
            "FROM conversations ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


class ActionItemRepo:
    def __init__(self, db: Database):
        self._db = db

    async def insert(self, item: ActionItemRecord) -> str:
        await self._db.conn.execute(
            """INSERT INTO action_items
               (id, conversation_id, description, deadline, priority,
                assigned_to, category, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.id,
                item.conversation_id,
                item.description,
                item.deadline.isoformat() if item.deadline else None,
                item.priority,
                item.assigned_to,
                item.category,
                item.status,
                _now_iso(),
            ),
        )
        await self._db.conn.commit()
        return item.id

    async def get_pending(self) -> list[dict]:
        async with self._db.conn.execute(
            "SELECT id, description, deadline, priority, category, assigned_to "
            "FROM action_items WHERE status = 'pending' ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_status(
        self, item_id: str, status: str, completed_at: str | None = None
    ) -> None:
        if status == "done" and completed_at is None:
            completed_at = _now_iso()
        await self._db.conn.execute(
            "UPDATE action_items SET status = ?, completed_at = ? WHERE id = ?",
            (status, completed_at, item_id),
        )
        await self._db.conn.commit()

    async def snooze(self, item_id: str, until: datetime) -> None:
        await self._db.conn.execute(
            "UPDATE action_items SET status = 'snoozed', snoozed_until = ? WHERE id = ?",
            (until.isoformat(), item_id),
        )
        await self._db.conn.commit()


class CalendarEventRepo:
    def __init__(self, db: Database):
        self._db = db

    async def insert(
        self,
        conversation_id: str,
        google_event_id: str,
        google_event_link: str | None,
        title: str,
        start_time: datetime,
        end_time: datetime | None,
        category: str,
        calendar_id: str,
    ) -> str:
        record_id = _new_id()
        await self._db.conn.execute(
            """INSERT INTO calendar_events
               (id, conversation_id, google_event_id, google_event_link,
                title, start_time, end_time, category, calendar_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record_id,
                conversation_id,
                google_event_id,
                google_event_link,
                title,
                start_time.isoformat(),
                end_time.isoformat() if end_time else None,
                category,
                calendar_id,
                _now_iso(),
            ),
        )
        await self._db.conn.commit()
        return record_id


class PeopleRepo:
    def __init__(self, db: Database):
        self._db = db

    async def upsert_person(
        self, name: str, role: str | None, category: str | None
    ) -> str:
        normalized = name.strip().lower()
        async with self._db.conn.execute(
            "SELECT id, mention_count FROM people WHERE normalized_name = ?",
            (normalized,),
        ) as cursor:
            row = await cursor.fetchone()

        now = _now_iso()
        if row:
            person_id = row["id"]
            await self._db.conn.execute(
                "UPDATE people SET last_seen = ?, mention_count = mention_count + 1, "
                "role = COALESCE(?, role), category = COALESCE(?, category) "
                "WHERE id = ?",
                (now, role, category, person_id),
            )
        else:
            person_id = _new_id()
            await self._db.conn.execute(
                """INSERT INTO people
                   (id, name, normalized_name, first_seen, last_seen,
                    mention_count, role, category, created_at)
                   VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)""",
                (person_id, name, normalized, now, now, role, category, now),
            )
        await self._db.conn.commit()
        return person_id

    async def find_person_by_name(self, name: str) -> dict | None:
        """Look up a person record by normalized name."""
        normalized = name.strip().lower()
        async with self._db.conn.execute(
            "SELECT id, name, email FROM people WHERE normalized_name = ?",
            (normalized,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_email(self, person_id: str, email: str) -> None:
        """Save or update a person's email address."""
        await self._db.conn.execute(
            "UPDATE people SET email = ? WHERE id = ?",
            (email, person_id),
        )
        await self._db.conn.commit()

    async def add_mention(
        self, person_id: str, conversation_id: str, context: str
    ) -> None:
        mention_id = _new_id()
        try:
            await self._db.conn.execute(
                """INSERT INTO person_mentions
                   (id, person_id, conversation_id, context, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (mention_id, person_id, conversation_id, context, _now_iso()),
            )
            await self._db.conn.commit()
        except Exception:
            # Unique constraint violation - already recorded this mention
            pass
