"""Main Textual application for feedback."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import App
from textual.binding import Binding

from feedback.config import get_config, get_data_path
from feedback.database import Database
from feedback.models import Episode, Feed  # noqa: TC001 - used at runtime
from feedback.player.base import NullPlayer, PlayerState
from feedback.screens.downloads import DownloadsScreen
from feedback.screens.primary import PrimaryScreen
from feedback.screens.queue import QueueScreen

if TYPE_CHECKING:
    from collections.abc import Callable

    from textual.screen import Screen

    from feedback.player.base import BasePlayer


class FeedbackApp(App[None]):
    """A modern TUI podcast client."""

    TITLE = "Feedback"
    CSS_PATH = "styles/app.tcss"

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("?", "toggle_help", "Help"),
        Binding("1", "switch_screen('primary')", "Feeds", show=False),
        Binding("2", "switch_screen('queue')", "Queue", show=False),
        Binding("3", "switch_screen('downloads')", "Downloads", show=False),
    ]

    SCREENS: ClassVar[dict[str, Callable[[], Screen[Any]]]] = {
        "primary": PrimaryScreen,
        "queue": QueueScreen,
        "downloads": DownloadsScreen,
    }

    def __init__(self) -> None:
        """Initialize the application."""
        super().__init__()
        self._config = get_config()
        self._db: Database | None = None
        self._player: BasePlayer = self._create_player()
        self._current_episode: Episode | None = None
        self._feeds: list[Feed] = []

    def _create_player(self) -> BasePlayer:
        """Create the appropriate player based on config.

        Returns:
            Player instance (VLC, MPV, or NullPlayer as fallback).
        """
        backend = self._config.player.backend.lower()

        if backend == "vlc":
            try:
                from feedback.player.vlc import VLCPlayer

                return VLCPlayer()
            except ImportError:
                self.notify("VLC not available, using null player", severity="warning")
                return NullPlayer()
        elif backend == "mpv":
            try:
                from feedback.player.mpv import MPVPlayer

                return MPVPlayer()
            except ImportError:
                self.notify("MPV not available, using null player", severity="warning")
                return NullPlayer()
        else:
            return NullPlayer()

    @property
    def database(self) -> Database:
        """Get the database instance."""
        if self._db is None:
            raise RuntimeError("Database not initialized")
        return self._db

    @property
    def player(self) -> BasePlayer:
        """Get the player instance."""
        return self._player

    @property
    def current_episode(self) -> Episode | None:
        """Get the currently playing episode."""
        return self._current_episode

    @property
    def feeds(self) -> list[Feed]:
        """Get the list of feeds."""
        return self._feeds

    async def on_mount(self) -> None:
        """Set up the application on mount."""
        # Initialize database
        db_path = get_data_path() / "feedback.db"
        self._db = Database(db_path)
        await self._db.connect()

        # Load feeds
        await self.refresh_feeds()

        # Push initial screen
        self.push_screen("primary")

    async def on_unmount(self) -> None:
        """Clean up resources on unmount."""
        if self._player.state != PlayerState.STOPPED:
            await self._player.stop()
        if self._db is not None:
            await self._db.close()

    async def refresh_feeds(self) -> None:
        """Refresh the list of feeds from the database."""
        if self._db is not None:
            self._feeds = await self._db.get_feeds()

    async def add_feed(self, url: str) -> bool:
        """Add a new feed.

        Args:
            url: The feed URL.

        Returns:
            True if successful, False otherwise.
        """
        from feedback.feeds import FeedError, FeedFetcher

        try:
            fetcher = FeedFetcher(
                timeout=self._config.network.timeout,
                max_episodes=self._config.network.max_episodes,
            )
            feed, episodes = await fetcher.fetch(url)
            await self.database.upsert_feed(feed)
            await self.database.upsert_episodes(episodes)
            await self.refresh_feeds()
            return True
        except FeedError as e:
            self.notify(f"Error adding feed: {e}", severity="error")
            return False
        except Exception as e:
            self.notify(f"Unexpected error: {e}", severity="error")
            return False

    async def delete_feed(self, feed_key: str) -> None:
        """Delete a feed.

        Args:
            feed_key: The feed key (URL) to delete.
        """
        await self.database.delete_feed(feed_key)
        await self.refresh_feeds()

    async def play_episode(self, episode: Episode) -> None:
        """Play an episode.

        Args:
            episode: The episode to play.
        """
        # Stop current playback if any
        if self._player.state != PlayerState.STOPPED:
            await self._player.stop()

        # Get the feed to check for start position
        feed = await self.database.get_feed(episode.feed_key)
        start_ms = episode.progress_ms

        # If episode hasn't been started, use feed's default start position
        if start_ms == 0 and feed is not None:
            start_ms = feed.start_position_ms

        # Determine media path (downloaded or streaming)
        media_path = episode.downloaded_path or episode.enclosure

        # Start playback
        await self._player.play(media_path, start_ms=start_ms)
        self._current_episode = episode

    async def toggle_play_pause(self) -> None:
        """Toggle play/pause for current playback."""
        if self._player.state == PlayerState.PLAYING:
            await self._player.pause()
        elif self._player.state == PlayerState.PAUSED:
            await self._player.resume()

    def action_toggle_help(self) -> None:
        """Toggle the help overlay."""
        self.notify("Help: Press 1-3 to switch screens, q to quit")

    async def action_switch_screen(self, screen_name: str) -> None:
        """Switch to a named screen.

        Args:
            screen_name: Name of the screen to switch to.
        """
        if screen_name in self.SCREENS:
            self.switch_screen(screen_name)
