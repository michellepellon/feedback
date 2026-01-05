"""Download list widget for displaying download progress."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option

if TYPE_CHECKING:
    from feedback.downloads import DownloadItem


class DownloadSelected(Message):
    """Message sent when a download is selected."""

    bubble = True  # Ensure message bubbles up to screen

    def __init__(self, download: DownloadItem) -> None:
        """Initialize the message.

        Args:
            download: The selected download item.
        """
        self.download = download
        super().__init__()


class DownloadList(OptionList):
    """Navigable list of downloads."""

    DEFAULT_CSS = """
    DownloadList {
        width: 100%;
        height: 1fr;
        border: solid $primary;
    }

    DownloadList:focus {
        border: solid $accent;
    }

    DownloadList > .option-list--option-highlighted {
        background: $accent;
    }
    """

    def __init__(self) -> None:
        """Initialize the download list."""
        super().__init__()
        self._downloads: list[DownloadItem] = []

    def set_downloads(self, downloads: list[DownloadItem]) -> None:
        """Set the downloads to display.

        Args:
            downloads: List of DownloadItem objects.
        """
        self._downloads = downloads
        self.clear_options()
        for download in downloads:
            title = self._format_download(download)
            self.add_option(Option(title, id=download.url))

    def _format_download(self, download: DownloadItem) -> str:
        """Format a download item for display.

        Args:
            download: The download item.

        Returns:
            Formatted display string.
        """
        from feedback.downloads import DownloadStatus

        filename = download.destination.name
        status_icons = {
            DownloadStatus.PENDING: "[pending]",
            DownloadStatus.DOWNLOADING: f"[{download.progress_percent}%]",
            DownloadStatus.COMPLETED: "[done]",
            DownloadStatus.FAILED: "[failed]",
            DownloadStatus.CANCELLED: "[cancelled]",
        }
        status = status_icons.get(download.status, "")
        return f"{status} {filename}"

    def get_selected_download(self) -> DownloadItem | None:
        """Get the currently selected download.

        Returns:
            The selected DownloadItem or None.
        """
        if self.highlighted is None or not self._downloads:
            return None
        if 0 <= self.highlighted < len(self._downloads):
            return self._downloads[self.highlighted]
        return None

    def on_option_list_option_selected(self, _event: OptionList.OptionSelected) -> None:
        """Handle option selection."""
        download = self.get_selected_download()
        if download:
            self.post_message(DownloadSelected(download))
