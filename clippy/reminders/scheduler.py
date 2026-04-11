"""Scheduler — checks pending reminders every 60 seconds and fires due ones.

Runs as a daemon thread started from app.py. Fires a reminder by:
- Sending a macOS notification
- Writing to ~/.clippy_chat_inject.json for chat_process.py to pick up

Removes fired reminders from the pending file and logs them to
~/.clippy_completions.json.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timedelta

import rumps

from clippy.reminders.state import resolve_pending
from clippy.reminders.escalator import escalate

INJECT_PATH = os.path.expanduser("~/.clippy_chat_inject.json")
COMPLETIONS_PATH = os.path.expanduser("~/.clippy_completions.json")
PENDING_PATH = os.path.expanduser("~/.clippy_pending_reminders.json")
_POLL_INTERVAL = 60  # seconds


def _write_inject(message: str) -> None:
    try:
        with open(INJECT_PATH, "w") as f:
            json.dump({
                "message": message,
                "written_at": datetime.now().isoformat(timespec="seconds"),
            }, f, indent=2)
    except Exception:
        pass


def _log_fired(label: str) -> None:
    existing: list[dict] = []
    if os.path.exists(COMPLETIONS_PATH):
        try:
            with open(COMPLETIONS_PATH) as f:
                existing = json.load(f)
        except Exception:
            pass
    existing.append({
        "task": label,
        "completed_at": datetime.now().isoformat(timespec="seconds"),
        "source": "reminder",
    })
    try:
        with open(COMPLETIONS_PATH, "w") as f:
            json.dump(existing, f, indent=2)
    except Exception:
        pass


def _remove_fired(label: str, due_at: str) -> None:
    """Remove one fired reminder from the pending file by (label, due_at)."""
    if not os.path.exists(PENDING_PATH):
        return
    try:
        with open(PENDING_PATH) as f:
            reminders = json.load(f)
        reminders = [
            r for r in reminders
            if not (r.get("label") == label and r.get("due_at") == due_at)
        ]
        with open(PENDING_PATH, "w") as f:
            json.dump(reminders, f, indent=2)
    except Exception:
        pass


def _snooze_reminder(label: str, due_at: str) -> None:
    """Increment snooze_count and set next_fire_at 30 min from now."""
    if not os.path.exists(PENDING_PATH):
        return
    try:
        with open(PENDING_PATH) as f:
            reminders = json.load(f)
        for r in reminders:
            if r.get("label") == label and r.get("due_at") == due_at:
                r["snooze_count"] = r.get("snooze_count", 0) + 1
                r["next_fire_at"] = (
                    datetime.now() + timedelta(minutes=30)
                ).isoformat(timespec="seconds")
                break
        with open(PENDING_PATH, "w") as f:
            json.dump(reminders, f, indent=2)
    except Exception:
        pass


def _check_and_fire() -> None:
    now = datetime.now()
    pending = resolve_pending()
    for reminder in pending:
        due_at_str = reminder.get("due_at", "")
        label = reminder.get("label", "Reminder")

        # Respect next_fire_at if set (snooze delay)
        next_fire_str = reminder.get("next_fire_at")
        if next_fire_str:
            try:
                if datetime.fromisoformat(next_fire_str) > now:
                    continue
            except ValueError:
                pass

        try:
            due_at = datetime.fromisoformat(due_at_str)
        except ValueError:
            continue

        if due_at <= now:
            rumps.notification(
                title="⏰ Clippy Reminder",
                subtitle=label,
                message=reminder.get("raw", ""),
            )
            _write_inject(f"⏰ Your reminder fired: {label}. How'd it go?")

            acknowledged = escalate(reminder)

            if acknowledged:
                _log_fired(label)
                _remove_fired(label, due_at_str)
            else:
                _snooze_reminder(label, due_at_str)


def _scheduler_loop() -> None:
    while True:
        time.sleep(_POLL_INTERVAL)
        try:
            _check_and_fire()
        except Exception:
            pass  # never let a transient error kill the scheduler thread


def start() -> None:
    """Start the scheduler daemon thread. Call once from app.py."""
    t = threading.Thread(target=_scheduler_loop, daemon=True, name="clippy-scheduler")
    t.start()
