"""Downloads screen for managing episode downloads."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from feedback.widgets.download_list import DownloadList
from feedback.widgets.player_bar import PlayerBar

if TYPE_CHECKING:
    from textual.app import ComposeResult


class DownloadsScreen(Screen[None]):
    """Screen for managing downloads."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("j", "move_down", "Down", show=False),
        Binding("k", "move_up", "Up", show=False),
        Binding("enter", "play", "Play"),
        Binding("d", "delete", "Delete"),
        Binding("c", "cancel", "Cancel"),
        Binding("C", "cancel_all", "Cancel All"),
        Binding("p", "play_pause", "Play/Pause"),
        Binding("space", "play_pause", "Play/Pause", show=False),
    ]

    def compose(self) -> ComposeResult:
        """Compose the downloads screen layout."""
        yield Header()
        yield PlayerBar()
        with Vertical(id="downloads-content"):
            yield Static("Downloads", id="downloads-title")
            yield DownloadList()
        yield Footer()

    def action_move_down(self) -> None:
        """Move selection down."""
        try:
            download_list = self.query_one(DownloadList)
            download_list.action_cursor_down()
        except Exception:
            pass

    def action_move_up(self) -> None:
        """Move selection up."""
        try:
            download_list = self.query_one(DownloadList)
            download_list.action_cursor_up()
        except Exception:
            pass

    def action_play(self) -> None:
        """Play the selected downloaded episode."""
        self.notify("Playing downloaded episode...")

    def action_delete(self) -> None:
        """Delete the selected download."""
        self.notify("Deleting download...")

    def action_cancel(self) -> None:
        """Cancel the selected download."""
        self.notify("Cancelling download...")

    def action_cancel_all(self) -> None:
        """Cancel all downloads."""
        self.notify("Cancelling all downloads...")

    def action_play_pause(self) -> None:
        """Toggle play/pause."""
        self.notify("Play/Pause")
