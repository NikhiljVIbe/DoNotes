from __future__ import annotations

import logging
from datetime import datetime, timedelta

from googleapiclient.discovery import build

from config.calendars import get_calendar_id
from config.settings import Settings
from src.ai.schemas import CalendarEvent, EventType
from src.integrations.google_auth import GoogleAuth

log = logging.getLogger(__name__)

# Google Calendar color IDs
# See: https://developers.google.com/calendar/api/v3/reference/colors
EVENT_TYPE_COLORS = {
    EventType.FAMILY: "3",     # Grape (purple)
    EventType.PERSONAL: "9",   # Blueberry (blue)
    EventType.OFFICE: "10",    # Basil (green)
    EventType.BIRTHDAY: "6",   # Tangerine (orange)
}


class CalendarManager:
    def __init__(self, google_auth: GoogleAuth, settings: Settings):
        self._auth = google_auth
        self._settings = settings

    def _get_service(self):
        creds = self._auth.get_credentials()
        return build("calendar", "v3", credentials=creds)

    def create_event(self, event: CalendarEvent) -> tuple[str, str | None]:
        """
        Create a Google Calendar event.
        Returns (event_id, event_link).
        """
        calendar_id = get_calendar_id(event.category.value, self._settings)

        start_time = event.start_time
        if not start_time:
            log.warning("No start_time for event '%s', skipping", event.title)
            return "", None

        # Determine end time
        if event.end_time:
            end_time = event.end_time
        elif event.duration_minutes:
            end_time = start_time + timedelta(minutes=event.duration_minutes)
        else:
            end_time = start_time + timedelta(hours=1)

        body = {
            "summary": event.title,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": self._settings.timezone,
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": self._settings.timezone,
            },
        }

        if event.description:
            body["description"] = event.description
        if event.location:
            body["location"] = event.location
        if event.attendees:
            body["attendees"] = [{"email": a} for a in event.attendees if "@" in a]

        # Color-code by event type
        color_id = EVENT_TYPE_COLORS.get(event.event_type)
        if color_id:
            body["colorId"] = color_id

        service = self._get_service()

        # Try the target calendar; fall back to personal if work calendar is inaccessible
        try:
            result = service.events().insert(
                calendarId=calendar_id, body=body
            ).execute()
        except Exception as e:
            if calendar_id != self._settings.personal_calendar_id:
                log.warning(
                    "Failed to create event in %s (%s), falling back to personal calendar",
                    calendar_id, e,
                )
                result = service.events().insert(
                    calendarId=self._settings.personal_calendar_id, body=body
                ).execute()
            else:
                raise

        event_id = result.get("id", "")
        event_link = result.get("htmlLink")
        log.info("Calendar event created: %s -> %s", event.title, event_link)
        return event_id, event_link

    def get_todays_events(self) -> list[dict]:
        """Fetch today's events from both work and personal calendars."""
        service = self._get_service()
        now = datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0).isoformat() + "Z"
        end_of_day = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"

        all_events = []
        for cal_id, cal_name in [
            (self._settings.work_calendar_id, "work"),
            (self._settings.personal_calendar_id, "personal"),
        ]:
            if not cal_id:
                continue
            result = service.events().list(
                calendarId=cal_id,
                timeMin=start_of_day,
                timeMax=end_of_day,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            for ev in result.get("items", []):
                ev["_calendar"] = cal_name
                all_events.append(ev)

        return sorted(
            all_events,
            key=lambda e: e.get("start", {}).get("dateTime", ""),
        )
