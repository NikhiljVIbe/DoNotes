"""Launch the DoNotes bot as a subprocess."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
BOT_ENTRY = PROJECT_ROOT / "__main__.py"
LOG_DIR = PROJECT_ROOT / "logs"
PID_FILE = PROJECT_ROOT / "data" / "donotes.pid"


def is_bot_running() -> dict:
    """Check if the bot is already running."""
    if not PID_FILE.exists():
        return {"running": False}

    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)  # Check if process is alive
        return {"running": True, "pid": pid}
    except (ValueError, ProcessLookupError, PermissionError):
        return {"running": False}


def launch_bot() -> dict:
    """Start the DoNotes bot as a detached subprocess."""
    status = is_bot_running()
    if status["running"]:
        return {"success": True, "pid": status["pid"], "message": "Bot is already running"}

    python_path = VENV_PYTHON if VENV_PYTHON.exists() else Path("python3")

    if not BOT_ENTRY.exists():
        return {"success": False, "error": f"Bot entry point not found: {BOT_ENTRY}"}

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    stdout_fh = open(LOG_DIR / "bot_stdout.log", "a")
    stderr_fh = open(LOG_DIR / "bot_stderr.log", "a")

    try:
        proc = subprocess.Popen(
            [str(python_path), str(BOT_ENTRY)],
            cwd=str(PROJECT_ROOT),
            stdout=stdout_fh,
            stderr=stderr_fh,
            start_new_session=True,
        )
        log.info("Bot started with PID %d", proc.pid)
        return {"success": True, "pid": proc.pid, "message": "Bot started successfully!"}
    except Exception as exc:
        log.exception("Failed to start bot")
        stdout_fh.close()
        stderr_fh.close()
        return {"success": False, "error": str(exc)}
