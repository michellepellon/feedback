"""History screen for viewing recently played episodes."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, OptionList, Static
from textual.widgets.option_list import Option

from feedback.widgets.player_bar import PlayerBar

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from feedback.app import FeedbackApp
    from feedback.models import Episode, HistoryItem


class HistoryList(OptionList):
    """List widget for playback history."""

    DEFAULT_CSS = """
    HistoryList {
        height: 1fr;
        border: solid $primary;
    }
    """

    def __init__(self) -> None:
        """Initialize the history list."""
        super().__init__()
        self._history: list[tuple[HistoryItem, Episode]] = []

    def set_history(self, history: list[tuple[HistoryItem, Episode]]) -> None:
        """Set the history items to display.

        Args:
            history: List of (HistoryItem, Episode) tuples.
        """
        self._history = history
        self.clear_options()

        for hist_item, episode in history:
            # Format played time
            played_str = hist_item.played_at.strftime("%Y-%m-%d %H:%M")

            # Format duration listened
            if hist_item.duration_listened_ms > 0:
                minutes = hist_item.duration_listened_ms // 60000
                duration_str = f"({minutes}m listened)"
            else:
                duration_str = ""

            label = f"{episode.title}\n  [dim]{played_str} {duration_str}[/dim]"
            self.add_option(Option(label, id=f"history-{hist_item.id}"))

    def get_selected_episode(self) -> Episode | None:
        """Get the currently selected episode.

        Returns:
            Selected Episode or None.
        """
        if self.highlighted is None or self.highlighted >= len(self._history):
            return None
        return self._history[self.highlighted][1]

    def get_selected_item(self) -> tuple[HistoryItem, Episode] | None:
        """Get the currently selected history item with episode.

        Returns:
            Tuple of (HistoryItem, Episode) or None.
        """
        if self.highlighted is None or self.highlighted >= len(self._history):
            return None
        return self._history[self.highlighted]


class HistoryScreen(Screen[None]):
    """Screen for viewing playback history."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("j", "move_down", "Down", show=False),
        Binding("k", "move_up", "Up", show=False),
        Binding("enter", "play", "Play"),
        Binding("c", "clear_history", "Clear History"),
        Binding("p", "play_pause", "Play/Pause"),
        Binding("space", "play_pause", "Play/Pause", show=False),
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the history screen layout."""
        yield Header()
        yield PlayerBar()
        with Vertical(id="history-content"):
            yield Static("Playback History", id="history-title")
            yield HistoryList()
        yield Footer()

    async def on_mount(self) -> None:
        """Load history when screen mounts."""
        await self._load_history()

    async def on_screen_resume(self) -> None:
        """Reload history when returning to this screen."""
        await self._load_history()

    async def _load_history(self) -> None:
        """Load history from database."""
        app: FeedbackApp = self.app  # type: ignore[assignment]
        history = await app.database.get_history(limit=50)

        history_list = self.query_one(HistoryList)
        history_list.set_history(history)

        if not history:
            self.notify("No playback history", severity="information")

    def action_move_down(self) -> None:
        """Move selection down."""
        try:
            history_list = self.query_one(HistoryList)
            history_list.action_cursor_down()
        except Exception:
            pass

    def action_move_up(self) -> None:
        """Move selection up."""
        try:
            history_list = self.query_one(HistoryList)
            history_list.action_cursor_up()
        except Exception:
            pass

    async def action_play(self) -> None:
        """Play the selected episode from history."""
        history_list = self.query_one(HistoryList)
        episode = history_list.get_selected_episode()

        if episode is None:
            self.notify("No episode selected", severity="warning")
            return

        app: FeedbackApp = self.app  # type: ignore[assignment]
        await app.play_episode(episode)

        player_bar = self.query_one(PlayerBar)
        player_bar.set_playing(
            title=episode.title,
            duration_ms=app.player.duration_ms,
        )
        self.notify(f"Playing: {episode.title}")

    async def action_clear_history(self) -> None:
        """Clear all playback history."""
        from feedback.widgets.confirm_dialog import ConfirmDialog

        history_list = self.query_one(HistoryList)
        if not history_list._history:
            self.notify("History is already empty", severity="information")
            return

        confirmed = await self.app.push_screen_wait(
            ConfirmDialog(
                title="Clear History",
                message=f"Clear all {len(history_list._history)} history items?",
                confirm_label="Clear",
                cancel_label="Cancel",
            )
        )

        if not confirmed:
            return

        app: FeedbackApp = self.app  # type: ignore[assignment]
        count = await app.database.clear_history()
        await self._load_history()
        self.notify(f"Cleared {count} history items", severity="information")

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

    def action_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()
