"""Clippy menu bar application — orchestration layer.

This module owns the rumps event loop, all timers, and the wiring between
every other module. It is the single place where observations (from monitor,
reminders, chat) get turned into UI decisions.
"""

import json
import os
from datetime import datetime

import rumps

from clippy.config import Config
from clippy.face import Face
from clippy.monitor import Monitor
from clippy.chat.window import ChatWindow
from clippy.reminders import scheduler


class ClippyApp(rumps.App):
    """rumps application — boots all subsystems and owns the timer loop.

    Instantiates Config, Monitor, and Face; starts the monitor thread; and
    updates the menu bar icon on every timer tick.
    """

    def __init__(self) -> None:
        super().__init__("📎", quit_button=None)
        self._config = Config()
        self._monitor = Monitor()
        self._monitor.start()
        self._face = Face(self._config, self._monitor)
        self._tick_timer = rumps.Timer(self._tick, 5)
        self._tick_timer.start()
        self._chat_window = ChatWindow()
        scheduler.start()
        self._history_item = rumps.MenuItem(
            self._history_label(),
            callback=self._toggle_history
        )
        self._retention_item = rumps.MenuItem(
            self._retention_label(),
            callback=self._toggle_retention
        )
        self.menu = [
            "💬 Open Chat",
            rumps.separator,
            self._history_item,
            self._retention_item,
            rumps.separator,
            "Quit",
        ]

    def _tick(self, _sender: rumps.Timer) -> None:
        """Timer callback — fires every 5 seconds on the main thread.

        Updates the menu bar icon based on current monitor state and config.
        """
        self.title = self._face.current_icon()
        self._write_monitor_snapshot()
        self._push_chat_face()

    def _write_monitor_snapshot(self) -> None:
        snapshot = {
            "active_app": self._monitor.current_app(),
            "app_duration_secs": self._monitor.current_app_duration(),
            "idle_secs": self._monitor.idle_duration(),
            "sampled_at": datetime.now().isoformat(timespec="seconds"),
        }
        path = os.path.expanduser("~/.clippy_monitor_state.json")
        try:
            with open(path, "w") as f:
                json.dump(snapshot, f, indent=2)
        except Exception:
            pass  # never let a write failure crash the main thread

    def _push_chat_face(self) -> None:
        """Write the current chat face emoji to ~/.clippy_face_state.json."""
        try:
            emoji = self._face.current_chat_face()
            path = os.path.expanduser("~/.clippy_face_state.json")
            with open(path, "w") as f:
                import json
                json.dump({"face": emoji}, f)
        except Exception:
            pass

    def _history_label(self) -> str:
        enabled = self._config.get("history_enabled", True)
        check = "✓ " if enabled else "   "
        return f"{check}Save chat history"

    def _retention_label(self) -> str:
        days = self._config.get("history_retention_days", None)
        if days is None:
            return "   History: unlimited"
        return f"   History: {days} days"

    def _toggle_history(self, _) -> None:
        enabled = self._config.get("history_enabled", True)
        self._config.set("history_enabled", not enabled)
        self._history_item.title = self._history_label()

    def _toggle_retention(self, _) -> None:
        days = self._config.get("history_retention_days", None)
        # Cycle: unlimited → 30 days → 7 days → unlimited
        if days is None:
            self._config.set("history_retention_days", 30)
        elif days == 30:
            self._config.set("history_retention_days", 7)
        else:
            self._config.set("history_retention_days", None)
        self._retention_item.title = self._retention_label()

    @rumps.clicked("💬 Open Chat")
    def _open_chat(self, _) -> None:
        self._chat_window.open()

    @rumps.clicked("Quit")
    def _quit(self, _) -> None:
        """Terminate the chat subprocess cleanly before quitting."""
        self._chat_window.close()
        rumps.quit_application()
