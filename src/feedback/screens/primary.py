"""Primary screen with feeds and episodes."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Static

from feedback.widgets.episode_list import EpisodeList, EpisodeSelected
from feedback.widgets.feed_list import FeedList, FeedSelected
from feedback.widgets.player_bar import PlayerBar

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from feedback.app import FeedbackApp


class MetadataPanel(Static):
    """Panel displaying episode metadata."""

    DEFAULT_CSS = """
    MetadataPanel {
        width: 1fr;
        height: 1fr;
        padding: 1;
        border: solid $primary;
    }
    """

    def __init__(self) -> None:
        """Initialize the metadata panel."""
        super().__init__("Select an episode to view details")

    def show_episode(self, title: str, description: str | None) -> None:
        """Display episode metadata.

        Args:
            title: The episode title.
            description: The episode description.
        """
        content = f"[bold]{title}[/bold]\n\n{description or 'No description available'}"
        self.update(content)


class AddFeedInput(Input):
    """Input widget for adding a new feed URL."""

    DEFAULT_CSS = """
    AddFeedInput {
        dock: bottom;
        width: 100%;
        margin: 1;
    }
    """

    def __init__(self) -> None:
        """Initialize the add feed input."""
        super().__init__(placeholder="Enter feed URL and press Enter...")


class SearchInput(Input):
    """Input widget for searching podcasts."""

    DEFAULT_CSS = """
    SearchInput {
        dock: bottom;
        width: 100%;
        margin: 1;
    }
    """

    def __init__(self) -> None:
        """Initialize the search input."""
        super().__init__(placeholder="Search podcasts (requires API key in config)...")


class PrimaryScreen(Screen[None]):
    """Primary screen with three-pane layout: feeds, episodes, metadata."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("j", "move_down", "Down", show=False),
        Binding("k", "move_up", "Up", show=False),
        Binding("enter", "select", "Select", show=False),
        Binding("tab", "focus_next", "Next Pane", show=False),
        Binding("shift+tab", "focus_previous", "Prev Pane", show=False),
        Binding("r", "refresh", "Refresh"),
        Binding("a", "add_feed", "Add Feed"),
        Binding("d", "delete", "Delete"),
        Binding("p", "play_pause", "Play/Pause"),
        Binding("space", "play_pause", "Play/Pause", show=False),
        Binding("S", "search_podcasts", "Search"),
        Binding("m", "mark_played", "Mark Played"),
        Binding("u", "mark_unplayed", "Mark Unplayed"),
        Binding("Q", "add_to_queue", "Add to Queue"),
        Binding("D", "download_episode", "Download"),
        Binding("f", "seek_forward", "Seek +30s", show=False),
        Binding("b", "seek_backward", "Seek -10s", show=False),
        Binding("+", "volume_up", "Vol+", show=False),
        Binding("-", "volume_down", "Vol-", show=False),
        Binding("]", "speed_up", "Speed+", show=False),
        Binding("[", "speed_down", "Speed-", show=False),
    ]

    # Progress save interval in seconds
    PROGRESS_SAVE_INTERVAL = 30.0
    # Mark as played when this percentage is reached
    PLAYED_THRESHOLD = 0.90

    def __init__(self) -> None:
        """Initialize the primary screen."""
        super().__init__()
        self._adding_feed = False
        self._searching = False
        self._selected_feed_key: str | None = None
        self._player_timer = None
        self._progress_timer = None
        self._last_saved_position = 0

    def compose(self) -> ComposeResult:
        """Compose the primary screen layout."""
        yield Header()
        yield PlayerBar()
        with Horizontal(id="main-content"):
            with Vertical(id="left-pane"):
                yield FeedList()
            with Vertical(id="right-pane"):
                yield EpisodeList()
                yield MetadataPanel()
        yield Footer()

    async def on_mount(self) -> None:
        """Load feeds when screen mounts."""
        await self._load_feeds()
        # Start the player update timer (fast for UI)
        self._player_timer = self.set_interval(0.5, self._update_player_bar)
        # Start the progress save timer (slower for database)
        self._progress_timer = self.set_interval(
            self.PROGRESS_SAVE_INTERVAL, self._save_progress
        )

    async def _update_player_bar(self) -> None:
        """Update the player bar with current playback position."""
        app: FeedbackApp = self.app  # type: ignore[assignment]
        player_bar = self.query_one(PlayerBar)

        if app.player.state.name == "PLAYING":
            player_bar.position_ms = app.player.position_ms
            player_bar.duration_ms = app.player.duration_ms
            player_bar.status = "Playing"

            # Check if we should mark as played
            if app.player.duration_ms > 0:
                progress = app.player.position_ms / app.player.duration_ms
                if progress >= self.PLAYED_THRESHOLD and app.current_episode:
                    episode = app.current_episode
                    if not episode.played and episode.id is not None:
                        await app.database.mark_played(episode.id)
                        episode.played = True

        elif app.player.state.name == "PAUSED":
            player_bar.position_ms = app.player.position_ms
            player_bar.status = "Paused"
        elif app.player.state.name == "STOPPED":
            # Save final progress when stopped
            await self._save_progress()

    async def _save_progress(self) -> None:
        """Save current playback progress to database."""
        app: FeedbackApp = self.app  # type: ignore[assignment]

        if app.current_episode is None or app.current_episode.id is None:
            return

        if app.player.state.name not in ("PLAYING", "PAUSED"):
            return

        position_ms = app.player.position_ms

        # Only save if position changed significantly (>5 seconds)
        if abs(position_ms - self._last_saved_position) > 5000:
            await app.database.update_progress(app.current_episode.id, position_ms)
            self._last_saved_position = position_ms

    async def _load_feeds(self) -> None:
        """Load feeds from the database."""
        app: FeedbackApp = self.app  # type: ignore[assignment]
        feed_list = self.query_one(FeedList)
        feed_list.set_feeds(app.feeds)

        # Auto-select first feed and load its episodes
        if app.feeds:
            first_feed = app.feeds[0]
            self._selected_feed_key = first_feed.key
            # Highlight the first feed in the list
            feed_list.highlighted = 0
            await self._load_episodes(first_feed.key)

    async def _load_episodes(self, feed_key: str) -> None:
        """Load episodes for a feed."""
        app: FeedbackApp = self.app  # type: ignore[assignment]
        episodes = await app.database.get_episodes(feed_key)
        episode_list = self.query_one(EpisodeList)
        episode_list.set_episodes(episodes)

    async def on_feed_selected(self, event: FeedSelected) -> None:
        """Handle feed selection."""
        self._selected_feed_key = event.feed.key
        await self._load_episodes(event.feed.key)
        self.notify(f"Selected: {event.feed.title}")

    async def on_episode_selected(self, event: EpisodeSelected) -> None:
        """Handle episode selection - start playback."""
        app: FeedbackApp = self.app  # type: ignore[assignment]

        # Save progress of previous episode before switching
        await self._save_progress()

        metadata_panel = self.query_one(MetadataPanel)
        metadata_panel.show_episode(event.episode.title, event.episode.description)
        await app.play_episode(event.episode)

        # Reset last saved position for new episode
        self._last_saved_position = event.episode.progress_ms

        # Update the player bar
        player_bar = self.query_one(PlayerBar)
        player_bar.set_playing(
            title=event.episode.title,
            duration_ms=app.player.duration_ms,
        )
        self.notify(f"Playing: {event.episode.title}")

    def action_move_down(self) -> None:
        """Move selection down in the focused list."""
        focused = self.focused
        if focused is not None and hasattr(focused, "action_cursor_down"):
            focused.action_cursor_down()

    def action_move_up(self) -> None:
        """Move selection up in the focused list."""
        focused = self.focused
        if focused is not None and hasattr(focused, "action_cursor_up"):
            focused.action_cursor_up()

    def action_select(self) -> None:
        """Select the current item."""
        focused = self.focused
        if focused is not None:
            # OptionList uses action_select, not action_select_cursor
            if hasattr(focused, "action_select"):
                focused.action_select()
            elif hasattr(focused, "action_select_cursor"):
                focused.action_select_cursor()

    async def action_refresh(self) -> None:
        """Refresh all feeds from their sources."""
        app: FeedbackApp = self.app  # type: ignore[assignment]
        self.notify("Refreshing feeds...")
        await app.refresh_feeds()
        await self._load_feeds()
        self.notify("Feeds refreshed", severity="information")

    def action_add_feed(self) -> None:
        """Add a new feed.

        Shows an input field to enter the feed URL.
        """
        if self._adding_feed:
            return

        self._adding_feed = True
        input_widget = AddFeedInput()
        self.mount(input_widget)
        input_widget.focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission (add feed or search)."""
        value = event.value.strip()
        is_search = isinstance(event.input, SearchInput)
        event.input.remove()

        if is_search:
            self._searching = False
            if value:
                await self._perform_search(value)
        else:
            self._adding_feed = False
            if not value:
                return

            url = value
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"

            app: FeedbackApp = self.app  # type: ignore[assignment]
            self.notify(f"Adding feed: {url}...")

            if await app.add_feed(url):
                await self._load_feeds()
                self.notify("Feed added successfully", severity="information")

    async def action_delete(self) -> None:
        """Delete the selected feed."""
        feed_list = self.query_one(FeedList)
        selected_feed = feed_list.get_selected_feed()

        if selected_feed is None:
            self.notify("No feed selected", severity="warning")
            return

        app: FeedbackApp = self.app  # type: ignore[assignment]
        await app.delete_feed(selected_feed.key)
        await self._load_feeds()
        self.notify(f"Deleted: {selected_feed.title}", severity="information")

    async def action_play_pause(self) -> None:
        """Toggle play/pause for current playback."""
        app: FeedbackApp = self.app  # type: ignore[assignment]

        # Save progress before pausing
        if app.player.state.name == "PLAYING":
            await self._save_progress()

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

    async def action_mark_played(self) -> None:
        """Mark the selected episode as played."""
        episode_list = self.query_one(EpisodeList)
        episode = episode_list.get_selected_episode()

        if episode is None or episode.id is None:
            self.notify("No episode selected", severity="warning")
            return

        app: FeedbackApp = self.app  # type: ignore[assignment]
        await app.database.mark_played(episode.id, played=True)

        # Refresh episode list
        if self._selected_feed_key:
            await self._load_episodes(self._selected_feed_key)

        self.notify(f"Marked as played: {episode.title}", severity="information")

    async def action_mark_unplayed(self) -> None:
        """Mark the selected episode as unplayed."""
        episode_list = self.query_one(EpisodeList)
        episode = episode_list.get_selected_episode()

        if episode is None or episode.id is None:
            self.notify("No episode selected", severity="warning")
            return

        app: FeedbackApp = self.app  # type: ignore[assignment]
        await app.database.mark_played(episode.id, played=False)

        # Refresh episode list
        if self._selected_feed_key:
            await self._load_episodes(self._selected_feed_key)

        self.notify(f"Marked as unplayed: {episode.title}", severity="information")

    async def action_add_to_queue(self) -> None:
        """Add the selected episode to the playback queue."""
        episode_list = self.query_one(EpisodeList)
        episode = episode_list.get_selected_episode()

        if episode is None:
            self.notify("No episode selected", severity="warning")
            return

        app: FeedbackApp = self.app  # type: ignore[assignment]
        if await app.add_to_queue(episode):
            self.notify(f"Added to queue: {episode.title}", severity="information")
        else:
            self.notify("Failed to add to queue", severity="error")

    async def action_download_episode(self) -> None:
        """Download the selected episode."""
        episode_list = self.query_one(EpisodeList)
        episode = episode_list.get_selected_episode()

        if episode is None:
            self.notify("No episode selected", severity="warning")
            return

        app: FeedbackApp = self.app  # type: ignore[assignment]
        item = await app.download_episode(episode)

        if item:
            self.notify(f"Downloading: {episode.title}", severity="information")

    async def action_seek_forward(self) -> None:
        """Seek forward 30 seconds."""
        app: FeedbackApp = self.app  # type: ignore[assignment]

        if app.player.state.name not in ("PLAYING", "PAUSED"):
            return

        new_position = min(
            app.player.position_ms + 30000,
            app.player.duration_ms,
        )
        await app.player.seek(new_position)

    async def action_seek_backward(self) -> None:
        """Seek backward 10 seconds."""
        app: FeedbackApp = self.app  # type: ignore[assignment]

        if app.player.state.name not in ("PLAYING", "PAUSED"):
            return

        new_position = max(app.player.position_ms - 10000, 0)
        await app.player.seek(new_position)

    async def action_volume_up(self) -> None:
        """Increase volume by 10%."""
        app: FeedbackApp = self.app  # type: ignore[assignment]
        new_volume = min(app.player.volume + 10, 100)
        await app.player.set_volume(new_volume)
        self.notify(f"Volume: {new_volume}%")

    async def action_volume_down(self) -> None:
        """Decrease volume by 10%."""
        app: FeedbackApp = self.app  # type: ignore[assignment]
        new_volume = max(app.player.volume - 10, 0)
        await app.player.set_volume(new_volume)
        self.notify(f"Volume: {new_volume}%")

    async def action_speed_up(self) -> None:
        """Increase playback speed by 0.1x."""
        app: FeedbackApp = self.app  # type: ignore[assignment]
        new_speed = min(app.player.speed + 0.1, 2.0)
        await app.player.set_speed(new_speed)
        self.notify(f"Speed: {new_speed:.1f}x")

    async def action_speed_down(self) -> None:
        """Decrease playback speed by 0.1x."""
        app: FeedbackApp = self.app  # type: ignore[assignment]
        new_speed = max(app.player.speed - 0.1, 0.5)
        await app.player.set_speed(new_speed)
        self.notify(f"Speed: {new_speed:.1f}x")

    def action_search_podcasts(self) -> None:
        """Search for podcasts using Podcast Index API.

        Shows an input field to enter a search query.
        """
        if self._searching:
            return

        self._searching = True
        input_widget = SearchInput()
        self.mount(input_widget)
        input_widget.focus()

    async def _perform_search(self, query: str) -> None:
        """Perform podcast search and display results.

        Args:
            query: Search query string.
        """
        from feedback.config import get_config
        from feedback.feeds.discovery import (
            DiscoveryAuthError,
            DiscoverySearchError,
            PodcastIndexClient,
        )

        config = get_config()

        if not config.discovery.api_key or not config.discovery.api_secret:
            self.notify(
                "Podcast Index API credentials not configured. "
                "Add api_key and api_secret to [discovery] in config.toml",
                severity="error",
            )
            return

        client = PodcastIndexClient(
            api_key=config.discovery.api_key,
            api_secret=config.discovery.api_secret,
            timeout=config.network.timeout,
        )

        try:
            self.notify(f"Searching for '{query}'...")
            results = await client.search(query, max_results=10)

            if not results:
                self.notify("No podcasts found", severity="warning")
                return

            # Show results in metadata panel
            metadata_panel = self.query_one(MetadataPanel)
            result_text = "[bold]Search Results[/bold]\n\n"
            for i, podcast in enumerate(results, 1):
                result_text += f"{i}. {podcast.title}\n"
                result_text += f"   [dim]{podcast.url}[/dim]\n\n"

            metadata_panel.update(result_text)
            self.notify(
                f"Found {len(results)} podcasts. Use 'a' to add a feed URL.",
                severity="information",
            )

        except DiscoveryAuthError as e:
            self.notify(f"Auth error: {e}", severity="error")
        except DiscoverySearchError as e:
            self.notify(f"Search error: {e}", severity="error")
