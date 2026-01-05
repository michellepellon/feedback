"""Queue list widget for displaying the playback queue."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option

if TYPE_CHECKING:
    from feedback.models import Episode, QueueItem


class QueueItemSelected(Message):
    """Message sent when a queue item is selected."""

    bubble = True  # Ensure message bubbles up to screen

    def __init__(self, queue_item: QueueItem, episode: Episode) -> None:
        """Initialize the message.

        Args:
            queue_item: The selected queue item.
            episode: The associated episode.
        """
        self.queue_item = queue_item
        self.episode = episode
        super().__init__()


class QueueList(OptionList):
    """Navigable list of queued episodes."""

    DEFAULT_CSS = """
    QueueList {
        width: 100%;
        height: 1fr;
        border: solid $primary;
    }

    QueueList:focus {
        border: solid $accent;
    }

    QueueList > .option-list--option-highlighted {
        background: $accent;
    }
    """

    def __init__(self) -> None:
        """Initialize the queue list."""
        super().__init__()
        self._items: list[tuple[QueueItem, Episode]] = []

    def set_queue(self, items: list[tuple[QueueItem, Episode]]) -> None:
        """Set the queue items to display.

        Args:
            items: List of (QueueItem, Episode) tuples.
        """
        self._items = items
        self.clear_options()
        for i, (queue_item, episode) in enumerate(items, 1):
            title = f"{i}. {episode.title}"
            self.add_option(Option(title, id=str(queue_item.episode_id)))

    def get_selected_item(self) -> tuple[QueueItem, Episode] | None:
        """Get the currently selected queue item.

        Returns:
            Tuple of (QueueItem, Episode) or None.
        """
        if self.highlighted is None or not self._items:
            return None
        if 0 <= self.highlighted < len(self._items):
            return self._items[self.highlighted]
        return None

    def on_option_list_option_selected(self, _event: OptionList.OptionSelected) -> None:
        """Handle option selection."""
        item = self.get_selected_item()
        if item:
            queue_item, episode = item
            self.post_message(QueueItemSelected(queue_item, episode))
