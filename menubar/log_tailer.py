from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

LOG_TIMESTAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
PROCESSING_RE = re.compile(r"Processing (voice_memo|text_note|audio_file)")


class LogTailer:
    """Tail a log file to extract last activity and message counts."""

    def __init__(self, log_path: Path):
        self._path = log_path
        self._offset: int = 0
        self._last_activity: Optional[datetime] = None
        self._message_count: int = 0

    def reset(self):
        self._offset = 0
        self._last_activity = None
        self._message_count = 0

    def seek_to_end(self):
        try:
            self._offset = self._path.stat().st_size
        except FileNotFoundError:
            self._offset = 0

    def update(self):
        """Read new log lines and update status."""
        if not self._path.exists():
            return
        try:
            size = self._path.stat().st_size
            if size < self._offset:
                self._offset = 0  # File truncated/rotated
            if size == self._offset:
                return

            with open(self._path, "r") as f:
                f.seek(self._offset)
                for line in f:
                    m = LOG_TIMESTAMP_RE.match(line)
                    if m:
                        try:
                            self._last_activity = datetime.strptime(
                                m.group(1), "%Y-%m-%d %H:%M:%S"
                            )
                        except ValueError:
                            pass
                    if PROCESSING_RE.search(line):
                        self._message_count += 1
                self._offset = f.tell()
        except Exception:
            pass

    @property
    def last_activity(self) -> Optional[datetime]:
        return self._last_activity

    @property
    def last_activity_ago(self) -> str:
        if not self._last_activity:
            return "No activity yet"
        delta = datetime.now() - self._last_activity
        seconds = int(delta.total_seconds())
        if seconds < 0:
            return "Just now"
        elif seconds < 60:
            return f"{seconds}s ago"
        elif seconds < 3600:
            return f"{seconds // 60}m ago"
        elif seconds < 86400:
            return f"{seconds // 3600}h ago"
        else:
            return f"{seconds // 86400}d ago"

    @property
    def message_count(self) -> int:
        return self._message_count
