from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Conversation:
    id: str
    timestamp: datetime
    source_type: str
    category: str
    transcript: str
    summary: str
    urgency_score: int = 5
    speaker_count: int = 1
    audio_duration: float | None = None
    raw_audio_path: str | None = None
    telegram_msg_id: int = 0
    key_topics: list[str] = field(default_factory=list)
    created_at: datetime | None = None


@dataclass
class ActionItemRecord:
    id: str
    conversation_id: str
    description: str
    category: str
    priority: str = "medium"
    deadline: datetime | None = None
    assigned_to: str | None = None
    status: str = "pending"
    snoozed_until: datetime | None = None
    duplicate_of: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class CalendarEventRecord:
    id: str
    conversation_id: str
    google_event_id: str
    title: str
    start_time: datetime
    category: str
    calendar_id: str
    google_event_link: str | None = None
    end_time: datetime | None = None
    created_at: datetime | None = None


@dataclass
class PersonRecord:
    id: str
    name: str
    normalized_name: str
    first_seen: datetime
    last_seen: datetime
    mention_count: int = 1
    role: str | None = None
    category: str | None = None
    notes: str | None = None
    email: str | None = None
