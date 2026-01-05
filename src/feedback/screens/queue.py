"""Queue screen for managing the playback queue."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from feedback.widgets.player_bar import PlayerBar
from feedback.widgets.queue_list import QueueList

if TYPE_CHECKING:
    from textual.app import ComposeResult


class QueueScreen(Screen[None]):
    """Screen for managing the playback queue."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("j", "move_down", "Down", show=False),
        Binding("k", "move_up", "Up", show=False),
        Binding("enter", "play", "Play"),
        Binding("d", "remove", "Remove"),
        Binding("c", "clear", "Clear Queue"),
        Binding("u", "move_item_up", "Move Up"),
        Binding("n", "move_item_down", "Move Down"),
        Binding("p", "play_pause", "Play/Pause"),
        Binding("space", "play_pause", "Play/Pause", show=False),
    ]

    def compose(self) -> ComposeResult:
        """Compose the queue screen layout."""
        yield Header()
        yield PlayerBar()
        with Vertical(id="queue-content"):
            yield Static("Playback Queue", id="queue-title")
            yield QueueList()
        yield Footer()

    def action_move_down(self) -> None:
        """Move selection down."""
        try:
            queue_list = self.query_one(QueueList)
            queue_list.action_cursor_down()
        except Exception:
            pass

    def action_move_up(self) -> None:
        """Move selection up."""
        try:
            queue_list = self.query_one(QueueList)
            queue_list.action_cursor_up()
        except Exception:
            pass

    def action_play(self) -> None:
        """Play the selected queue item."""
        self.notify("Playing selected item...")

    def action_remove(self) -> None:
        """Remove the selected item from the queue."""
        self.notify("Removing item from queue...")

    def action_clear(self) -> None:
        """Clear the entire queue."""
        self.notify("Clearing queue...")

    def action_move_item_up(self) -> None:
        """Move the selected item up in the queue."""
        self.notify("Moving item up...")

    def action_move_item_down(self) -> None:
        """Move the selected item down in the queue."""
        self.notify("Moving item down...")

    def action_play_pause(self) -> None:
        """Toggle play/pause."""
        self.notify("Play/Pause")
