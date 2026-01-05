"""Loading overlay widget for long operations."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Center, Middle
from textual.screen import ModalScreen
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class LoadingOverlay(ModalScreen[None]):
    """A modal overlay showing loading progress.

    Can be dismissed by pressing Escape if cancellable.
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    LoadingOverlay {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }

    LoadingOverlay > Middle {
        width: auto;
        height: auto;
    }

    LoadingOverlay > Middle > Center {
        width: auto;
        height: auto;
        background: $surface;
        border: solid $primary;
        padding: 2 4;
    }

    LoadingOverlay .loading-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    LoadingOverlay .loading-message {
        text-align: center;
    }

    LoadingOverlay .loading-progress {
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        title: str = "Loading...",
        message: str = "",
        *,
        cancellable: bool = False,
    ) -> None:
        """Initialize the loading overlay.

        Args:
            title: The title text to display.
            message: Optional message below the title.
            cancellable: If True, can be dismissed with Escape.
        """
        super().__init__()
        self._title = title
        self._message = message
        self._cancellable = cancellable
        self._progress_text = ""
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        """Check if the operation was cancelled."""
        return self._cancelled

    def compose(self) -> ComposeResult:
        """Compose the loading overlay."""
        with Middle(), Center():
            yield Static(self._title, classes="loading-title", id="loading-title")
            yield Static(self._message, classes="loading-message", id="loading-message")
            yield Static(self._progress_text, classes="loading-progress", id="loading-progress")

    def update_title(self, title: str) -> None:
        """Update the title text.

        Args:
            title: New title text.
        """
        self._title = title
        with contextlib.suppress(Exception):
            self.query_one("#loading-title", Static).update(title)

    def update_message(self, message: str) -> None:
        """Update the message text.

        Args:
            message: New message text.
        """
        self._message = message
        with contextlib.suppress(Exception):
            self.query_one("#loading-message", Static).update(message)

    def update_progress(self, current: int, total: int, label: str = "") -> None:
        """Update progress display.

        Args:
            current: Current item number (1-indexed).
            total: Total number of items.
            label: Optional label for current item.
        """
        if label:
            self._progress_text = f"{current}/{total}: {label}"
        else:
            self._progress_text = f"{current}/{total}"
        with contextlib.suppress(Exception):
            self.query_one("#loading-progress", Static).update(self._progress_text)

    def action_cancel(self) -> None:
        """Handle cancel action."""
        if self._cancellable:
            self._cancelled = True
            self.dismiss()
