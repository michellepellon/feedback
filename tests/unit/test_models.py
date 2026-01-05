"""Tests for feedback data models."""

from datetime import datetime

import pytest

from feedback.models import Episode, Feed, QueueItem


class TestFeed:
    """Tests for the Feed model."""

    def test_create_feed_minimal(self):
        """Test creating a feed with minimal required fields."""
        feed = Feed(key="https://example.com/feed", title="Test Feed")
        assert feed.key == "https://example.com/feed"
        assert feed.title == "Test Feed"
        assert feed.description == ""
        assert feed.link == ""
        assert feed.last_build_date is None
        assert feed.copyright is None

    def test_create_feed_full(self):
        """Test creating a feed with all fields."""
        now = datetime.now()
        feed = Feed(
            key="https://example.com/feed",
            title="Full Feed",
            description="A full description",
            link="https://example.com",
            last_build_date=now,
            copyright="2024 Example",
        )
        assert feed.key == "https://example.com/feed"
        assert feed.title == "Full Feed"
        assert feed.description == "A full description"
        assert feed.link == "https://example.com"
        assert feed.last_build_date == now
        assert feed.copyright == "2024 Example"

    def test_feed_str(self):
        """Test feed string representation."""
        feed = Feed(key="key", title="My Podcast")
        assert str(feed) == "My Podcast"

    def test_feed_immutable(self):
        """Test that feed is immutable (frozen)."""
        from pydantic import ValidationError

        feed = Feed(key="key", title="Title")
        with pytest.raises(ValidationError):
            feed.title = "New Title"  # type: ignore

    def test_feed_start_position_default(self):
        """Test that start_position_ms defaults to 0."""
        feed = Feed(key="key", title="Title")
        assert feed.start_position_ms == 0
        assert feed.start_position_seconds == 0.0

    def test_feed_start_position_custom(self):
        """Test feed with custom start position."""
        feed = Feed(key="key", title="Title", start_position_ms=30000)
        assert feed.start_position_ms == 30000
        assert feed.start_position_seconds == 30.0

    def test_feed_with_start_position(self):
        """Test with_start_position method."""
        feed = Feed(key="key", title="Title")
        updated = feed.with_start_position(60000)
        assert updated.start_position_ms == 60000
        assert feed.start_position_ms == 0  # Original unchanged

    def test_feed_start_position_clamps_negative(self):
        """Test that with_start_position clamps negative values."""
        feed = Feed(key="key", title="Title", start_position_ms=30000)
        updated = feed.with_start_position(-5000)
        assert updated.start_position_ms == 0

    def test_feed_start_position_validation(self):
        """Test that start_position_ms must be non-negative."""
        with pytest.raises(ValueError):
            Feed(key="key", title="Title", start_position_ms=-1)


class TestEpisode:
    """Tests for the Episode model."""

    def test_create_episode_minimal(self):
        """Test creating an episode with minimal required fields."""
        episode = Episode(
            feed_key="feed1",
            title="Episode 1",
            enclosure="https://example.com/ep1.mp3",
        )
        assert episode.id is None
        assert episode.feed_key == "feed1"
        assert episode.title == "Episode 1"
        assert episode.enclosure == "https://example.com/ep1.mp3"
        assert episode.played is False
        assert episode.progress_ms == 0
        assert episode.downloaded_path is None

    def test_create_episode_full(self):
        """Test creating an episode with all fields."""
        now = datetime.now()
        episode = Episode(
            id=1,
            feed_key="feed1",
            title="Episode 1",
            description="Description",
            link="https://example.com/ep1",
            enclosure="https://example.com/ep1.mp3",
            pubdate=now,
            copyright="2024",
            played=True,
            progress_ms=60000,
            downloaded_path="/path/to/file.mp3",
        )
        assert episode.id == 1
        assert episode.description == "Description"
        assert episode.link == "https://example.com/ep1"
        assert episode.pubdate == now
        assert episode.copyright == "2024"
        assert episode.played is True
        assert episode.progress_ms == 60000
        assert episode.downloaded_path == "/path/to/file.mp3"

    def test_episode_str(self):
        """Test episode string representation."""
        episode = Episode(
            feed_key="feed1",
            title="My Episode",
            enclosure="https://example.com/ep.mp3",
        )
        assert str(episode) == "My Episode"

    def test_episode_is_downloaded(self):
        """Test is_downloaded property."""
        episode = Episode(
            feed_key="feed1",
            title="Episode",
            enclosure="https://example.com/ep.mp3",
        )
        assert episode.is_downloaded is False

        episode_downloaded = Episode(
            feed_key="feed1",
            title="Episode",
            enclosure="https://example.com/ep.mp3",
            downloaded_path="/path/to/file.mp3",
        )
        assert episode_downloaded.is_downloaded is True

    def test_episode_progress_seconds(self):
        """Test progress_seconds property."""
        episode = Episode(
            feed_key="feed1",
            title="Episode",
            enclosure="https://example.com/ep.mp3",
            progress_ms=90000,
        )
        assert episode.progress_seconds == 90.0

    def test_episode_with_progress(self):
        """Test with_progress method."""
        episode = Episode(
            feed_key="feed1",
            title="Episode",
            enclosure="https://example.com/ep.mp3",
        )
        updated = episode.with_progress(30000)
        assert updated.progress_ms == 30000
        assert episode.progress_ms == 0  # Original unchanged

    def test_episode_mark_played(self):
        """Test mark_played method."""
        episode = Episode(
            feed_key="feed1",
            title="Episode",
            enclosure="https://example.com/ep.mp3",
            progress_ms=30000,
        )
        played = episode.mark_played()
        assert played.played is True
        assert played.progress_ms == 0

    def test_episode_mark_unplayed(self):
        """Test mark_unplayed method."""
        episode = Episode(
            feed_key="feed1",
            title="Episode",
            enclosure="https://example.com/ep.mp3",
            played=True,
        )
        unplayed = episode.mark_unplayed()
        assert unplayed.played is False

    def test_episode_progress_validation(self):
        """Test that progress_ms must be non-negative."""
        with pytest.raises(ValueError):
            Episode(
                feed_key="feed1",
                title="Episode",
                enclosure="https://example.com/ep.mp3",
                progress_ms=-1,
            )


class TestQueueItem:
    """Tests for the QueueItem model."""

    def test_create_queue_item(self):
        """Test creating a queue item."""
        item = QueueItem(position=1, episode_id=42)
        assert item.position == 1
        assert item.episode_id == 42

    def test_queue_item_immutable(self):
        """Test that queue item is immutable (frozen)."""
        from pydantic import ValidationError

        item = QueueItem(position=1, episode_id=42)
        with pytest.raises(ValidationError):
            item.position = 2  # type: ignore
