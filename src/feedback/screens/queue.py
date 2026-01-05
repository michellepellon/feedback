"""Queue screen for managing the playback queue."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from feedback.models import QueueItem
from feedback.widgets.player_bar import PlayerBar
from feedback.widgets.queue_list import QueueItemSelected, QueueList

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from feedback.app import FeedbackApp
    from feedback.models import Episode


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

    def __init__(self) -> None:
        """Initialize the queue screen."""
        super().__init__()
        self._queue_items: list[tuple[QueueItem, Episode]] = []

    def compose(self) -> ComposeResult:
        """Compose the queue screen layout."""
        yield Header()
        yield PlayerBar()
        with Vertical(id="queue-content"):
            yield Static("Playback Queue", id="queue-title")
            yield QueueList()
        yield Footer()

    async def on_mount(self) -> None:
        """Load queue when screen mounts."""
        await self._load_queue()

    async def on_screen_resume(self) -> None:
        """Reload queue when returning to this screen."""
        await self._load_queue()

    async def _load_queue(self) -> None:
        """Load the queue from database."""
        app: FeedbackApp = self.app  # type: ignore[assignment]
        queue_items = await app.database.get_queue()

        # Fetch episode details for each queue item
        self._queue_items = []
        for item in queue_items:
            episode = await app.database.get_episode(item.episode_id)
            if episode:
                self._queue_items.append((item, episode))

        # Update the widget
        queue_list = self.query_one(QueueList)
        queue_list.set_queue(self._queue_items)

        if not self._queue_items:
            self.notify("Queue is empty", severity="information")

    async def _save_queue(self) -> None:
        """Save the current queue order to database."""
        app: FeedbackApp = self.app  # type: ignore[assignment]
        # Rebuild queue items with new positions
        new_items = [
            QueueItem(position=i + 1, episode_id=episode.id)
            for i, (_, episode) in enumerate(self._queue_items)
            if episode.id is not None
        ]
        await app.database.save_queue(new_items)

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

    async def action_play(self) -> None:
        """Play the selected queue item."""
        queue_list = self.query_one(QueueList)
        item = queue_list.get_selected_item()

        if item is None:
            self.notify("No item selected", severity="warning")
            return

        _queue_item, episode = item
        app: FeedbackApp = self.app  # type: ignore[assignment]

        # Play the episode
        await app.play_episode(episode)

        # Update player bar
        player_bar = self.query_one(PlayerBar)
        player_bar.set_playing(
            title=episode.title,
            duration_ms=app.player.duration_ms,
        )

        self.notify(f"Playing: {episode.title}")

    async def action_remove(self) -> None:
        """Remove the selected item from the queue."""
        queue_list = self.query_one(QueueList)
        item = queue_list.get_selected_item()

        if item is None:
            self.notify("No item selected", severity="warning")
            return

        queue_item, episode = item

        # Remove from local list
        self._queue_items = [
            (qi, ep) for qi, ep in self._queue_items if qi.episode_id != queue_item.episode_id
        ]

        # Save to database
        await self._save_queue()

        # Refresh display
        queue_list.set_queue(self._queue_items)

        self.notify(f"Removed: {episode.title}", severity="information")

    async def action_clear(self) -> None:
        """Clear the entire queue."""
        if not self._queue_items:
            self.notify("Queue is already empty", severity="information")
            return

        app: FeedbackApp = self.app  # type: ignore[assignment]
        await app.database.clear_queue()

        self._queue_items = []
        queue_list = self.query_one(QueueList)
        queue_list.set_queue([])

        self.notify("Queue cleared", severity="information")

    async def action_move_item_up(self) -> None:
        """Move the selected item up in the queue."""
        queue_list = self.query_one(QueueList)

        if queue_list.highlighted is None or queue_list.highlighted <= 0:
            return

        idx = queue_list.highlighted

        # Swap with previous item
        self._queue_items[idx], self._queue_items[idx - 1] = (
            self._queue_items[idx - 1],
            self._queue_items[idx],
        )

        # Save and refresh
        await self._save_queue()
        queue_list.set_queue(self._queue_items)
        queue_list.highlighted = idx - 1

        self.notify("Moved up")

    async def action_move_item_down(self) -> None:
        """Move the selected item down in the queue."""
        queue_list = self.query_one(QueueList)

        if (
            queue_list.highlighted is None
            or queue_list.highlighted >= len(self._queue_items) - 1
        ):
            return

        idx = queue_list.highlighted

        # Swap with next item
        self._queue_items[idx], self._queue_items[idx + 1] = (
            self._queue_items[idx + 1],
            self._queue_items[idx],
        )

        # Save and refresh
        await self._save_queue()
        queue_list.set_queue(self._queue_items)
        queue_list.highlighted = idx + 1

        self.notify("Moved down")

    async def action_play_pause(self) -> None:
        """Toggle play/pause."""
        app: FeedbackApp = self.app  # type: ignore[assignment]
        await app.toggle_play_pause()

        player_bar = self.query_one(PlayerBar)
        if app.player.state.name == "PLAYING":
            player_bar.status = "Playing"
            self.notify("Resumed playback")
        elif app.player.state.name == "PAUSED":
            player_bar.status = "Paused"
            self.notify("Paused playback")
        else:
            self.notify("No episode playing")

    async def on_queue_item_selected(self, event: QueueItemSelected) -> None:
        """Handle queue item selection (Enter key or click)."""
        app: FeedbackApp = self.app  # type: ignore[assignment]

        # Play the episode
        await app.play_episode(event.episode)

        # Update player bar
        player_bar = self.query_one(PlayerBar)
        player_bar.set_playing(
            title=event.episode.title,
            duration_ms=app.player.duration_ms,
        )

        self.notify(f"Playing: {event.episode.title}")
