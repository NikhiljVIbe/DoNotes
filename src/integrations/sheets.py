from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.settings import Settings
from src.ai.schemas import Category, EventType, ProcessedMessage
from src.integrations.google_auth import GoogleAuth

log = logging.getLogger(__name__)

TAB_WORK = "Work"
TAB_PERSONAL = "Personal"

HEADERS = [
    "Date",           # A
    "Summary",        # B
    "Action Items",   # C
    "Calendar Events",# D
    "Event Type",     # E
    "Commitments",    # F
    "People",         # G
    "Urgency",        # H
    "Status",         # I
    "IDs",            # J (hidden, for status update lookups)
    "Source",         # K
]

# RGB colors for the Event Type cell (matching Google Calendar colors)
EVENT_TYPE_COLORS = {
    EventType.FAMILY: {"red": 0.56, "green": 0.36, "blue": 0.68},    # Purple
    EventType.PERSONAL: {"red": 0.24, "green": 0.47, "blue": 0.85},  # Blue
    EventType.OFFICE: {"red": 0.06, "green": 0.56, "blue": 0.35},    # Green
    EventType.BIRTHDAY: {"red": 0.95, "green": 0.52, "blue": 0.10},  # Orange
}

EVENT_TYPE_TEXT_COLOR = {"red": 1.0, "green": 1.0, "blue": 1.0}  # White text


def _fmt_deadline(dt: datetime | None) -> str:
    return f" (by {dt.strftime('%b %d')})" if dt else ""


class SheetsManager:
    """Manages a Google Sheets tracker with Work and Personal tabs."""

    def __init__(self, google_auth: GoogleAuth, settings: Settings):
        self._auth = google_auth
        self._settings = settings
        self._spreadsheet_id: str | None = settings.google_sheet_id or None
        self._sheet_ids: dict[str, int] = {}  # tab name -> sheetId

    def _get_service(self):
        creds = self._auth.get_credentials()
        return build("sheets", "v4", credentials=creds)

    def _load_sheet_ids(self, service) -> None:
        """Load the numeric sheetId for each tab."""
        if self._sheet_ids:
            return
        result = service.spreadsheets().get(
            spreadsheetId=self._spreadsheet_id
        ).execute()
        for s in result.get("sheets", []):
            self._sheet_ids[s["properties"]["title"]] = s["properties"]["sheetId"]

    def _ensure_spreadsheet(self) -> str:
        """Create spreadsheet if it doesn't exist, return its ID."""
        if self._spreadsheet_id:
            try:
                service = self._get_service()
                service.spreadsheets().get(
                    spreadsheetId=self._spreadsheet_id
                ).execute()
                return self._spreadsheet_id
            except HttpError as e:
                if e.resp.status == 404:
                    log.warning("Configured sheet not found, creating new one")
                    self._spreadsheet_id = None
                else:
                    raise

        service = self._get_service()
        body = {
            "properties": {"title": "DoNotes Tracker"},
            "sheets": [
                {"properties": {"title": TAB_WORK}},
                {"properties": {"title": TAB_PERSONAL}},
            ],
        }
        result = service.spreadsheets().create(body=body).execute()
        self._spreadsheet_id = result["spreadsheetId"]
        log.info("Created new tracker sheet: %s", self._spreadsheet_id)

        # Persist the ID to .env so it survives restarts
        self._save_sheet_id_to_env(self._spreadsheet_id)

        # Cache sheet IDs
        self._sheet_ids = {
            s["properties"]["title"]: s["properties"]["sheetId"]
            for s in result.get("sheets", [])
        }

        # Write headers to both tabs
        for tab in [TAB_WORK, TAB_PERSONAL]:
            service.spreadsheets().values().update(
                spreadsheetId=self._spreadsheet_id,
                range=f"'{tab}'!A1",
                valueInputOption="RAW",
                body={"values": [HEADERS]},
            ).execute()

        # Freeze header row on both tabs
        requests = []
        for tab in [TAB_WORK, TAB_PERSONAL]:
            if tab in self._sheet_ids:
                requests.append({
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": self._sheet_ids[tab],
                            "gridProperties": {"frozenRowCount": 1},
                        },
                        "fields": "gridProperties.frozenRowCount",
                    }
                })
        if requests:
            service.spreadsheets().batchUpdate(
                spreadsheetId=self._spreadsheet_id,
                body={"requests": requests},
            ).execute()

        return self._spreadsheet_id

    def append_processed_message(
        self,
        processed: ProcessedMessage,
        summary: str,
        source_type: str,
        action_item_ids: list[str],
    ) -> None:
        """Append one row per message to the appropriate tab(s)."""
        sheet_id = self._ensure_spreadsheet()
        service = self._get_service()
        self._load_sheet_ids(service)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        tabs = self._get_tabs_for_category(processed.category)

        # Build action items cell
        action_items_parts = []
        for item in processed.action_items:
            line = f"- {item.description}{_fmt_deadline(item.deadline)}"
            if item.assigned_to:
                line += f" [{item.assigned_to}]"
            if item.priority.value in ("urgent", "high"):
                line += f" ({item.priority.value})"
            action_items_parts.append(line)
        action_items_str = "\n".join(action_items_parts)

        # Build calendar events cell and collect event types
        events_parts = []
        event_types = []
        for ev in processed.calendar_events:
            time_str = ev.start_time.strftime("%b %d %H:%M") if ev.start_time else ""
            line = f"- {ev.title} @ {time_str}"
            if ev.location:
                line += f" ({ev.location})"
            events_parts.append(line)
            event_types.append(ev.event_type)
        events_str = "\n".join(events_parts)

        # Build event type cell
        event_type_str = ", ".join(sorted(set(et.value for et in event_types))) if event_types else ""

        # Build commitments cell
        commitments_parts = []
        for c in processed.commitments:
            line = f"- {c.made_by} -> {c.made_to}: {c.description}{_fmt_deadline(c.deadline)}"
            commitments_parts.append(line)
        commitments_str = "\n".join(commitments_parts)

        # Build people cell
        people_parts = []
        for p in processed.people_mentioned:
            line = p.name
            if p.role:
                line += f" ({p.role})"
            people_parts.append(line)
        people_str = ", ".join(people_parts)

        # Determine status
        has_pending = bool(processed.action_items or processed.commitments)
        status = "pending" if has_pending else "done"

        # Store IDs for status update lookups
        ids_str = ",".join(action_item_ids)

        row = [
            now_str,
            summary,
            action_items_str,
            events_str,
            event_type_str,
            commitments_str,
            people_str,
            str(processed.urgency_score),
            status,
            ids_str,
            source_type,
        ]

        for tab in tabs:
            try:
                result = service.spreadsheets().values().append(
                    spreadsheetId=sheet_id,
                    range=f"'{tab}'!A:K",
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body={"values": [row]},
                ).execute()
                log.info("Appended 1 row to %s tab", tab)

                # Color-code the Event Type cell
                if event_types and tab in self._sheet_ids:
                    row_num = self._parse_appended_row(result)
                    if row_num:
                        # Use the first event type for the cell color
                        primary_type = event_types[0]
                        self._color_event_type_cell(
                            service, self._sheet_ids[tab],
                            row_num, primary_type,
                        )
            except Exception:
                log.exception("Failed to append row to %s tab", tab)

    def _parse_appended_row(self, append_result: dict) -> int | None:
        """Extract the row number from the append API response."""
        try:
            updated_range = append_result.get("updates", {}).get("updatedRange", "")
            # e.g. "'Work'!A5:K5"
            cell_range = updated_range.split("!")[-1]
            start_cell = cell_range.split(":")[0]
            return int("".join(c for c in start_cell if c.isdigit()))
        except (ValueError, IndexError):
            return None

    def _color_event_type_cell(
        self, service, sheet_id: int, row_num: int, event_type: EventType
    ) -> None:
        """Apply background color to the Event Type cell (column E = index 4)."""
        bg_color = EVENT_TYPE_COLORS.get(event_type)
        if not bg_color:
            return

        requests = [{
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row_num - 1,  # 0-based
                    "endRowIndex": row_num,
                    "startColumnIndex": 4,  # Column E
                    "endColumnIndex": 5,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": bg_color,
                        "textFormat": {
                            "foregroundColor": EVENT_TYPE_TEXT_COLOR,
                            "bold": True,
                        },
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        }]

        try:
            service.spreadsheets().batchUpdate(
                spreadsheetId=self._spreadsheet_id,
                body={"requests": requests},
            ).execute()
        except Exception:
            log.exception("Failed to color event type cell")

    def update_action_item_status(self, item_id: str, new_status: str) -> None:
        """Find a row containing this action item ID and update its Status cell."""
        if not self._spreadsheet_id:
            return

        service = self._get_service()

        for tab in [TAB_WORK, TAB_PERSONAL]:
            try:
                # Read IDs column (J) to find the row
                result = service.spreadsheets().values().get(
                    spreadsheetId=self._spreadsheet_id,
                    range=f"'{tab}'!J:J",
                ).execute()
                values = result.get("values", [])

                for row_idx, row in enumerate(values):
                    if row and item_id in row[0].split(","):
                        # Status is column I (index 9, 1-based)
                        cell = f"'{tab}'!I{row_idx + 1}"
                        service.spreadsheets().values().update(
                            spreadsheetId=self._spreadsheet_id,
                            range=cell,
                            valueInputOption="RAW",
                            body={"values": [[new_status]]},
                        ).execute()
                        log.info(
                            "Updated sheet status for %s to %s in %s",
                            item_id, new_status, tab,
                        )
            except Exception:
                log.exception("Failed to update sheet status in tab %s", tab)

    def _save_sheet_id_to_env(self, sheet_id: str) -> None:
        """Persist the sheet ID to .env so it's reused across restarts."""
        env_path = self._settings.project_root / ".env"
        key = "DONOTES_GOOGLE_SHEET_ID"
        line = f"{key}={sheet_id}\n"

        if env_path.exists():
            content = env_path.read_text()
            if re.search(rf"^{key}=", content, re.MULTILINE):
                content = re.sub(
                    rf"^{key}=.*$", f"{key}={sheet_id}", content, flags=re.MULTILINE
                )
            else:
                content = content.rstrip("\n") + "\n" + line
            env_path.write_text(content)
        else:
            env_path.write_text(line)

        log.info("Saved sheet ID to %s", env_path)

    def _get_tabs_for_category(self, category: Category) -> list[str]:
        if category == Category.WORK:
            return [TAB_WORK]
        elif category == Category.PERSONAL:
            return [TAB_PERSONAL]
        else:
            return [TAB_WORK, TAB_PERSONAL]
