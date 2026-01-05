"""Player bar widget showing playback status and controls."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Label, ProgressBar, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class PlayerBar(Static):
    """Playback status bar with progress indicator."""

    DEFAULT_CSS = """
    PlayerBar {
        height: 3;
        dock: top;
        background: $surface;
        padding: 0 1;
    }

    PlayerBar Horizontal {
        height: 1;
        width: 100%;
    }

    PlayerBar #player-title {
        width: 1fr;
        text-style: bold;
    }

    PlayerBar #player-status {
        width: auto;
        min-width: 10;
        text-align: right;
    }

    PlayerBar #player-time {
        width: auto;
        min-width: 20;
        text-align: right;
    }

    PlayerBar ProgressBar {
        width: 100%;
        height: 1;
        padding: 0;
    }

    PlayerBar ProgressBar Bar {
        width: 100%;
    }
    """

    # Reactive properties
    title: reactive[str] = reactive("No episode playing")
    status: reactive[str] = reactive("Stopped")
    position_ms: reactive[int] = reactive(0)
    duration_ms: reactive[int] = reactive(0)
    volume: reactive[int] = reactive(100)

    def compose(self) -> ComposeResult:
        """Compose the player bar layout."""
        with Horizontal():
            yield Label(self.title, id="player-title")
            yield Label(self.status, id="player-status")
            yield Label(self._format_time(), id="player-time")
        yield ProgressBar(total=100, show_eta=False, show_percentage=False)

    def watch_title(self, title: str) -> None:
        """Update the title label when title changes."""
        with contextlib.suppress(Exception):
            self.query_one("#player-title", Label).update(title)

    def watch_status(self, status: str) -> None:
        """Update the status label when status changes."""
        with contextlib.suppress(Exception):
            self.query_one("#player-status", Label).update(status)

    def watch_position_ms(self, _position: int) -> None:
        """Update progress when position changes."""
        self._update_progress()
        self._update_time()

    def watch_duration_ms(self, _duration: int) -> None:
        """Update progress when duration changes."""
        self._update_progress()
        self._update_time()

    def _update_progress(self) -> None:
        """Update the progress bar."""
        try:
            progress_bar = self.query_one(ProgressBar)
            if self.duration_ms > 0:
                progress = (self.position_ms / self.duration_ms) * 100
                progress_bar.update(progress=progress)
            else:
                progress_bar.update(progress=0)
        except Exception:
            pass

    def _update_time(self) -> None:
        """Update the time label."""
        with contextlib.suppress(Exception):
            self.query_one("#player-time", Label).update(self._format_time())

    def _format_time(self) -> str:
        """Format position/duration as time string."""
        pos = self._ms_to_time(self.position_ms)
        dur = self._ms_to_time(self.duration_ms)
        return f"{pos} / {dur}"

    @staticmethod
    def _ms_to_time(ms: int) -> str:
        """Convert milliseconds to HH:MM:SS format.

        Args:
            ms: Time in milliseconds.

        Returns:
            Formatted time string.
        """
        seconds = max(0, ms // 1000)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def set_playing(
        self,
        title: str,
        position_ms: int = 0,
        duration_ms: int = 0,
    ) -> None:
        """Set the player to playing state.

        Args:
            title: Episode title.
            position_ms: Current position in milliseconds.
            duration_ms: Total duration in milliseconds.
        """
        self.title = title
        self.status = "Playing"
        self.position_ms = position_ms
        self.duration_ms = duration_ms

    def set_paused(self) -> None:
        """Set the player to paused state."""
        self.status = "Paused"

    def set_stopped(self) -> None:
        """Set the player to stopped state."""
        self.title = "No episode playing"
        self.status = "Stopped"
        self.position_ms = 0
        self.duration_ms = 0
