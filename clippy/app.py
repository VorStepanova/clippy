"""Clippy menu bar application — orchestration layer.

This module owns the rumps event loop, all timers, and the wiring between
every other module. It is the single place where observations (from monitor,
reminders, chat) get turned into UI decisions.

In Phase 1 the app does three things only:
1. Shows a menu bar icon.
2. Starts the activity monitor.
3. Provides a Quit item and a timer stub for Phase 2 wiring.
"""

import rumps

from clippy.monitor import Monitor


class ClippyApp(rumps.App):
    """Minimal rumps application for Phase 1.

    Boots the monitor, registers the timer tick, and exposes a Quit item.
    Feature logic (icon selection, chat, reminders) is added in later phases.
    """

    def __init__(self) -> None:
        super().__init__("📎", quit_button="Quit")
        self._monitor = Monitor()
        self._monitor.start()
        self._tick_timer = rumps.Timer(self._tick, 5)
        self._tick_timer.start()

    def _tick(self, _sender: rumps.Timer) -> None:
        """Timer callback — fires every 5 seconds on the main thread.

        Stub for Phase 1. Will be wired to face.py in Phase 2.
        """
        pass
