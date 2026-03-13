from __future__ import annotations

import logging
import subprocess

import rumps

from menubar.constants import (
    APP_NAME, ICON_GREEN, ICON_RED, ICON_GRAY,
    STATUS_CHECK_INTERVAL, BOT_STDERR_LOG,
)
from menubar.process_manager import BotProcessManager
from menubar.log_tailer import LogTailer

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class DoNotesMenuBarApp(rumps.App):
    def __init__(self):
        super().__init__(
            name=APP_NAME,
            icon=ICON_GRAY,
            template=False,  # Allow colored icons
            quit_button=None,  # Custom quit
        )

        self.manager = BotProcessManager()
        self.tailer = LogTailer(BOT_STDERR_LOG)

        # Menu items
        self.toggle_button = rumps.MenuItem("Start Bot", callback=self.on_toggle)
        self.status_item = rumps.MenuItem("Status: Checking...")
        self.status_item.set_callback(None)
        self.uptime_item = rumps.MenuItem("Uptime: --")
        self.uptime_item.set_callback(None)
        self.activity_item = rumps.MenuItem("Last Activity: --")
        self.activity_item.set_callback(None)
        self.messages_item = rumps.MenuItem("Messages: 0")
        self.messages_item.set_callback(None)
        self.open_logs_item = rumps.MenuItem("Open Logs...", callback=self.on_open_logs)
        self.quit_item = rumps.MenuItem("Quit DoNotes", callback=self.on_quit)

        self.menu = [
            self.toggle_button,
            rumps.separator,
            self.status_item,
            self.uptime_item,
            self.activity_item,
            self.messages_item,
            rumps.separator,
            self.open_logs_item,
            self.quit_item,
        ]

        # Detect existing bot on startup
        self.manager.detect_existing()
        self.tailer.seek_to_end()
        self._update_ui()

        # Status check timer
        self._timer = rumps.Timer(self._on_tick, STATUS_CHECK_INTERVAL)
        self._timer.start()

    def _on_tick(self, _timer):
        self.tailer.update()
        self._update_ui()

    def _update_ui(self):
        running = self.manager.is_running

        if running:
            self.icon = ICON_GREEN
            self.toggle_button.title = "Stop Bot"
            self.status_item.title = "Status: Running (PID {})".format(self.manager.pid)

            uptime = self.manager.uptime_seconds
            if uptime is not None:
                self.uptime_item.title = "Uptime: {}".format(self._format_uptime(uptime))
            else:
                self.uptime_item.title = "Uptime: Unknown"

            self.activity_item.title = "Last Activity: {}".format(self.tailer.last_activity_ago)
            self.messages_item.title = "Messages: {}".format(self.tailer.message_count)
        else:
            self.icon = ICON_RED
            self.toggle_button.title = "Start Bot"
            self.status_item.title = "Status: Stopped"
            self.uptime_item.title = "Uptime: --"
            self.activity_item.title = "Last Activity: --"
            self.messages_item.title = "Messages: --"

    def on_toggle(self, sender):
        if self.manager.is_running:
            self.icon = ICON_GRAY
            self.status_item.title = "Status: Stopping..."
            success = self.manager.stop()
            if success:
                self.tailer.reset()
                rumps.notification(APP_NAME, "Bot Stopped", "DoNotes bot has been stopped.")
            else:
                rumps.notification(APP_NAME, "Error", "Failed to stop the bot.")
        else:
            self.icon = ICON_GRAY
            self.status_item.title = "Status: Starting..."
            success = self.manager.start()
            if success:
                self.tailer.seek_to_end()
                rumps.notification(APP_NAME, "Bot Started", "DoNotes bot is now running.")
            else:
                rumps.notification(APP_NAME, "Error", "Failed to start the bot. Check .venv exists.")
        self._update_ui()

    def on_open_logs(self, _sender):
        log_path = str(BOT_STDERR_LOG)
        subprocess.Popen(["open", log_path])

    def on_quit(self, _sender):
        if self.manager.is_running:
            response = rumps.alert(
                title="Quit DoNotes",
                message="The bot is still running. What would you like to do?",
                ok="Stop Bot & Quit",
                cancel="Keep Running & Quit",
            )
            if response == 1:  # OK
                self.manager.stop()
        rumps.quit_application()

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        s = int(seconds)
        if s < 60:
            return "{}s".format(s)
        elif s < 3600:
            return "{}m {}s".format(s // 60, s % 60)
        elif s < 86400:
            h, remainder = divmod(s, 3600)
            m = remainder // 60
            return "{}h {}m".format(h, m)
        else:
            d, remainder = divmod(s, 86400)
            h = remainder // 3600
            return "{}d {}h".format(d, h)
