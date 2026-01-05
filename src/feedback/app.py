"""Main Textual application for feedback."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import App
from textual.binding import Binding

from feedback.config import get_config, get_data_path
from feedback.database import Database
from feedback.downloads import DownloadItem, DownloadQueue
from feedback.logging import get_logger, setup_logging
from feedback.models import Episode, Feed  # noqa: TC001 - used at runtime
from feedback.player.base import NullPlayer, PlayerState
from feedback.screens.downloads import DownloadsScreen
from feedback.screens.help import HelpScreen
from feedback.screens.history import HistoryScreen
from feedback.screens.primary import PrimaryScreen
from feedback.screens.queue import QueueScreen
from feedback.screens.settings import SettingsScreen
from feedback.sleep_timer import SleepTimer

if TYPE_CHECKING:
    from collections.abc import Callable

    from textual.screen import Screen

    from feedback.player.base import BasePlayer

# Module logger
_log = get_logger("app")


class FeedbackApp(App[None]):
    """A modern TUI podcast client."""

    TITLE = "Feedback"
    CSS_PATH = "styles/app.tcss"

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("?", "toggle_help", "Help"),
        Binding("ctrl+comma", "open_settings", "Settings", show=False),
        Binding("1", "switch_screen('primary')", "Feeds", show=False),
        Binding("2", "switch_screen('queue')", "Queue", show=False),
        Binding("3", "switch_screen('downloads')", "Downloads", show=False),
        Binding("4", "switch_screen('history')", "History", show=False),
    ]

    SCREENS: ClassVar[dict[str, Callable[[], Screen[Any]]]] = {
        "primary": PrimaryScreen,
        "queue": QueueScreen,
        "downloads": DownloadsScreen,
        "history": HistoryScreen,
    }

    def __init__(self) -> None:
        """Initialize the application."""
        super().__init__()
        self._config = get_config()
        self._db: Database | None = None
        self._player: BasePlayer = self._create_player()
        self._current_episode: Episode | None = None
        self._feeds: list[Feed] = []
        self._download_queue: DownloadQueue | None = None
        self._sleep_timer = SleepTimer(on_expire=self._on_sleep_timer_expire)

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

    @property
    def download_queue(self) -> DownloadQueue:
        """Get the download queue instance."""
        if self._download_queue is None:
            raise RuntimeError("Download queue not initialized")
        return self._download_queue

    @property
    def sleep_timer(self) -> SleepTimer:
        """Get the sleep timer instance."""
        return self._sleep_timer

    def _on_sleep_timer_expire(self) -> None:
        """Handle sleep timer expiration."""
        _log.info("Sleep timer expired, stopping playback")
        # Schedule the stop on the event loop
        self.call_later(self._stop_for_sleep)

    async def _stop_for_sleep(self) -> None:
        """Stop playback when sleep timer expires."""
        if self._player.state != PlayerState.STOPPED:
            await self._player.pause()
            self.notify("Sleep timer: Playback paused", severity="information")

    async def on_mount(self) -> None:
        """Set up the application on mount."""
        # Initialize logging
        setup_logging(log_to_file=True)
        _log.info("Feedback starting up")

        # Initialize database
        db_path = get_data_path() / "feedback.db"
        self._db = Database(db_path)
        await self._db.connect()
        _log.info("Database connected: %s", db_path)

        # Initialize download queue
        download_dir = get_data_path() / "downloads"
        self._download_queue = DownloadQueue(
            download_dir=download_dir,
            max_concurrent=self._config.download.concurrent,
        )
        _log.info("Download queue initialized: %s", download_dir)

        # Load feeds
        await self.refresh_feeds()
        _log.info("Loaded %d feeds", len(self._feeds))

        # Push initial screen
        self.push_screen("primary")

    async def on_unmount(self) -> None:
        """Clean up resources on unmount."""
        _log.info("Feedback shutting down")
        if self._player.state != PlayerState.STOPPED:
            await self._player.stop()
        if self._db is not None:
            await self._db.close()
        _log.info("Shutdown complete")

    async def refresh_feeds(self) -> None:
        """Refresh the list of feeds from the database."""
        if self._db is not None:
            self._feeds = await self._db.get_feeds()

    async def refresh_feeds_from_sources(
        self,
        *,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> tuple[int, int, list[str]]:
        """Refresh all feeds by fetching from their sources.

        Args:
            progress_callback: Optional callback(current, total, title) for progress.

        Returns:
            Tuple of (success_count, fail_count, list of errors).
        """
        from feedback.feeds import FeedError, FeedFetcher

        if self._db is None:
            return 0, 0, ["Database not initialized"]

        feeds = await self._db.get_feeds()
        total = len(feeds)
        success = 0
        errors: list[str] = []

        fetcher = FeedFetcher(
            timeout=self._config.network.timeout,
            max_episodes=self._config.network.max_episodes,
        )

        for i, feed in enumerate(feeds, 1):
            if progress_callback:
                progress_callback(i, total, feed.title)

            try:
                _log.debug("Refreshing feed: %s", feed.key)
                updated_feed, episodes = await fetcher.fetch(feed.key)
                await self._db.upsert_feed(updated_feed)
                await self._db.upsert_episodes(episodes)
                success += 1
                _log.info("Refreshed feed: %s (%d episodes)", feed.title, len(episodes))
            except FeedError as e:
                _log.warning("Failed to refresh feed %s: %s", feed.title, e)
                errors.append(f"{feed.title}: {e}")
            except Exception as e:
                _log.exception("Unexpected error refreshing feed %s", feed.title)
                errors.append(f"{feed.title}: {e}")

        # Reload feeds list
        self._feeds = await self._db.get_feeds()

        return success, total - success, errors

    async def add_feed(self, url: str, *, check_duplicate: bool = True) -> bool:
        """Add a new feed.

        Args:
            url: The feed URL.
            check_duplicate: If True, warn if feed already exists.

        Returns:
            True if successful, False otherwise.
        """
        from feedback.feeds import FeedError, FeedFetcher

        # Check for duplicate
        if check_duplicate:
            existing = await self.database.get_feed(url)
            if existing:
                self.notify(
                    f"Feed already exists: {existing.title}",
                    severity="warning",
                )
                return False

        try:
            _log.info("Adding new feed: %s", url)
            fetcher = FeedFetcher(
                timeout=self._config.network.timeout,
                max_episodes=self._config.network.max_episodes,
            )
            feed, episodes = await fetcher.fetch(url)

            # Double-check for duplicate by feed key (URL might redirect)
            if check_duplicate:
                existing = await self.database.get_feed(feed.key)
                if existing:
                    _log.info("Feed already exists: %s", existing.title)
                    self.notify(
                        f"Feed already exists: {existing.title}",
                        severity="warning",
                    )
                    return False

            await self.database.upsert_feed(feed)
            await self.database.upsert_episodes(episodes)
            await self.refresh_feeds()
            _log.info("Added feed: %s (%d episodes)", feed.title, len(episodes))
            return True
        except FeedError as e:
            _log.warning("Failed to add feed %s: %s", url, e)
            self.notify(f"Error adding feed: {e}", severity="error")
            return False
        except Exception as e:
            _log.exception("Unexpected error adding feed %s", url)
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

        # Record to playback history
        if episode.id is not None:
            await self.database.add_to_history(episode.id)
            _log.debug("Added episode to playback history: %s", episode.title)

    async def toggle_play_pause(self) -> None:
        """Toggle play/pause for current playback."""
        if self._player.state == PlayerState.PLAYING:
            await self._player.pause()
        elif self._player.state == PlayerState.PAUSED:
            await self._player.resume()

    async def download_episode(self, episode: Episode) -> DownloadItem | None:
        """Download an episode.

        Args:
            episode: The episode to download.

        Returns:
            DownloadItem if download started, None if already downloaded.
        """
        if episode.downloaded_path:
            self.notify("Episode already downloaded", severity="information")
            return None

        # Generate filename from episode title
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in episode.title)
        ext = episode.enclosure.split(".")[-1].split("?")[0][:4] or "mp3"
        filename = f"{safe_title[:50]}.{ext}"

        item = await self.download_queue.add(
            url=episode.enclosure,
            filename=filename,
            episode_id=episode.id,
        )

        return item

    async def add_to_queue(self, episode: Episode) -> bool:
        """Add an episode to the playback queue.

        Args:
            episode: The episode to add.

        Returns:
            True if added successfully.
        """
        if episode.id is None:
            return False

        from feedback.models import QueueItem

        # Get current queue to determine position
        queue = await self.database.get_queue()
        position = len(queue) + 1

        new_item = QueueItem(position=position, episode_id=episode.id)
        await self.database.save_queue([*queue, new_item])

        return True

    def action_toggle_help(self) -> None:
        """Toggle the help overlay."""
        self.push_screen(HelpScreen())

    def action_open_settings(self) -> None:
        """Open the settings screen."""
        self.push_screen(SettingsScreen())

    async def action_switch_screen(self, screen_name: str) -> None:
        """Switch to a named screen.

        Args:
            screen_name: Name of the screen to switch to.
        """
        if screen_name in self.SCREENS:
            self.switch_screen(screen_name)
