"""Episode list widget for displaying podcast episodes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option

if TYPE_CHECKING:
    from feedback.models import Episode


class EpisodeSelected(Message):
    """Message sent when an episode is selected."""

    bubble = True  # Ensure message bubbles up to screen

    def __init__(self, episode: Episode) -> None:
        """Initialize the message.

        Args:
            episode: The selected episode.
        """
        self.episode = episode
        super().__init__()


class EpisodeList(OptionList):
    """Navigable list of podcast episodes."""

    DEFAULT_CSS = """
    EpisodeList {
        width: 1fr;
        height: 2fr;
        border: solid $primary;
    }

    EpisodeList:focus {
        border: solid $accent;
    }

    EpisodeList > .option-list--option-highlighted {
        background: $accent;
    }

    EpisodeList > .option-list--option.played {
        color: $text-muted;
    }
    """

    def __init__(self) -> None:
        """Initialize the episode list."""
        super().__init__()
        self._episodes: list[Episode] = []

    def set_episodes(self, episodes: list[Episode]) -> None:
        """Set the list of episodes to display.

        Args:
            episodes: List of Episode objects.
        """
        self._episodes = episodes
        self.clear_options()
        for episode in episodes:
            # Format the display title
            prefix = "[played] " if episode.played else ""
            title = f"{prefix}{episode.title}"
            self.add_option(Option(title, id=str(episode.id)))

    def get_selected_episode(self) -> Episode | None:
        """Get the currently selected episode.

        Returns:
            The selected Episode or None.
        """
        if self.highlighted is None or not self._episodes:
            return None
        if 0 <= self.highlighted < len(self._episodes):
            return self._episodes[self.highlighted]
        return None

    def on_option_list_option_selected(self, _event: OptionList.OptionSelected) -> None:
        """Handle option selection."""
        episode = self.get_selected_episode()
        if episode:
            self.post_message(EpisodeSelected(episode))
