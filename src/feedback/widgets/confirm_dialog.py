"""Confirmation dialog widget."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class ConfirmDialog(ModalScreen[bool]):
    """A modal confirmation dialog.

    Returns True if confirmed, False if cancelled.
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Confirm"),
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
    ]

    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
    }

    ConfirmDialog > Vertical {
        width: 50;
        height: auto;
        background: $surface;
        border: solid $warning;
        padding: 1 2;
    }

    ConfirmDialog .dialog-title {
        text-align: center;
        text-style: bold;
        color: $warning;
        padding-bottom: 1;
    }

    ConfirmDialog .dialog-message {
        text-align: center;
        padding: 1 0;
    }

    ConfirmDialog .button-row {
        height: auto;
        margin-top: 1;
        align: center middle;
    }

    ConfirmDialog Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        title: str = "Confirm",
        message: str = "Are you sure?",
        confirm_label: str = "Yes",
        cancel_label: str = "No",
    ) -> None:
        """Initialize the confirmation dialog.

        Args:
            title: The dialog title.
            message: The message to display.
            confirm_label: Label for the confirm button.
            cancel_label: Label for the cancel button.
        """
        super().__init__()
        self._title = title
        self._message = message
        self._confirm_label = confirm_label
        self._cancel_label = cancel_label

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        with Vertical():
            yield Static(self._title, classes="dialog-title")
            yield Static(self._message, classes="dialog-message")
            with Horizontal(classes="button-row"):
                yield Button(self._confirm_label, variant="warning", id="confirm-btn")
                yield Button(self._cancel_label, variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "confirm-btn":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self) -> None:
        """Confirm and close the dialog."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel and close the dialog."""
        self.dismiss(False)
