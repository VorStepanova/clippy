"""Standalone subprocess that owns the pywebview chat window.

This script is spawned by ChatWindow.open() as a separate process so that
pywebview can take the main thread freely — rumps already owns the main
thread in the parent process and macOS does not allow two AppKit event
loops to share a thread.

Do NOT import this module from app.py or any other clippy module. It is
an entry point only; subprocess.Popen is the only caller.
"""

import os
import sys

# Resolve the project root (three levels up: chat_process.py → chat/ → clippy/ → project root)
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))

# Load .env before any other clippy imports so API keys are available
from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

import webview  # noqa: E402
from clippy.chat.client import ClippyClient  # noqa: E402

_client = ClippyClient()

_INDEX_HTML = os.path.join(_HERE, "ui", "index.html")


def _get_response(text: str) -> str:
    return _client.send(text)


class ClippyBridge:
    """Exposes Python methods to the JS running in the webview.

    Each public method becomes callable from JavaScript as
    ``window.pywebview.api.<method_name>(...)``.
    """

    def send_message(self, text: str) -> str:
        """Receive a message from the UI and return a response.

        Args:
            text: The raw string the user typed in the chat input.

        Returns:
            A reply string. Delegates to _get_response() so Phase 4 can
            swap in the real Claude call without touching this method.
        """
        return _get_response(text)


def main() -> None:
    bridge = ClippyBridge()
    webview.create_window(
        title="Clippy",
        url=f"file://{_INDEX_HTML}",
        js_api=bridge,
        width=380,
        height=600,
        on_top=True,
        frameless=False,
    )
    webview.start()


if __name__ == "__main__":
    main()
