"""Episode list widget for displaying podcast episodes."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option

if TYPE_CHECKING:
    from feedback.models import Episode


class EpisodeFilter(Enum):
    """Filter options for episode list."""

    ALL = "all"
    UNPLAYED = "unplayed"
    DOWNLOADED = "downloaded"
    IN_PROGRESS = "in_progress"


class EpisodeSort(Enum):
    """Sort options for episode list."""

    DATE_NEWEST = "date_newest"
    DATE_OLDEST = "date_oldest"
    TITLE = "title"


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


class EpisodeFilterChanged(Message):
    """Message sent when filter/sort changes."""

    bubble = True

    def __init__(self, filter_type: EpisodeFilter, sort_type: EpisodeSort) -> None:
        """Initialize the message.

        Args:
            filter_type: The new filter type.
            sort_type: The new sort type.
        """
        self.filter_type = filter_type
        self.sort_type = sort_type
        super().__init__()


class EpisodeList(OptionList):
    """Navigable list of podcast episodes with filtering and sorting."""

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
        self._all_episodes: list[Episode] = []
        self._filtered_episodes: list[Episode] = []
        self._filter: EpisodeFilter = EpisodeFilter.ALL
        self._sort: EpisodeSort = EpisodeSort.DATE_NEWEST

    @property
    def filter_type(self) -> EpisodeFilter:
        """Get the current filter type."""
        return self._filter

    @property
    def sort_type(self) -> EpisodeSort:
        """Get the current sort type."""
        return self._sort

    @property
    def total_count(self) -> int:
        """Get total number of episodes (before filtering)."""
        return len(self._all_episodes)

    @property
    def filtered_count(self) -> int:
        """Get number of episodes after filtering."""
        return len(self._filtered_episodes)

    def set_episodes(self, episodes: list[Episode]) -> None:
        """Set the list of episodes to display.

        Args:
            episodes: List of Episode objects.
        """
        self._all_episodes = episodes
        self._apply_filter_and_sort()

    def set_filter(self, filter_type: EpisodeFilter) -> None:
        """Set the filter type and refresh display.

        Args:
            filter_type: The filter to apply.
        """
        if self._filter != filter_type:
            self._filter = filter_type
            self._apply_filter_and_sort()
            self.post_message(EpisodeFilterChanged(self._filter, self._sort))

    def set_sort(self, sort_type: EpisodeSort) -> None:
        """Set the sort type and refresh display.

        Args:
            sort_type: The sort to apply.
        """
        if self._sort != sort_type:
            self._sort = sort_type
            self._apply_filter_and_sort()
            self.post_message(EpisodeFilterChanged(self._filter, self._sort))

    def cycle_filter(self) -> EpisodeFilter:
        """Cycle to the next filter type.

        Returns:
            The new filter type.
        """
        filters = list(EpisodeFilter)
        current_idx = filters.index(self._filter)
        next_idx = (current_idx + 1) % len(filters)
        self.set_filter(filters[next_idx])
        return self._filter

    def cycle_sort(self) -> EpisodeSort:
        """Cycle to the next sort type.

        Returns:
            The new sort type.
        """
        sorts = list(EpisodeSort)
        current_idx = sorts.index(self._sort)
        next_idx = (current_idx + 1) % len(sorts)
        self.set_sort(sorts[next_idx])
        return self._sort

    def _apply_filter_and_sort(self) -> None:
        """Apply current filter and sort, then update display."""
        # Apply filter
        if self._filter == EpisodeFilter.ALL:
            filtered = self._all_episodes
        elif self._filter == EpisodeFilter.UNPLAYED:
            filtered = [ep for ep in self._all_episodes if not ep.played]
        elif self._filter == EpisodeFilter.DOWNLOADED:
            filtered = [ep for ep in self._all_episodes if ep.downloaded_path]
        elif self._filter == EpisodeFilter.IN_PROGRESS:
            filtered = [
                ep for ep in self._all_episodes if ep.progress_ms > 0 and not ep.played
            ]
        else:
            filtered = self._all_episodes

        # Apply sort
        if self._sort == EpisodeSort.DATE_NEWEST:
            # Sort by pubdate descending (newest first), None dates at end
            filtered = sorted(
                filtered,
                key=lambda ep: (ep.pubdate is None, ep.pubdate),
                reverse=True,
            )
        elif self._sort == EpisodeSort.DATE_OLDEST:
            # Sort by pubdate ascending (oldest first), None dates at end
            filtered = sorted(
                filtered,
                key=lambda ep: (ep.pubdate is None, ep.pubdate or ""),
            )
        elif self._sort == EpisodeSort.TITLE:
            filtered = sorted(filtered, key=lambda ep: ep.title.lower())

        self._filtered_episodes = filtered
        self._update_display()

    def _update_display(self) -> None:
        """Update the option list display."""
        self.clear_options()
        for episode in self._filtered_episodes:
            # Format the display title with status indicators
            parts = []

            if episode.played:
                parts.append("[played]")
            elif episode.progress_ms > 0:
                parts.append("[▶]")  # In progress indicator

            if episode.downloaded_path:
                parts.append("[↓]")  # Downloaded indicator

            prefix = " ".join(parts)
            if prefix:
                prefix += " "

            title = f"{prefix}{episode.title}"
            self.add_option(Option(title, id=str(episode.id)))

    def get_selected_episode(self) -> Episode | None:
        """Get the currently selected episode.

        Returns:
            The selected Episode or None.
        """
        if self.highlighted is None or not self._filtered_episodes:
            return None
        if 0 <= self.highlighted < len(self._filtered_episodes):
            return self._filtered_episodes[self.highlighted]
        return None

    def on_option_list_option_selected(self, _event: OptionList.OptionSelected) -> None:
        """Handle option selection."""
        episode = self.get_selected_episode()
        if episode:
            self.post_message(EpisodeSelected(episode))

    def get_filter_label(self) -> str:
        """Get a human-readable label for the current filter.

        Returns:
            Filter label string.
        """
        labels = {
            EpisodeFilter.ALL: "All",
            EpisodeFilter.UNPLAYED: "Unplayed",
            EpisodeFilter.DOWNLOADED: "Downloaded",
            EpisodeFilter.IN_PROGRESS: "In Progress",
        }
        return labels.get(self._filter, "All")

    def get_sort_label(self) -> str:
        """Get a human-readable label for the current sort.

        Returns:
            Sort label string.
        """
        labels = {
            EpisodeSort.DATE_NEWEST: "Newest",
            EpisodeSort.DATE_OLDEST: "Oldest",
            EpisodeSort.TITLE: "Title",
        }
        return labels.get(self._sort, "Newest")
