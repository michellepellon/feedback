"""Tests for widget functionality."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import PropertyMock, patch

import pytest

from feedback.downloads import DownloadItem, DownloadStatus
from feedback.models.feed import Episode, Feed, QueueItem
from feedback.widgets.download_list import DownloadList, DownloadSelected
from feedback.widgets.episode_list import EpisodeList, EpisodeSelected
from feedback.widgets.feed_list import FeedList, FeedSelected
from feedback.widgets.player_bar import PlayerBar
from feedback.widgets.queue_list import QueueItemSelected, QueueList


class TestFeedList:
    """Tests for FeedList widget."""

    @pytest.fixture
    def sample_feeds(self) -> list[Feed]:
        """Create sample feeds for testing."""
        return [
            Feed(
                key="feed1",
                title="Test Podcast 1",
                description="A test podcast",
                link="https://example.com/feed1",
            ),
            Feed(
                key="feed2",
                title="Test Podcast 2",
                description="Another test podcast",
                link="https://example.com/feed2",
            ),
        ]

    def test_feed_list_initialization(self) -> None:
        """Test FeedList initializes correctly."""
        feed_list = FeedList()
        assert feed_list._feeds == []

    def test_feed_list_set_feeds(self, sample_feeds: list[Feed]) -> None:
        """Test setting feeds on FeedList."""
        feed_list = FeedList()
        feed_list.set_feeds(sample_feeds)
        assert feed_list._feeds == sample_feeds

    def test_feed_list_get_selected_empty(self) -> None:
        """Test get_selected_feed returns None when empty."""
        feed_list = FeedList()
        assert feed_list.get_selected_feed() is None

    def test_feed_list_get_selected_out_of_bounds(
        self, sample_feeds: list[Feed]
    ) -> None:
        """Test get_selected_feed returns None when index out of bounds."""
        feed_list = FeedList()
        feed_list._feeds = sample_feeds
        with patch.object(
            type(feed_list), "highlighted", new_callable=PropertyMock, return_value=10
        ):
            assert feed_list.get_selected_feed() is None

    def test_feed_list_get_selected_valid(self, sample_feeds: list[Feed]) -> None:
        """Test get_selected_feed returns feed when valid selection."""
        feed_list = FeedList()
        feed_list._feeds = sample_feeds
        with patch.object(
            type(feed_list), "highlighted", new_callable=PropertyMock, return_value=0
        ):
            assert feed_list.get_selected_feed() == sample_feeds[0]

    def test_feed_selected_message(self, sample_feeds: list[Feed]) -> None:
        """Test FeedSelected message creation."""
        feed = sample_feeds[0]
        message = FeedSelected(feed)
        assert message.feed == feed


class TestEpisodeList:
    """Tests for EpisodeList widget."""

    @pytest.fixture
    def sample_episodes(self) -> list[Episode]:
        """Create sample episodes for testing."""
        return [
            Episode(
                id=1,
                feed_key="feed1",
                title="Episode 1",
                enclosure="https://example.com/ep1.mp3",
                pubdate=datetime.now(UTC),
            ),
            Episode(
                id=2,
                feed_key="feed1",
                title="Episode 2",
                enclosure="https://example.com/ep2.mp3",
            ),
        ]

    def test_episode_list_initialization(self) -> None:
        """Test EpisodeList initializes correctly."""
        episode_list = EpisodeList()
        assert episode_list._episodes == []

    def test_episode_list_set_episodes(self, sample_episodes: list[Episode]) -> None:
        """Test setting episodes on EpisodeList."""
        episode_list = EpisodeList()
        episode_list.set_episodes(sample_episodes)
        assert episode_list._episodes == sample_episodes

    def test_episode_list_get_selected_empty(self) -> None:
        """Test get_selected_episode returns None when empty."""
        episode_list = EpisodeList()
        assert episode_list.get_selected_episode() is None

    def test_episode_list_get_selected_out_of_bounds(
        self, sample_episodes: list[Episode]
    ) -> None:
        """Test get_selected_episode returns None when index out of bounds."""
        episode_list = EpisodeList()
        episode_list._episodes = sample_episodes
        with patch.object(
            type(episode_list),
            "highlighted",
            new_callable=PropertyMock,
            return_value=10,
        ):
            assert episode_list.get_selected_episode() is None

    def test_episode_list_get_selected_valid(
        self, sample_episodes: list[Episode]
    ) -> None:
        """Test get_selected_episode returns episode when valid selection."""
        episode_list = EpisodeList()
        episode_list._episodes = sample_episodes
        with patch.object(
            type(episode_list), "highlighted", new_callable=PropertyMock, return_value=0
        ):
            assert episode_list.get_selected_episode() == sample_episodes[0]

    def test_episode_selected_message(self, sample_episodes: list[Episode]) -> None:
        """Test EpisodeSelected message creation."""
        episode = sample_episodes[0]
        message = EpisodeSelected(episode)
        assert message.episode == episode


class TestQueueList:
    """Tests for QueueList widget."""

    @pytest.fixture
    def sample_queue_items(self) -> list[tuple[QueueItem, Episode]]:
        """Create sample queue items for testing."""
        episode = Episode(
            id=1,
            feed_key="feed1",
            title="Episode 1",
            enclosure="https://example.com/ep1.mp3",
        )
        queue_item = QueueItem(episode_id=1, position=0)
        return [(queue_item, episode)]

    def test_queue_list_initialization(self) -> None:
        """Test QueueList initializes correctly."""
        queue_list = QueueList()
        assert queue_list._items == []

    def test_queue_list_set_queue(
        self, sample_queue_items: list[tuple[QueueItem, Episode]]
    ) -> None:
        """Test setting queue on QueueList."""
        queue_list = QueueList()
        queue_list.set_queue(sample_queue_items)
        assert queue_list._items == sample_queue_items

    def test_queue_list_get_selected_empty(self) -> None:
        """Test get_selected_item returns None when empty."""
        queue_list = QueueList()
        assert queue_list.get_selected_item() is None

    def test_queue_list_get_selected_out_of_bounds(
        self, sample_queue_items: list[tuple[QueueItem, Episode]]
    ) -> None:
        """Test get_selected_item returns None when index out of bounds."""
        queue_list = QueueList()
        queue_list._items = sample_queue_items
        with patch.object(
            type(queue_list), "highlighted", new_callable=PropertyMock, return_value=10
        ):
            assert queue_list.get_selected_item() is None

    def test_queue_list_get_selected_valid(
        self, sample_queue_items: list[tuple[QueueItem, Episode]]
    ) -> None:
        """Test get_selected_item returns item when valid selection."""
        queue_list = QueueList()
        queue_list._items = sample_queue_items
        with patch.object(
            type(queue_list), "highlighted", new_callable=PropertyMock, return_value=0
        ):
            assert queue_list.get_selected_item() == sample_queue_items[0]

    def test_queue_item_selected_message(
        self, sample_queue_items: list[tuple[QueueItem, Episode]]
    ) -> None:
        """Test QueueItemSelected message creation."""
        queue_item, episode = sample_queue_items[0]
        message = QueueItemSelected(queue_item, episode)
        assert message.queue_item == queue_item
        assert message.episode == episode


class TestDownloadList:
    """Tests for DownloadList widget."""

    @pytest.fixture
    def sample_downloads(self) -> list[DownloadItem]:
        """Create sample download items for testing."""
        return [
            DownloadItem(
                episode_id=1,
                url="https://example.com/ep1.mp3",
                destination=Path("/downloads/ep1.mp3"),
                status=DownloadStatus.PENDING,
            ),
            DownloadItem(
                episode_id=2,
                url="https://example.com/ep2.mp3",
                destination=Path("/downloads/ep2.mp3"),
                status=DownloadStatus.DOWNLOADING,
                progress=0.5,
            ),
        ]

    def test_download_list_initialization(self) -> None:
        """Test DownloadList initializes correctly."""
        download_list = DownloadList()
        assert download_list._downloads == []

    def test_download_list_set_downloads(
        self, sample_downloads: list[DownloadItem]
    ) -> None:
        """Test setting downloads on DownloadList."""
        download_list = DownloadList()
        download_list.set_downloads(sample_downloads)
        assert download_list._downloads == sample_downloads

    def test_download_list_get_selected_empty(self) -> None:
        """Test get_selected_download returns None when empty."""
        download_list = DownloadList()
        assert download_list.get_selected_download() is None

    def test_download_list_get_selected_out_of_bounds(
        self, sample_downloads: list[DownloadItem]
    ) -> None:
        """Test get_selected_download returns None when index out of bounds."""
        download_list = DownloadList()
        download_list._downloads = sample_downloads
        with patch.object(
            type(download_list),
            "highlighted",
            new_callable=PropertyMock,
            return_value=10,
        ):
            assert download_list.get_selected_download() is None

    def test_download_list_get_selected_valid(
        self, sample_downloads: list[DownloadItem]
    ) -> None:
        """Test get_selected_download returns item when valid selection."""
        download_list = DownloadList()
        download_list._downloads = sample_downloads
        with patch.object(
            type(download_list),
            "highlighted",
            new_callable=PropertyMock,
            return_value=0,
        ):
            assert download_list.get_selected_download() == sample_downloads[0]

    def test_download_selected_message(
        self, sample_downloads: list[DownloadItem]
    ) -> None:
        """Test DownloadSelected message creation."""
        download = sample_downloads[0]
        message = DownloadSelected(download)
        assert message.download == download


class TestPlayerBar:
    """Tests for PlayerBar widget."""

    def test_player_bar_default_values(self) -> None:
        """Test PlayerBar has correct default values."""
        player_bar = PlayerBar()
        assert player_bar.title == "No episode playing"
        assert player_bar.status == "Stopped"
        assert player_bar.position_ms == 0
        assert player_bar.duration_ms == 0
        assert player_bar.volume == 100

    def test_player_bar_set_playing(self) -> None:
        """Test set_playing method."""
        player_bar = PlayerBar()
        player_bar.set_playing(
            title="Test Episode", position_ms=5000, duration_ms=60000
        )
        assert player_bar.title == "Test Episode"
        assert player_bar.status == "Playing"
        assert player_bar.position_ms == 5000
        assert player_bar.duration_ms == 60000

    def test_player_bar_set_paused(self) -> None:
        """Test set_paused method."""
        player_bar = PlayerBar()
        player_bar.set_playing(title="Test Episode")
        player_bar.set_paused()
        assert player_bar.status == "Paused"

    def test_player_bar_set_stopped(self) -> None:
        """Test set_stopped method."""
        player_bar = PlayerBar()
        player_bar.set_playing(
            title="Test Episode", position_ms=5000, duration_ms=60000
        )
        player_bar.set_stopped()
        assert player_bar.title == "No episode playing"
        assert player_bar.status == "Stopped"
        assert player_bar.position_ms == 0
        assert player_bar.duration_ms == 0

    def test_player_bar_ms_to_time_seconds(self) -> None:
        """Test _ms_to_time with seconds only."""
        result = PlayerBar._ms_to_time(45000)
        assert result == "00:45"

    def test_player_bar_ms_to_time_minutes(self) -> None:
        """Test _ms_to_time with minutes and seconds."""
        result = PlayerBar._ms_to_time(125000)
        assert result == "02:05"

    def test_player_bar_ms_to_time_hours(self) -> None:
        """Test _ms_to_time with hours."""
        result = PlayerBar._ms_to_time(3725000)
        assert result == "01:02:05"

    def test_player_bar_ms_to_time_negative(self) -> None:
        """Test _ms_to_time with negative value."""
        result = PlayerBar._ms_to_time(-1000)
        assert result == "00:00"

    def test_player_bar_format_time(self) -> None:
        """Test _format_time method."""
        player_bar = PlayerBar()
        player_bar.position_ms = 65000
        player_bar.duration_ms = 300000
        result = player_bar._format_time()
        assert result == "01:05 / 05:00"
