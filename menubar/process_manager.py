from __future__ import annotations

import logging
import os
import signal
import subprocess
import time
from typing import Optional

from menubar.constants import (
    VENV_PYTHON, BOT_ENTRY, PROJECT_ROOT, PID_FILE,
    BOT_STDOUT_LOG, BOT_STDERR_LOG, LOG_DIR, SHUTDOWN_TIMEOUT,
)

log = logging.getLogger(__name__)


class BotProcessManager:
    """Manages the DoNotes bot as a subprocess."""

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._pid: Optional[int] = None
        self._start_time: Optional[float] = None
        self._stdout_fh = None
        self._stderr_fh = None

    @property
    def is_running(self) -> bool:
        """Check if the bot process is alive."""
        # Check our own managed process first
        if self._process is not None:
            retcode = self._process.poll()
            if retcode is None:
                return True
            else:
                self._cleanup()
                return False

        # Check PID file for externally-started processes (launchd, terminal)
        pid = self._read_pid_file()
        if pid and self._is_pid_alive(pid) and self._is_donotes_process(pid):
            self._pid = pid
            return True

        return False

    @property
    def pid(self) -> Optional[int]:
        if self._process is not None:
            return self._process.pid
        return self._pid

    @property
    def uptime_seconds(self) -> Optional[float]:
        if self._start_time and self.is_running:
            return time.time() - self._start_time
        return None

    def start(self) -> bool:
        """Start the bot subprocess. Returns True on success."""
        if self.is_running:
            log.warning("Bot is already running (PID %s)", self.pid)
            return False

        if not VENV_PYTHON.exists():
            log.error("Virtual env python not found: %s", VENV_PYTHON)
            return False

        if not BOT_ENTRY.exists():
            log.error("Bot entry point not found: %s", BOT_ENTRY)
            return False

        LOG_DIR.mkdir(parents=True, exist_ok=True)

        self._stdout_fh = open(BOT_STDOUT_LOG, "a")
        self._stderr_fh = open(BOT_STDERR_LOG, "a")

        try:
            self._process = subprocess.Popen(
                [str(VENV_PYTHON), str(BOT_ENTRY)],
                cwd=str(PROJECT_ROOT),
                stdout=self._stdout_fh,
                stderr=self._stderr_fh,
                start_new_session=True,
            )
            self._start_time = time.time()
            log.info("Bot started with PID %d", self._process.pid)
            return True
        except Exception:
            log.exception("Failed to start bot")
            self._close_log_handles()
            return False

    def stop(self) -> bool:
        """Stop the bot gracefully. Returns True if stopped."""
        pid = self.pid
        if not pid:
            log.warning("No bot process to stop")
            return False

        if not self._is_pid_alive(pid):
            self._cleanup()
            return True

        # SIGTERM for graceful shutdown
        log.info("Sending SIGTERM to PID %d", pid)
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            self._cleanup()
            return True

        # Wait for graceful shutdown
        deadline = time.time() + SHUTDOWN_TIMEOUT
        while time.time() < deadline:
            if not self._is_pid_alive(pid):
                log.info("Bot stopped gracefully")
                self._cleanup()
                return True
            time.sleep(0.5)

        # Force kill
        log.warning("Bot did not stop in %ds, sending SIGKILL", SHUTDOWN_TIMEOUT)
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self._cleanup()
        return True

    def detect_existing(self) -> bool:
        """Check if a bot instance is already running (launchd, terminal, etc.)."""
        # Check PID file first
        pid = self._read_pid_file()
        if pid and self._is_pid_alive(pid) and self._is_donotes_process(pid):
            self._pid = pid
            self._start_time = self._get_process_start_time(pid)
            log.info("Detected existing bot: PID %d", pid)
            return True

        # Fallback: scan for orphaned processes
        return self._scan_for_bot_process()

    def _cleanup(self):
        self._process = None
        self._pid = None
        self._start_time = None
        self._remove_pid_file()
        self._close_log_handles()

    def _close_log_handles(self):
        for fh in (self._stdout_fh, self._stderr_fh):
            if fh:
                try:
                    fh.close()
                except Exception:
                    pass
        self._stdout_fh = None
        self._stderr_fh = None

    # --- PID file ---

    @staticmethod
    def _read_pid_file() -> Optional[int]:
        try:
            return int(PID_FILE.read_text().strip())
        except (FileNotFoundError, ValueError):
            return None

    @staticmethod
    def _write_pid_file(pid: int):
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(pid))

    @staticmethod
    def _remove_pid_file():
        try:
            PID_FILE.unlink()
        except FileNotFoundError:
            pass

    # --- Process detection ---

    @staticmethod
    def _is_pid_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False

    @staticmethod
    def _is_donotes_process(pid: int) -> bool:
        try:
            result = subprocess.run(
                ["ps", "-p", str(pid), "-o", "command="],
                capture_output=True, text=True, timeout=3,
            )
            cmd = result.stdout.strip()
            return "__main__.py" in cmd or "donotes" in cmd.lower()
        except Exception:
            return False

    @staticmethod
    def _get_process_start_time(pid: int) -> Optional[float]:
        try:
            result = subprocess.run(
                ["ps", "-p", str(pid), "-o", "etime="],
                capture_output=True, text=True, timeout=3,
            )
            etime = result.stdout.strip()
            parts = etime.replace("-", ":").split(":")
            parts = [int(p) for p in parts]
            seconds = 0
            if len(parts) == 2:
                seconds = parts[0] * 60 + parts[1]
            elif len(parts) == 3:
                seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
            elif len(parts) == 4:
                seconds = parts[0] * 86400 + parts[1] * 3600 + parts[2] * 60 + parts[3]
            return time.time() - seconds
        except Exception:
            return None

    def _scan_for_bot_process(self) -> bool:
        try:
            result = subprocess.run(
                ["pgrep", "-f", "__main__.py"],
                capture_output=True, text=True, timeout=3,
            )
            for line in result.stdout.strip().splitlines():
                pid = int(line.strip())
                if pid == os.getpid():
                    continue
                if self._is_donotes_process(pid):
                    self._pid = pid
                    self._start_time = self._get_process_start_time(pid)
                    self._write_pid_file(pid)
                    log.info("Found orphaned bot process: PID %d", pid)
                    return True
        except Exception:
            pass
        return False
