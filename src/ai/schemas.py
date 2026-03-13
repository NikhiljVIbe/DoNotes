from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    WORK = "work"
    PERSONAL = "personal"
    MIXED = "mixed"


class Priority(str, Enum):
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Person(BaseModel):
    name: str
    role: str | None = None
    context: str | None = None


class ActionItem(BaseModel):
    description: str
    deadline: datetime | None = None
    priority: Priority = Priority.MEDIUM
    assigned_to: str | None = None
    category: Category


class EventType(str, Enum):
    FAMILY = "family"
    PERSONAL = "personal"
    OFFICE = "office"
    BIRTHDAY = "birthday"


class CalendarEvent(BaseModel):
    title: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_minutes: int | None = None
    location: str | None = None
    attendees: list[str] = Field(default_factory=list)
    category: Category
    event_type: EventType = EventType.PERSONAL
    description: str | None = None


class Commitment(BaseModel):
    description: str
    made_by: str
    made_to: str
    deadline: datetime | None = None


class ProcessedMessage(BaseModel):
    category: Category
    summary: str
    action_items: list[ActionItem] = Field(default_factory=list)
    calendar_events: list[CalendarEvent] = Field(default_factory=list)
    commitments: list[Commitment] = Field(default_factory=list)
    people_mentioned: list[Person] = Field(default_factory=list)
    follow_up_needed: bool = False
    follow_up_date: datetime | None = None
    key_topics: list[str] = Field(default_factory=list)
    urgency_score: int = Field(ge=1, le=10, default=5)
