"""Download queue for episode downloads."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path  # noqa: TC003 - used at runtime in dataclass
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from collections.abc import Callable


class DownloadStatus(IntEnum):
    """Status of a download."""

    PENDING = 0
    DOWNLOADING = 1
    COMPLETED = 2
    FAILED = 3
    CANCELLED = 4


@dataclass
class DownloadItem:
    """Represents a download in the queue."""

    url: str
    destination: Path
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0  # 0.0 to 1.0
    bytes_downloaded: int = 0
    total_bytes: int = 0
    error: str | None = None
    episode_id: int | None = None

    @property
    def progress_percent(self) -> int:
        """Progress as a percentage (0-100)."""
        return int(self.progress * 100)


@dataclass
class DownloadQueue:
    """Manages concurrent downloads of podcast episodes."""

    download_dir: Path
    max_concurrent: int = 3
    timeout: float = 300.0  # 5 minutes
    chunk_size: int = 65536  # 64KB
    user_agent: str = "Feedback/0.1.0"

    _queue: list[DownloadItem] = field(default_factory=list)
    _active: dict[str, asyncio.Task[None]] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _progress_callback: Callable[[DownloadItem], None] | None = None

    def __post_init__(self) -> None:
        """Ensure download directory exists."""
        self.download_dir.mkdir(parents=True, exist_ok=True)

    @property
    def pending_count(self) -> int:
        """Number of pending downloads."""
        return sum(1 for d in self._queue if d.status == DownloadStatus.PENDING)

    @property
    def active_count(self) -> int:
        """Number of active downloads."""
        return len(self._active)

    @property
    def completed_count(self) -> int:
        """Number of completed downloads."""
        return sum(1 for d in self._queue if d.status == DownloadStatus.COMPLETED)

    @property
    def failed_count(self) -> int:
        """Number of failed downloads."""
        return sum(1 for d in self._queue if d.status == DownloadStatus.FAILED)

    def set_progress_callback(
        self, callback: Callable[[DownloadItem], None] | None
    ) -> None:
        """Set callback for download progress updates.

        Args:
            callback: Function called with DownloadItem on progress updates.
        """
        self._progress_callback = callback

    async def add(
        self,
        url: str,
        filename: str | None = None,
        episode_id: int | None = None,
    ) -> DownloadItem:
        """Add a download to the queue.

        Args:
            url: URL to download.
            filename: Optional filename (derived from URL if not provided).
            episode_id: Optional episode ID for tracking.

        Returns:
            The created DownloadItem.
        """
        if filename is None:
            # Extract filename from URL
            filename = url.split("/")[-1].split("?")[0]
            if not filename:
                filename = f"download_{len(self._queue)}"

        destination = self.download_dir / filename

        item = DownloadItem(
            url=url,
            destination=destination,
            episode_id=episode_id,
        )

        async with self._lock:
            self._queue.append(item)

        # Try to start downloading
        await self._process_queue()

        return item

    async def add_batch(
        self,
        downloads: list[tuple[str, str | None, int | None]],
    ) -> list[DownloadItem]:
        """Add multiple downloads to the queue at once.

        Args:
            downloads: List of (url, filename, episode_id) tuples.
                filename and episode_id can be None.

        Returns:
            List of created DownloadItems.
        """
        items: list[DownloadItem] = []

        async with self._lock:
            for url, filename, episode_id in downloads:
                if filename is None:
                    filename = url.split("/")[-1].split("?")[0]
                    if not filename:
                        filename = f"download_{len(self._queue)}"

                destination = self.download_dir / filename
                item = DownloadItem(
                    url=url,
                    destination=destination,
                    episode_id=episode_id,
                )
                self._queue.append(item)
                items.append(item)

        # Start processing the queue
        await self._process_queue()

        return items

    async def cancel(self, url: str) -> bool:
        """Cancel a download by URL.

        Args:
            url: URL of the download to cancel.

        Returns:
            True if cancelled, False if not found or already completed.
        """
        async with self._lock:
            # Cancel active download
            if url in self._active:
                self._active[url].cancel()
                del self._active[url]

            # Update status
            for item in self._queue:
                if item.url == url and item.status in (
                    DownloadStatus.PENDING,
                    DownloadStatus.DOWNLOADING,
                ):
                    item.status = DownloadStatus.CANCELLED
                    return True

        return False

    async def cancel_all(self) -> int:
        """Cancel all pending and active downloads.

        Returns:
            Number of downloads cancelled.
        """
        cancelled = 0

        async with self._lock:
            # Cancel all active downloads
            for _url, task in list(self._active.items()):
                task.cancel()
                cancelled += 1
            self._active.clear()

            # Mark pending as cancelled
            for item in self._queue:
                if item.status in (DownloadStatus.PENDING, DownloadStatus.DOWNLOADING):
                    item.status = DownloadStatus.CANCELLED
                    cancelled += 1

        return cancelled

    async def clear_completed(self) -> int:
        """Remove completed and failed downloads from the queue.

        Returns:
            Number of items removed.
        """
        async with self._lock:
            before = len(self._queue)
            self._queue = [
                item
                for item in self._queue
                if item.status
                not in (
                    DownloadStatus.COMPLETED,
                    DownloadStatus.FAILED,
                    DownloadStatus.CANCELLED,
                )
            ]
            return before - len(self._queue)

    def get_items(self) -> list[DownloadItem]:
        """Get all items in the queue.

        Returns:
            Copy of the download queue.
        """
        return list(self._queue)

    def get_item(self, url: str) -> DownloadItem | None:
        """Get a download item by URL.

        Args:
            url: URL to look up.

        Returns:
            DownloadItem or None if not found.
        """
        for item in self._queue:
            if item.url == url:
                return item
        return None

    async def _process_queue(self) -> None:
        """Start downloads for pending items up to max_concurrent."""
        async with self._lock:
            # Find pending items to start
            pending = [
                item for item in self._queue if item.status == DownloadStatus.PENDING
            ]

            # Start downloads up to limit
            for item in pending:
                if len(self._active) >= self.max_concurrent:
                    break

                item.status = DownloadStatus.DOWNLOADING
                task = asyncio.create_task(self._download(item))
                self._active[item.url] = task

    async def _download(self, item: DownloadItem) -> None:
        """Download a single item.

        Args:
            item: DownloadItem to download.
        """
        try:
            async with (
                httpx.AsyncClient(
                    timeout=httpx.Timeout(self.timeout, connect=30.0),
                    follow_redirects=True,
                    headers={"User-Agent": self.user_agent},
                ) as client,
                client.stream("GET", item.url) as response,
            ):
                response.raise_for_status()

                # Get total size if available
                total = response.headers.get("content-length")
                if total:
                    item.total_bytes = int(total)

                # Download with progress tracking
                with item.destination.open("wb") as f:
                    async for chunk in response.aiter_bytes(self.chunk_size):
                        f.write(chunk)
                        item.bytes_downloaded += len(chunk)

                        if item.total_bytes > 0:
                            item.progress = item.bytes_downloaded / item.total_bytes

                        if self._progress_callback:
                            self._progress_callback(item)

            # Mark completed
            item.status = DownloadStatus.COMPLETED
            item.progress = 1.0

        except asyncio.CancelledError:
            item.status = DownloadStatus.CANCELLED
            # Clean up partial file
            if item.destination.exists():
                item.destination.unlink()
            raise

        except httpx.HTTPStatusError as e:
            item.status = DownloadStatus.FAILED
            item.error = f"HTTP {e.response.status_code}"

        except httpx.RequestError as e:
            item.status = DownloadStatus.FAILED
            item.error = str(e)

        except OSError as e:
            item.status = DownloadStatus.FAILED
            item.error = f"IO error: {e}"

        finally:
            # Remove from active and process next
            async with self._lock:
                self._active.pop(item.url, None)

            if self._progress_callback:
                self._progress_callback(item)

            # Start next pending download
            await self._process_queue()

    async def wait_all(self) -> None:
        """Wait for all downloads to complete."""
        while self._active:
            await asyncio.gather(*self._active.values(), return_exceptions=True)
            # Re-check in case new downloads were added
            await asyncio.sleep(0.1)
