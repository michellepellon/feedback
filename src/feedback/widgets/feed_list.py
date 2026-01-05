"""Feed list widget for displaying podcast feeds."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option

if TYPE_CHECKING:
    from feedback.models import Feed


class FeedSelected(Message):
    """Message sent when a feed is selected."""

    bubble = True  # Ensure message bubbles up to screen

    def __init__(self, feed: Feed) -> None:
        """Initialize the message.

        Args:
            feed: The selected feed.
        """
        self.feed = feed
        super().__init__()


class FeedList(OptionList):
    """Navigable list of podcast feeds."""

    DEFAULT_CSS = """
    FeedList {
        width: 1fr;
        height: 100%;
        border: solid $primary;
    }

    FeedList:focus {
        border: solid $accent;
    }

    FeedList > .option-list--option-highlighted {
        background: $accent;
    }
    """

    def __init__(self) -> None:
        """Initialize the feed list."""
        super().__init__()
        self._feeds: list[Feed] = []

    def set_feeds(self, feeds: list[Feed]) -> None:
        """Set the list of feeds to display.

        Args:
            feeds: List of Feed objects.
        """
        self._feeds = feeds
        self.clear_options()
        for feed in feeds:
            self.add_option(Option(feed.title, id=feed.key))

    def get_selected_feed(self) -> Feed | None:
        """Get the currently selected feed.

        Returns:
            The selected Feed or None.
        """
        if self.highlighted is None or not self._feeds:
            return None
        if 0 <= self.highlighted < len(self._feeds):
            return self._feeds[self.highlighted]
        return None

    def on_option_list_option_selected(self, _event: OptionList.OptionSelected) -> None:
        """Handle option selection (Enter key or double-click)."""
        feed = self.get_selected_feed()
        if feed:
            self.post_message(FeedSelected(feed))

    def on_option_list_option_highlighted(
        self, _event: OptionList.OptionHighlighted
    ) -> None:
        """Handle option highlight change (cursor movement)."""
        feed = self.get_selected_feed()
        if feed:
            self.post_message(FeedSelected(feed))
