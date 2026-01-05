"""Downloads screen for managing episode downloads."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from feedback.downloads import DownloadItem, DownloadStatus
from feedback.widgets.download_list import DownloadList, DownloadSelected
from feedback.widgets.player_bar import PlayerBar

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from feedback.app import FeedbackApp


class DownloadsScreen(Screen[None]):
    """Screen for managing downloads."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("j", "move_down", "Down", show=False),
        Binding("k", "move_up", "Up", show=False),
        Binding("enter", "play", "Play"),
        Binding("d", "delete", "Delete"),
        Binding("c", "cancel", "Cancel"),
        Binding("C", "cancel_all", "Cancel All"),
        Binding("x", "clear_completed", "Clear Done"),
        Binding("p", "play_pause", "Play/Pause"),
        Binding("space", "play_pause", "Play/Pause", show=False),
    ]

    def __init__(self) -> None:
        """Initialize the downloads screen."""
        super().__init__()
        self._refresh_timer = None

    def compose(self) -> ComposeResult:
        """Compose the downloads screen layout."""
        yield Header()
        yield PlayerBar()
        with Vertical(id="downloads-content"):
            yield Static("Downloads", id="downloads-title")
            yield DownloadList()
        yield Footer()

    async def on_mount(self) -> None:
        """Set up when screen mounts."""
        await self._load_downloads()
        # Set up progress callback and refresh timer
        app: FeedbackApp = self.app  # type: ignore[assignment]
        app.download_queue.set_progress_callback(self._on_progress)
        self._refresh_timer = self.set_interval(1.0, self._refresh_display)

    async def on_screen_resume(self) -> None:
        """Reload downloads when returning to this screen."""
        await self._load_downloads()

    async def _load_downloads(self) -> None:
        """Load downloads from the queue."""
        app: FeedbackApp = self.app  # type: ignore[assignment]
        items = app.download_queue.get_items()

        download_list = self.query_one(DownloadList)
        download_list.set_downloads(items)

        if not items:
            self.notify("No downloads", severity="information")

    def _on_progress(self, item: DownloadItem) -> None:
        """Handle download progress update.

        Args:
            item: The download item with updated progress.
        """
        # Progress updates will be picked up by the refresh timer
        pass

    async def _refresh_display(self) -> None:
        """Refresh the download list display."""
        app: FeedbackApp = self.app  # type: ignore[assignment]
        items = app.download_queue.get_items()
        download_list = self.query_one(DownloadList)
        download_list.set_downloads(items)

    def action_move_down(self) -> None:
        """Move selection down."""
        try:
            download_list = self.query_one(DownloadList)
            download_list.action_cursor_down()
        except Exception:
            pass

    def action_move_up(self) -> None:
        """Move selection up."""
        try:
            download_list = self.query_one(DownloadList)
            download_list.action_cursor_up()
        except Exception:
            pass

    async def action_play(self) -> None:
        """Play the selected downloaded episode."""
        download_list = self.query_one(DownloadList)
        item = download_list.get_selected_download()

        if item is None:
            self.notify("No download selected", severity="warning")
            return

        if item.status != DownloadStatus.COMPLETED:
            self.notify("Download not complete", severity="warning")
            return

        if not item.destination.exists():
            self.notify("Downloaded file not found", severity="error")
            return

        app: FeedbackApp = self.app  # type: ignore[assignment]

        # Get the episode if we have the ID
        if item.episode_id:
            episode = await app.database.get_episode(item.episode_id)
            if episode:
                # Update episode with downloaded path if not set
                if not episode.downloaded_path:
                    episode.downloaded_path = str(item.destination)
                    await app.database.upsert_episode(episode)

                await app.play_episode(episode)

                player_bar = self.query_one(PlayerBar)
                player_bar.set_playing(
                    title=episode.title,
                    duration_ms=app.player.duration_ms,
                )
                self.notify(f"Playing: {episode.title}")
                return

        # Fallback: play file directly
        await app.player.play(str(item.destination))
        player_bar = self.query_one(PlayerBar)
        player_bar.set_playing(
            title=item.destination.name,
            duration_ms=app.player.duration_ms,
        )
        self.notify(f"Playing: {item.destination.name}")

    async def action_delete(self) -> None:
        """Delete the selected download and its file."""
        from feedback.widgets.confirm_dialog import ConfirmDialog

        download_list = self.query_one(DownloadList)
        item = download_list.get_selected_download()

        if item is None:
            self.notify("No download selected", severity="warning")
            return

        if item.status == DownloadStatus.DOWNLOADING:
            self.notify("Cancel the download first", severity="warning")
            return

        # Show confirmation dialog
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog(
                title="Delete Download",
                message=f"Delete '{item.destination.name}'?",
                confirm_label="Delete",
                cancel_label="Cancel",
            )
        )

        if not confirmed:
            return

        # Delete the file if it exists
        if item.destination.exists():
            try:
                item.destination.unlink()
            except OSError as e:
                self.notify(f"Failed to delete file: {e}", severity="error")
                return

        # Update episode to remove downloaded_path
        app: FeedbackApp = self.app  # type: ignore[assignment]
        if item.episode_id:
            episode = await app.database.get_episode(item.episode_id)
            if episode and episode.downloaded_path:
                episode.downloaded_path = None
                await app.database.upsert_episode(episode)

        # Remove from queue display (clear completed will remove it)
        await app.download_queue.clear_completed()
        await self._load_downloads()

        self.notify("Download deleted", severity="information")

    async def action_cancel(self) -> None:
        """Cancel the selected download."""
        download_list = self.query_one(DownloadList)
        item = download_list.get_selected_download()

        if item is None:
            self.notify("No download selected", severity="warning")
            return

        if item.status not in (DownloadStatus.PENDING, DownloadStatus.DOWNLOADING):
            self.notify("Download not in progress", severity="information")
            return

        app: FeedbackApp = self.app  # type: ignore[assignment]
        cancelled = await app.download_queue.cancel(item.url)

        if cancelled:
            await self._load_downloads()
            self.notify("Download cancelled", severity="information")
        else:
            self.notify("Failed to cancel download", severity="error")

    async def action_cancel_all(self) -> None:
        """Cancel all pending and active downloads."""
        from feedback.widgets.confirm_dialog import ConfirmDialog

        app: FeedbackApp = self.app  # type: ignore[assignment]

        # Count active/pending downloads
        items = app.download_queue.get_items()
        active_count = sum(
            1
            for item in items
            if item.status in (DownloadStatus.PENDING, DownloadStatus.DOWNLOADING)
        )

        if active_count == 0:
            self.notify("No downloads to cancel", severity="information")
            return

        # Show confirmation dialog
        confirmed = await self.app.push_screen_wait(
            ConfirmDialog(
                title="Cancel All Downloads",
                message=f"Cancel {active_count} active download{'s' if active_count != 1 else ''}?",
                confirm_label="Cancel All",
                cancel_label="Keep",
            )
        )

        if not confirmed:
            return

        count = await app.download_queue.cancel_all()

        await self._load_downloads()

        if count > 0:
            self.notify(f"Cancelled {count} downloads", severity="information")

    async def action_clear_completed(self) -> None:
        """Clear completed, failed, and cancelled downloads from the list."""
        app: FeedbackApp = self.app  # type: ignore[assignment]
        count = await app.download_queue.clear_completed()

        await self._load_downloads()

        if count > 0:
            self.notify(f"Cleared {count} downloads", severity="information")
        else:
            self.notify("Nothing to clear", severity="information")

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

    async def on_download_selected(self, event: DownloadSelected) -> None:
        """Handle download selection."""
        if event.download.status == DownloadStatus.COMPLETED:
            await self.action_play()
