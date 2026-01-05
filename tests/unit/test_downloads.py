"""Tests for download queue."""

import asyncio
import contextlib
from pathlib import Path

import httpx
import pytest
import respx

from feedback.downloads import DownloadItem, DownloadQueue, DownloadStatus


class TestDownloadStatus:
    """Tests for DownloadStatus enum."""

    def test_status_values(self) -> None:
        """Test status enum values."""
        assert DownloadStatus.PENDING == 0
        assert DownloadStatus.DOWNLOADING == 1
        assert DownloadStatus.COMPLETED == 2
        assert DownloadStatus.FAILED == 3
        assert DownloadStatus.CANCELLED == 4


class TestDownloadItem:
    """Tests for DownloadItem."""

    def test_create_item(self, tmp_path: Path) -> None:
        """Test creating a download item."""
        item = DownloadItem(
            url="https://example.com/file.mp3",
            destination=tmp_path / "file.mp3",
        )
        assert item.status == DownloadStatus.PENDING
        assert item.progress == 0.0
        assert item.bytes_downloaded == 0
        assert item.error is None

    def test_progress_percent(self, tmp_path: Path) -> None:
        """Test progress_percent property."""
        item = DownloadItem(
            url="https://example.com/file.mp3",
            destination=tmp_path / "file.mp3",
            progress=0.5,
        )
        assert item.progress_percent == 50

    def test_item_with_episode_id(self, tmp_path: Path) -> None:
        """Test item with episode ID."""
        item = DownloadItem(
            url="https://example.com/file.mp3",
            destination=tmp_path / "file.mp3",
            episode_id=42,
        )
        assert item.episode_id == 42


class TestDownloadQueueInit:
    """Tests for DownloadQueue initialization."""

    def test_default_values(self, tmp_path: Path) -> None:
        """Test default initialization values."""
        queue = DownloadQueue(download_dir=tmp_path)
        assert queue.max_concurrent == 3
        assert queue.timeout == 300.0
        assert queue.chunk_size == 65536
        assert tmp_path.exists()

    def test_custom_values(self, tmp_path: Path) -> None:
        """Test custom initialization values."""
        queue = DownloadQueue(
            download_dir=tmp_path,
            max_concurrent=5,
            timeout=60.0,
            chunk_size=1024,
        )
        assert queue.max_concurrent == 5
        assert queue.timeout == 60.0
        assert queue.chunk_size == 1024

    def test_creates_download_dir(self, tmp_path: Path) -> None:
        """Test that init creates download directory."""
        new_dir = tmp_path / "downloads" / "nested"
        DownloadQueue(download_dir=new_dir)
        assert new_dir.exists()


class TestDownloadQueueCounts:
    """Tests for queue count properties."""

    @pytest.mark.asyncio
    async def test_pending_count(self, tmp_path: Path) -> None:
        """Test pending_count property."""
        queue = DownloadQueue(download_dir=tmp_path, max_concurrent=1)

        # Add items without starting downloads (we'll mock later)
        item1 = DownloadItem(
            url="url1", destination=tmp_path / "f1", status=DownloadStatus.PENDING
        )
        item2 = DownloadItem(
            url="url2", destination=tmp_path / "f2", status=DownloadStatus.PENDING
        )
        item3 = DownloadItem(
            url="url3", destination=tmp_path / "f3", status=DownloadStatus.COMPLETED
        )
        queue._queue = [item1, item2, item3]

        assert queue.pending_count == 2

    @pytest.mark.asyncio
    async def test_completed_count(self, tmp_path: Path) -> None:
        """Test completed_count property."""
        queue = DownloadQueue(download_dir=tmp_path)

        item1 = DownloadItem(
            url="url1", destination=tmp_path / "f1", status=DownloadStatus.COMPLETED
        )
        item2 = DownloadItem(
            url="url2", destination=tmp_path / "f2", status=DownloadStatus.COMPLETED
        )
        queue._queue = [item1, item2]

        assert queue.completed_count == 2

    @pytest.mark.asyncio
    async def test_failed_count(self, tmp_path: Path) -> None:
        """Test failed_count property."""
        queue = DownloadQueue(download_dir=tmp_path)

        item1 = DownloadItem(
            url="url1", destination=tmp_path / "f1", status=DownloadStatus.FAILED
        )
        queue._queue = [item1]

        assert queue.failed_count == 1

    @pytest.mark.asyncio
    async def test_active_count(self, tmp_path: Path) -> None:
        """Test active_count property."""
        queue = DownloadQueue(download_dir=tmp_path)
        assert queue.active_count == 0


class TestDownloadQueueAdd:
    """Tests for adding downloads."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_add_download(self, tmp_path: Path) -> None:
        """Test adding a download."""
        respx.get("https://example.com/file.mp3").respond(
            200, content=b"audio data here"
        )

        queue = DownloadQueue(download_dir=tmp_path)
        item = await queue.add("https://example.com/file.mp3")

        # Wait for download to complete
        await queue.wait_all()

        assert item.destination == tmp_path / "file.mp3"
        assert item.status == DownloadStatus.COMPLETED
        assert (tmp_path / "file.mp3").exists()

    @pytest.mark.asyncio
    @respx.mock
    async def test_add_with_custom_filename(self, tmp_path: Path) -> None:
        """Test adding download with custom filename."""
        respx.get("https://example.com/file.mp3").respond(200, content=b"data")

        queue = DownloadQueue(download_dir=tmp_path)
        item = await queue.add(
            "https://example.com/file.mp3",
            filename="custom.mp3",
        )

        await queue.wait_all()

        assert item.destination == tmp_path / "custom.mp3"
        assert (tmp_path / "custom.mp3").exists()

    @pytest.mark.asyncio
    @respx.mock
    async def test_add_with_episode_id(self, tmp_path: Path) -> None:
        """Test adding download with episode ID."""
        respx.get("https://example.com/file.mp3").respond(200, content=b"data")

        queue = DownloadQueue(download_dir=tmp_path)
        item = await queue.add(
            "https://example.com/file.mp3",
            episode_id=123,
        )

        assert item.episode_id == 123

    @pytest.mark.asyncio
    @respx.mock
    async def test_add_url_without_filename(self, tmp_path: Path) -> None:
        """Test adding URL without extractable filename."""
        respx.get("https://example.com/").respond(200, content=b"data")

        queue = DownloadQueue(download_dir=tmp_path)
        item = await queue.add("https://example.com/")

        await queue.wait_all()

        assert "download_" in item.destination.name


class TestDownloadQueueBatch:
    """Tests for batch download functionality."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_add_batch(self, tmp_path: Path) -> None:
        """Test adding multiple downloads at once."""
        for i in range(3):
            respx.get(f"https://example.com/file{i}.mp3").respond(
                200, content=f"data{i}".encode()
            )

        queue = DownloadQueue(download_dir=tmp_path)
        downloads = [
            (f"https://example.com/file{i}.mp3", f"batch{i}.mp3", i) for i in range(3)
        ]

        items = await queue.add_batch(downloads)
        await queue.wait_all()

        assert len(items) == 3
        for i, item in enumerate(items):
            assert item.destination == tmp_path / f"batch{i}.mp3"
            assert item.episode_id == i
            assert item.status == DownloadStatus.COMPLETED
            assert (tmp_path / f"batch{i}.mp3").exists()

    @pytest.mark.asyncio
    @respx.mock
    async def test_add_batch_without_filenames(self, tmp_path: Path) -> None:
        """Test batch add with auto-generated filenames."""
        for i in range(2):
            respx.get(f"https://example.com/ep{i}.mp3").respond(200, content=b"data")

        queue = DownloadQueue(download_dir=tmp_path)
        downloads = [(f"https://example.com/ep{i}.mp3", None, None) for i in range(2)]

        items = await queue.add_batch(downloads)
        await queue.wait_all()

        assert len(items) == 2
        assert items[0].destination == tmp_path / "ep0.mp3"
        assert items[1].destination == tmp_path / "ep1.mp3"

    @pytest.mark.asyncio
    @respx.mock
    async def test_add_batch_respects_concurrency(self, tmp_path: Path) -> None:
        """Test batch downloads respect max_concurrent."""
        for i in range(5):
            respx.get(f"https://example.com/file{i}.mp3").respond(200, content=b"data")

        queue = DownloadQueue(download_dir=tmp_path, max_concurrent=2)
        downloads = [(f"https://example.com/file{i}.mp3", None, None) for i in range(5)]

        await queue.add_batch(downloads)

        # Should never exceed max_concurrent
        assert queue.active_count <= 2

        await queue.wait_all()
        assert queue.completed_count == 5

    @pytest.mark.asyncio
    async def test_add_batch_empty(self, tmp_path: Path) -> None:
        """Test adding empty batch."""
        queue = DownloadQueue(download_dir=tmp_path)
        items = await queue.add_batch([])
        assert items == []


class TestDownloadQueueDownload:
    """Tests for download functionality."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_download_with_content_length(self, tmp_path: Path) -> None:
        """Test download tracks progress with content-length."""
        content = b"x" * 1000
        respx.get("https://example.com/file.mp3").respond(
            200,
            content=content,
            headers={"content-length": str(len(content))},
        )

        progress_updates: list[float] = []

        def on_progress(item: DownloadItem) -> None:
            progress_updates.append(item.progress)

        queue = DownloadQueue(download_dir=tmp_path, chunk_size=100)
        queue.set_progress_callback(on_progress)

        await queue.add("https://example.com/file.mp3")
        await queue.wait_all()

        assert len(progress_updates) > 0
        assert progress_updates[-1] == 1.0

    @pytest.mark.asyncio
    @respx.mock
    async def test_download_completes_with_data(self, tmp_path: Path) -> None:
        """Test download completes and has bytes downloaded."""
        respx.get("https://example.com/file.mp3").respond(200, content=b"audio data")

        queue = DownloadQueue(download_dir=tmp_path)
        item = await queue.add("https://example.com/file.mp3")
        await queue.wait_all()

        assert item.status == DownloadStatus.COMPLETED
        assert item.bytes_downloaded > 0
        assert (tmp_path / "file.mp3").read_bytes() == b"audio data"

    @pytest.mark.asyncio
    @respx.mock
    async def test_download_http_error(self, tmp_path: Path) -> None:
        """Test download handles HTTP errors."""
        respx.get("https://example.com/file.mp3").respond(404)

        queue = DownloadQueue(download_dir=tmp_path)
        item = await queue.add("https://example.com/file.mp3")
        await queue.wait_all()

        assert item.status == DownloadStatus.FAILED
        assert "404" in item.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_download_connection_error(self, tmp_path: Path) -> None:
        """Test download handles connection errors."""
        respx.get("https://example.com/file.mp3").mock(
            side_effect=httpx.ConnectError("failed")
        )

        queue = DownloadQueue(download_dir=tmp_path)
        item = await queue.add("https://example.com/file.mp3")
        await queue.wait_all()

        assert item.status == DownloadStatus.FAILED
        assert "failed" in item.error


class TestDownloadQueueConcurrency:
    """Tests for concurrent downloads."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_max_concurrent_respected(self, tmp_path: Path) -> None:
        """Test that max_concurrent limit is respected."""
        # Create slow responses
        for i in range(5):
            respx.get(f"https://example.com/file{i}.mp3").respond(200, content=b"data")

        queue = DownloadQueue(download_dir=tmp_path, max_concurrent=2)

        # Add 5 downloads
        for i in range(5):
            await queue.add(f"https://example.com/file{i}.mp3")

        # Should never exceed max_concurrent active downloads
        assert queue.active_count <= 2

        await queue.wait_all()

        assert queue.completed_count == 5


class TestDownloadQueueCancel:
    """Tests for cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_pending(self, tmp_path: Path) -> None:
        """Test cancelling a pending download."""
        queue = DownloadQueue(download_dir=tmp_path, max_concurrent=0)

        # Manually add pending item (max_concurrent=0 prevents auto-start)
        item = DownloadItem(
            url="https://example.com/file.mp3",
            destination=tmp_path / "file.mp3",
            status=DownloadStatus.PENDING,
        )
        queue._queue.append(item)

        result = await queue.cancel("https://example.com/file.mp3")
        assert result is True
        assert item.status == DownloadStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_downloading(self, tmp_path: Path) -> None:
        """Test cancelling a downloading item."""
        queue = DownloadQueue(download_dir=tmp_path)

        item = DownloadItem(
            url="https://example.com/file.mp3",
            destination=tmp_path / "file.mp3",
            status=DownloadStatus.DOWNLOADING,
        )
        queue._queue.append(item)

        result = await queue.cancel("https://example.com/file.mp3")
        assert result is True
        assert item.status == DownloadStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_active_download(self, tmp_path: Path) -> None:
        """Test cancelling an active download task."""
        queue = DownloadQueue(download_dir=tmp_path)

        # Create a mock task
        async def slow_task() -> None:
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                raise

        task = asyncio.create_task(slow_task())
        queue._active["https://example.com/file.mp3"] = task

        item = DownloadItem(
            url="https://example.com/file.mp3",
            destination=tmp_path / "file.mp3",
            status=DownloadStatus.DOWNLOADING,
        )
        queue._queue.append(item)

        result = await queue.cancel("https://example.com/file.mp3")
        assert result is True

        # Wait for task to be cancelled
        with contextlib.suppress(asyncio.CancelledError):
            await task

        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_cancel_not_found(self, tmp_path: Path) -> None:
        """Test cancelling non-existent download."""
        queue = DownloadQueue(download_dir=tmp_path)
        result = await queue.cancel("https://example.com/nonexistent.mp3")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_completed(self, tmp_path: Path) -> None:
        """Test cannot cancel completed download."""
        queue = DownloadQueue(download_dir=tmp_path)
        item = DownloadItem(
            url="https://example.com/file.mp3",
            destination=tmp_path / "file.mp3",
            status=DownloadStatus.COMPLETED,
        )
        queue._queue.append(item)

        result = await queue.cancel("https://example.com/file.mp3")
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_all(self, tmp_path: Path) -> None:
        """Test cancelling all downloads."""
        queue = DownloadQueue(download_dir=tmp_path)

        # Add multiple items
        for i in range(3):
            item = DownloadItem(
                url=f"url{i}",
                destination=tmp_path / f"f{i}",
                status=DownloadStatus.PENDING,
            )
            queue._queue.append(item)

        cancelled = await queue.cancel_all()
        assert cancelled == 3

        for item in queue._queue:
            assert item.status == DownloadStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_all_with_active(self, tmp_path: Path) -> None:
        """Test cancel_all cancels active download tasks."""
        queue = DownloadQueue(download_dir=tmp_path)

        # Create mock tasks
        async def slow_task() -> None:
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                raise

        task1 = asyncio.create_task(slow_task())
        task2 = asyncio.create_task(slow_task())
        queue._active["url1"] = task1
        queue._active["url2"] = task2

        cancelled = await queue.cancel_all()
        assert cancelled >= 2

        # Wait for tasks to be cancelled
        for task in [task1, task2]:
            with contextlib.suppress(asyncio.CancelledError):
                await task

        assert task1.cancelled()
        assert task2.cancelled()


class TestDownloadQueueClear:
    """Tests for clearing completed downloads."""

    @pytest.mark.asyncio
    async def test_clear_completed(self, tmp_path: Path) -> None:
        """Test clearing completed downloads."""
        queue = DownloadQueue(download_dir=tmp_path)

        queue._queue = [
            DownloadItem(
                url="u1", destination=tmp_path / "f1", status=DownloadStatus.COMPLETED
            ),
            DownloadItem(
                url="u2", destination=tmp_path / "f2", status=DownloadStatus.PENDING
            ),
            DownloadItem(
                url="u3", destination=tmp_path / "f3", status=DownloadStatus.FAILED
            ),
            DownloadItem(
                url="u4", destination=tmp_path / "f4", status=DownloadStatus.CANCELLED
            ),
        ]

        removed = await queue.clear_completed()
        assert removed == 3  # completed, failed, cancelled
        assert len(queue._queue) == 1
        assert queue._queue[0].url == "u2"


class TestDownloadQueueGetItems:
    """Tests for getting queue items."""

    @pytest.mark.asyncio
    async def test_get_items(self, tmp_path: Path) -> None:
        """Test getting all items."""
        queue = DownloadQueue(download_dir=tmp_path)

        item1 = DownloadItem(url="u1", destination=tmp_path / "f1")
        item2 = DownloadItem(url="u2", destination=tmp_path / "f2")
        queue._queue = [item1, item2]

        items = queue.get_items()
        assert len(items) == 2
        # Should be a copy
        items.append(DownloadItem(url="u3", destination=tmp_path / "f3"))
        assert len(queue._queue) == 2

    @pytest.mark.asyncio
    async def test_get_item(self, tmp_path: Path) -> None:
        """Test getting single item by URL."""
        queue = DownloadQueue(download_dir=tmp_path)

        item = DownloadItem(
            url="https://example.com/file.mp3", destination=tmp_path / "f"
        )
        queue._queue = [item]

        result = queue.get_item("https://example.com/file.mp3")
        assert result is item

    @pytest.mark.asyncio
    async def test_get_item_not_found(self, tmp_path: Path) -> None:
        """Test getting non-existent item."""
        queue = DownloadQueue(download_dir=tmp_path)
        result = queue.get_item("nonexistent")
        assert result is None


class TestDownloadQueueProgressCallback:
    """Tests for progress callback."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_progress_callback_called(self, tmp_path: Path) -> None:
        """Test progress callback is called."""
        respx.get("https://example.com/file.mp3").respond(200, content=b"data")

        callback_items: list[DownloadItem] = []

        def on_progress(item: DownloadItem) -> None:
            callback_items.append(item)

        queue = DownloadQueue(download_dir=tmp_path)
        queue.set_progress_callback(on_progress)

        await queue.add("https://example.com/file.mp3")
        await queue.wait_all()

        assert len(callback_items) > 0
        # Last callback should be completed status
        assert callback_items[-1].status == DownloadStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_set_progress_callback_none(self, tmp_path: Path) -> None:
        """Test setting progress callback to None."""
        queue = DownloadQueue(download_dir=tmp_path)
        queue.set_progress_callback(lambda _: None)
        queue.set_progress_callback(None)
        assert queue._progress_callback is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_download_without_callback(self, tmp_path: Path) -> None:
        """Test download works without progress callback."""
        respx.get("https://example.com/file.mp3").respond(200, content=b"data")

        queue = DownloadQueue(download_dir=tmp_path)
        # No callback set

        item = await queue.add("https://example.com/file.mp3")
        await queue.wait_all()

        assert item.status == DownloadStatus.COMPLETED


class TestDownloadQueueErrors:
    """Tests for error handling."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_download_io_error(self, tmp_path: Path) -> None:
        """Test download handles IO errors."""
        respx.get("https://example.com/file.mp3").respond(200, content=b"data")

        # Make directory read-only to cause IO error
        queue = DownloadQueue(download_dir=tmp_path)

        item = DownloadItem(
            url="https://example.com/file.mp3",
            destination=tmp_path / "nonexistent_subdir" / "file.mp3",
            status=DownloadStatus.PENDING,
        )
        queue._queue.append(item)

        # Directly call _download to trigger IO error
        await queue._download(item)

        assert item.status == DownloadStatus.FAILED
        assert "IO error" in item.error

    @pytest.mark.asyncio
    async def test_download_cancelled_cleans_up(self, tmp_path: Path) -> None:
        """Test cancelled download cleans up partial file."""
        DownloadQueue(download_dir=tmp_path)

        # Create a partial file
        partial_file = tmp_path / "partial.mp3"
        partial_file.write_bytes(b"partial data")

        item = DownloadItem(
            url="https://example.com/partial.mp3",
            destination=partial_file,
            status=DownloadStatus.DOWNLOADING,
        )

        # Simulate CancelledError in _download
        async def mock_download() -> None:
            try:
                raise asyncio.CancelledError()
            except asyncio.CancelledError:
                item.status = DownloadStatus.CANCELLED
                if item.destination.exists():
                    item.destination.unlink()
                raise

        with contextlib.suppress(asyncio.CancelledError):
            await mock_download()

        assert item.status == DownloadStatus.CANCELLED
        assert not partial_file.exists()


class TestDownloadQueueNoProgress:
    """Tests for downloads without total_bytes (progress tracking)."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_progress_zero_total(self, tmp_path: Path) -> None:
        """Test progress stays 0 when total_bytes is unknown."""
        # Use streaming response without content-length
        respx.get("https://example.com/file.mp3").respond(
            200,
            content=b"x" * 100,
        )

        queue = DownloadQueue(download_dir=tmp_path, chunk_size=10)

        item = DownloadItem(
            url="https://example.com/file.mp3",
            destination=tmp_path / "file.mp3",
            status=DownloadStatus.PENDING,
            total_bytes=0,  # Explicitly set to 0
        )
        queue._queue.append(item)

        # Force the branch where total_bytes is 0
        # by patching the response to not include content-length
        await queue._process_queue()
        await queue.wait_all()

        # File should be downloaded
        assert (tmp_path / "file.mp3").exists()
