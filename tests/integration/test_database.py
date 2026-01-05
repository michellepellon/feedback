"""Integration tests for feedback database."""

from pathlib import Path

import pytest

from feedback.database import Database, get_database
from feedback.models import Episode, Feed, QueueItem


class TestDatabaseConnection:
    """Tests for database connection."""

    @pytest.mark.asyncio
    async def test_connect_creates_file(self, temp_db_path: Path):
        """Test that connect creates the database file."""
        db = Database(temp_db_path)
        await db.connect()
        try:
            assert temp_db_path.exists()
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_connect_creates_parent_dirs(self, temp_dir: Path):
        """Test that connect creates parent directories."""
        db_path = temp_dir / "subdir" / "nested" / "test.db"
        db = Database(db_path)
        await db.connect()
        try:
            assert db_path.exists()
        finally:
            await db.close()

    @pytest.mark.asyncio
    async def test_close(self, temp_db_path: Path):
        """Test closing the database."""
        db = Database(temp_db_path)
        await db.connect()
        await db.close()
        assert db._conn is None

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self, temp_db_path: Path):
        """Test closing when already closed or never connected."""
        db = Database(temp_db_path)
        # Should not raise - close on never-connected db
        await db.close()
        assert db._conn is None

    @pytest.mark.asyncio
    async def test_get_database_context_manager(self, temp_db_path: Path):
        """Test get_database context manager."""
        async with get_database(temp_db_path) as db:
            assert db._conn is not None
        assert db._conn is None


class TestFeedOperations:
    """Tests for feed database operations."""

    @pytest.mark.asyncio
    async def test_upsert_and_get_feed(self, database: Database):
        """Test inserting and retrieving a feed."""
        feed = Feed(
            key="https://example.com/feed",
            title="Test Feed",
            description="A test feed",
            link="https://example.com",
        )
        await database.upsert_feed(feed)

        result = await database.get_feed("https://example.com/feed")
        assert result is not None
        assert result.key == feed.key
        assert result.title == feed.title
        assert result.description == feed.description

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(self, database: Database):
        """Test that upsert updates existing feed."""
        feed1 = Feed(key="feed1", title="Original")
        await database.upsert_feed(feed1)

        feed2 = Feed(key="feed1", title="Updated")
        await database.upsert_feed(feed2)

        result = await database.get_feed("feed1")
        assert result is not None
        assert result.title == "Updated"

    @pytest.mark.asyncio
    async def test_get_feeds(self, database: Database):
        """Test getting all feeds."""
        await database.upsert_feed(Feed(key="feed2", title="Bravo"))
        await database.upsert_feed(Feed(key="feed1", title="Alpha"))
        await database.upsert_feed(Feed(key="feed3", title="Charlie"))

        feeds = await database.get_feeds()
        assert len(feeds) == 3
        # Ordered by title (case insensitive)
        assert feeds[0].title == "Alpha"
        assert feeds[1].title == "Bravo"
        assert feeds[2].title == "Charlie"

    @pytest.mark.asyncio
    async def test_get_feed_not_found(self, database: Database):
        """Test getting a non-existent feed."""
        result = await database.get_feed("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_feed(self, database: Database):
        """Test deleting a feed."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        await database.delete_feed("feed1")
        result = await database.get_feed("feed1")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_feed_cascades_episodes(self, database: Database):
        """Test that deleting a feed also deletes its episodes."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep1", enclosure="url1")
        )
        await database.delete_feed("feed1")
        episodes = await database.get_episodes("feed1")
        assert len(episodes) == 0


class TestEpisodeOperations:
    """Tests for episode database operations."""

    @pytest.mark.asyncio
    async def test_upsert_and_get_episodes(self, database: Database):
        """Test inserting and retrieving episodes."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        episode = Episode(
            feed_key="feed1",
            title="Episode 1",
            description="First episode",
            enclosure="https://example.com/ep1.mp3",
        )
        episode_id = await database.upsert_episode(episode)
        assert episode_id > 0

        episodes = await database.get_episodes("feed1")
        assert len(episodes) == 1
        assert episodes[0].title == "Episode 1"
        assert episodes[0].id == episode_id

    @pytest.mark.asyncio
    async def test_get_episode_by_id(self, database: Database):
        """Test getting episode by ID."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        episode_id = await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep1", enclosure="url1")
        )

        result = await database.get_episode(episode_id)
        assert result is not None
        assert result.id == episode_id
        assert result.title == "Ep1"

    @pytest.mark.asyncio
    async def test_get_unplayed_episodes(self, database: Database):
        """Test getting unplayed episodes."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))

        ep1_id = await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep1", enclosure="url1", played=False)
        )
        await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep2", enclosure="url2", played=True)
        )
        ep3_id = await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep3", enclosure="url3", played=False)
        )

        unplayed = await database.get_unplayed_episodes("feed1")
        assert len(unplayed) == 2
        unplayed_ids = {ep.id for ep in unplayed}
        assert ep1_id in unplayed_ids
        assert ep3_id in unplayed_ids

    @pytest.mark.asyncio
    async def test_upsert_episodes_bulk(self, database: Database):
        """Test bulk upserting episodes."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        episodes = [
            Episode(feed_key="feed1", title=f"Ep{i}", enclosure=f"url{i}")
            for i in range(5)
        ]
        await database.upsert_episodes(episodes)

        result = await database.get_episodes("feed1")
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_update_progress(self, database: Database):
        """Test updating episode progress."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        episode_id = await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep1", enclosure="url1")
        )

        await database.update_progress(episode_id, 30000)
        result = await database.get_episode(episode_id)
        assert result is not None
        assert result.progress_ms == 30000

    @pytest.mark.asyncio
    async def test_mark_played(self, database: Database):
        """Test marking episode as played."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        episode_id = await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep1", enclosure="url1", progress_ms=30000)
        )

        await database.mark_played(episode_id, played=True)
        result = await database.get_episode(episode_id)
        assert result is not None
        assert result.played is True
        assert result.progress_ms == 0  # Reset on mark played

    @pytest.mark.asyncio
    async def test_mark_unplayed(self, database: Database):
        """Test marking episode as unplayed."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        episode_id = await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep1", enclosure="url1", played=True)
        )

        await database.mark_played(episode_id, played=False)
        result = await database.get_episode(episode_id)
        assert result is not None
        assert result.played is False

    @pytest.mark.asyncio
    async def test_delete_episode(self, database: Database):
        """Test deleting an episode."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        episode_id = await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep1", enclosure="url1")
        )

        await database.delete_episode(episode_id)
        result = await database.get_episode(episode_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_mark_all_played(self, database: Database):
        """Test marking all episodes of a feed as played."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep1", enclosure="url1")
        )
        await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep2", enclosure="url2")
        )
        await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep3", enclosure="url3")
        )

        count = await database.mark_all_played("feed1", played=True)
        assert count == 3

        episodes = await database.get_episodes("feed1")
        assert all(ep.played for ep in episodes)

    @pytest.mark.asyncio
    async def test_mark_all_unplayed(self, database: Database):
        """Test marking all episodes of a feed as unplayed."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep1", enclosure="url1", played=True)
        )
        await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep2", enclosure="url2", played=True)
        )

        count = await database.mark_all_played("feed1", played=False)
        assert count == 2

        episodes = await database.get_episodes("feed1")
        assert all(not ep.played for ep in episodes)

    @pytest.mark.asyncio
    async def test_get_episode_count(self, database: Database):
        """Test getting episode counts for a feed."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep1", enclosure="url1", played=False)
        )
        await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep2", enclosure="url2", played=True)
        )
        await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep3", enclosure="url3", played=False)
        )

        total, unplayed = await database.get_episode_count("feed1")
        assert total == 3
        assert unplayed == 2


class TestQueueOperations:
    """Tests for queue database operations."""

    @pytest.mark.asyncio
    async def test_save_and_get_queue(self, database: Database):
        """Test saving and retrieving queue."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        ep1_id = await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep1", enclosure="url1")
        )
        ep2_id = await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep2", enclosure="url2")
        )

        queue = [
            QueueItem(position=1, episode_id=ep1_id),
            QueueItem(position=2, episode_id=ep2_id),
        ]
        await database.save_queue(queue)

        result = await database.get_queue()
        assert len(result) == 2
        assert result[0].position == 1
        assert result[0].episode_id == ep1_id
        assert result[1].position == 2
        assert result[1].episode_id == ep2_id

    @pytest.mark.asyncio
    async def test_save_queue_replaces_existing(self, database: Database):
        """Test that saving queue replaces existing."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        ep1_id = await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep1", enclosure="url1")
        )
        ep2_id = await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep2", enclosure="url2")
        )

        # Save initial queue
        await database.save_queue([QueueItem(position=1, episode_id=ep1_id)])

        # Save new queue
        await database.save_queue([QueueItem(position=1, episode_id=ep2_id)])

        result = await database.get_queue()
        assert len(result) == 1
        assert result[0].episode_id == ep2_id

    @pytest.mark.asyncio
    async def test_clear_queue(self, database: Database):
        """Test clearing the queue."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        ep_id = await database.upsert_episode(
            Episode(feed_key="feed1", title="Ep1", enclosure="url1")
        )

        await database.save_queue([QueueItem(position=1, episode_id=ep_id)])
        await database.clear_queue()

        result = await database.get_queue()
        assert len(result) == 0


class TestDatabaseTransactions:
    """Tests for database transaction handling."""

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, database: Database):
        """Test that transactions rollback on error."""
        await database.upsert_feed(Feed(key="feed1", title="Original"))

        # This should fail and rollback
        try:
            async with database.transaction() as conn:
                await conn.execute(
                    "UPDATE feed SET title = ? WHERE key = ?",
                    ("Modified", "feed1"),
                )
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Title should be unchanged
        feed = await database.get_feed("feed1")
        assert feed is not None
        assert feed.title == "Original"


class TestDatabaseNotConnected:
    """Tests for database operations when not connected."""

    @pytest.mark.asyncio
    async def test_get_feeds_not_connected(self, temp_db_path: Path):
        """Test get_feeds raises when not connected."""
        db = Database(temp_db_path)
        with pytest.raises(RuntimeError, match="not connected"):
            await db.get_feeds()

    @pytest.mark.asyncio
    async def test_get_feed_not_connected(self, temp_db_path: Path):
        """Test get_feed raises when not connected."""
        db = Database(temp_db_path)
        with pytest.raises(RuntimeError, match="not connected"):
            await db.get_feed("key")

    @pytest.mark.asyncio
    async def test_get_episodes_not_connected(self, temp_db_path: Path):
        """Test get_episodes raises when not connected."""
        db = Database(temp_db_path)
        with pytest.raises(RuntimeError, match="not connected"):
            await db.get_episodes("feed1")

    @pytest.mark.asyncio
    async def test_transaction_not_connected(self, temp_db_path: Path):
        """Test transaction raises when not connected."""
        db = Database(temp_db_path)
        with pytest.raises(RuntimeError, match="not connected"):
            async with db.transaction():
                pass

    @pytest.mark.asyncio
    async def test_get_episode_not_connected(self, temp_db_path: Path):
        """Test get_episode raises when not connected."""
        db = Database(temp_db_path)
        with pytest.raises(RuntimeError, match="not connected"):
            await db.get_episode(1)

    @pytest.mark.asyncio
    async def test_get_unplayed_episodes_not_connected(self, temp_db_path: Path):
        """Test get_unplayed_episodes raises when not connected."""
        db = Database(temp_db_path)
        with pytest.raises(RuntimeError, match="not connected"):
            await db.get_unplayed_episodes("feed1")

    @pytest.mark.asyncio
    async def test_get_queue_not_connected(self, temp_db_path: Path):
        """Test get_queue raises when not connected."""
        db = Database(temp_db_path)
        with pytest.raises(RuntimeError, match="not connected"):
            await db.get_queue()


class TestEpisodeUpdateWithExistingId:
    """Tests for updating episodes with existing IDs."""

    @pytest.mark.asyncio
    async def test_upsert_episode_with_existing_id(self, database: Database):
        """Test upserting an episode with an existing ID updates it."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))

        # Insert initial episode
        episode = Episode(
            feed_key="feed1",
            title="Original Title",
            enclosure="url1",
        )
        episode_id = await database.upsert_episode(episode)

        # Update with the same ID
        updated_episode = Episode(
            id=episode_id,
            feed_key="feed1",
            title="Updated Title",
            enclosure="url1",
            played=True,
            progress_ms=5000,
        )
        result_id = await database.upsert_episode(updated_episode)
        assert result_id == episode_id

        # Verify the update
        result = await database.get_episode(episode_id)
        assert result is not None
        assert result.title == "Updated Title"
        assert result.played is True
        assert result.progress_ms == 5000


class TestDatabaseDateParsing:
    """Tests for date parsing in database."""

    @pytest.mark.asyncio
    async def test_invalid_feed_date_handled(self, database: Database):
        """Test that invalid dates in feeds are handled gracefully."""
        # Directly insert a feed with invalid date
        async with database.transaction() as conn:
            await conn.execute(
                """INSERT INTO feed (key, title, description, link, last_build_date)
                   VALUES (?, ?, ?, ?, ?)""",
                ("feed1", "Test", "", "", "not-a-valid-date"),
            )

        feed = await database.get_feed("feed1")
        assert feed is not None
        assert feed.last_build_date is None  # Should be None due to parse error

    @pytest.mark.asyncio
    async def test_invalid_episode_date_handled(self, database: Database):
        """Test that invalid dates in episodes are handled gracefully."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))

        # Directly insert an episode with invalid date
        async with database.transaction() as conn:
            await conn.execute(
                """INSERT INTO episode (feed_key, title, enclosure, pubdate)
                   VALUES (?, ?, ?, ?)""",
                ("feed1", "Episode", "url", "invalid-date-format"),
            )

        episodes = await database.get_episodes("feed1")
        assert len(episodes) == 1
        assert episodes[0].pubdate is None  # Should be None due to parse error


class TestFeedStartPosition:
    """Tests for per-podcast start position feature."""

    @pytest.mark.asyncio
    async def test_feed_start_position_default(self, database: Database):
        """Test that start_position_ms defaults to 0."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        feed = await database.get_feed("feed1")
        assert feed is not None
        assert feed.start_position_ms == 0

    @pytest.mark.asyncio
    async def test_feed_start_position_persists(self, database: Database):
        """Test that start_position_ms is persisted."""
        feed = Feed(key="feed1", title="Test", start_position_ms=30000)
        await database.upsert_feed(feed)

        result = await database.get_feed("feed1")
        assert result is not None
        assert result.start_position_ms == 30000

    @pytest.mark.asyncio
    async def test_update_feed_start_position(self, database: Database):
        """Test updating start position for a feed."""
        await database.upsert_feed(Feed(key="feed1", title="Test"))
        await database.update_feed_start_position("feed1", 60000)

        feed = await database.get_feed("feed1")
        assert feed is not None
        assert feed.start_position_ms == 60000

    @pytest.mark.asyncio
    async def test_update_feed_start_position_clamps_negative(self, database: Database):
        """Test that negative start positions are clamped to 0."""
        await database.upsert_feed(
            Feed(key="feed1", title="Test", start_position_ms=30000)
        )
        await database.update_feed_start_position("feed1", -5000)

        feed = await database.get_feed("feed1")
        assert feed is not None
        assert feed.start_position_ms == 0

    @pytest.mark.asyncio
    async def test_feed_start_position_preserved_on_upsert(self, database: Database):
        """Test that start_position_ms is preserved when upserting."""
        feed1 = Feed(key="feed1", title="Original", start_position_ms=45000)
        await database.upsert_feed(feed1)

        # Upsert with different title but keep start position
        feed2 = Feed(key="feed1", title="Updated", start_position_ms=45000)
        await database.upsert_feed(feed2)

        result = await database.get_feed("feed1")
        assert result is not None
        assert result.title == "Updated"
        assert result.start_position_ms == 45000


class TestPlaybackHistory:
    """Tests for playback history operations."""

    @pytest.mark.asyncio
    async def test_add_to_history(self, database: Database):
        """Test adding an episode to playback history."""
        await database.upsert_feed(Feed(key="feed1", title="Test Feed"))
        episode = Episode(
            feed_key="feed1",
            title="Test Episode",
            enclosure="http://example.com/ep.mp3",
        )
        await database.upsert_episode(episode)

        # Get episode ID
        episodes = await database.get_episodes("feed1")
        ep_id = episodes[0].id
        assert ep_id is not None

        # Add to history
        history_item = await database.add_to_history(ep_id, duration_listened_ms=60000)

        assert history_item.episode_id == ep_id
        assert history_item.duration_listened_ms == 60000
        assert history_item.id is not None

    @pytest.mark.asyncio
    async def test_get_history(self, database: Database):
        """Test retrieving playback history."""
        await database.upsert_feed(Feed(key="feed1", title="Test Feed"))
        episode = Episode(
            feed_key="feed1",
            title="Test Episode",
            enclosure="http://example.com/ep.mp3",
        )
        await database.upsert_episode(episode)

        episodes = await database.get_episodes("feed1")
        ep_id = episodes[0].id
        assert ep_id is not None

        await database.add_to_history(ep_id, duration_listened_ms=30000)

        history = await database.get_history(limit=50)

        assert len(history) == 1
        hist_item, ep = history[0]
        assert hist_item.episode_id == ep_id
        assert hist_item.duration_listened_ms == 30000
        assert ep.title == "Test Episode"

    @pytest.mark.asyncio
    async def test_get_history_ordered_by_time(self, database: Database):
        """Test that history is ordered by played_at descending."""
        await database.upsert_feed(Feed(key="feed1", title="Test Feed"))

        for i in range(3):
            episode = Episode(
                feed_key="feed1",
                title=f"Episode {i+1}",
                enclosure=f"http://example.com/ep{i+1}.mp3",
            )
            await database.upsert_episode(episode)

        episodes = await database.get_episodes("feed1")

        # Add in order - save episode IDs by title
        ep_by_title = {ep.title: ep for ep in episodes}

        # Add in specific order: 1, 2, 3
        for title in ["Episode 1", "Episode 2", "Episode 3"]:
            ep = ep_by_title[title]
            assert ep.id is not None
            await database.add_to_history(ep.id)

        history = await database.get_history(limit=50)

        # Should be in reverse order (newest first): 3, 2, 1
        assert len(history) == 3
        # The last added (Episode 3) should be first in history
        assert history[0][1].title == "Episode 3"
        assert history[1][1].title == "Episode 2"
        assert history[2][1].title == "Episode 1"

    @pytest.mark.asyncio
    async def test_get_history_respects_limit(self, database: Database):
        """Test that history limit is respected."""
        await database.upsert_feed(Feed(key="feed1", title="Test Feed"))

        for i in range(5):
            episode = Episode(
                feed_key="feed1",
                title=f"Episode {i+1}",
                enclosure=f"http://example.com/ep{i+1}.mp3",
            )
            await database.upsert_episode(episode)

        episodes = await database.get_episodes("feed1")
        for ep in episodes:
            assert ep.id is not None
            await database.add_to_history(ep.id)

        history = await database.get_history(limit=3)
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_clear_history(self, database: Database):
        """Test clearing all playback history."""
        await database.upsert_feed(Feed(key="feed1", title="Test Feed"))
        episode = Episode(
            feed_key="feed1",
            title="Test Episode",
            enclosure="http://example.com/ep.mp3",
        )
        await database.upsert_episode(episode)

        episodes = await database.get_episodes("feed1")
        ep_id = episodes[0].id
        assert ep_id is not None

        await database.add_to_history(ep_id)
        await database.add_to_history(ep_id)

        count = await database.clear_history()
        assert count == 2

        history = await database.get_history()
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_add_to_history_not_connected(self, temp_db_path: Path):
        """Test add_to_history raises when not connected."""
        db = Database(temp_db_path)
        with pytest.raises(RuntimeError, match="not connected"):
            await db.add_to_history(1)

    @pytest.mark.asyncio
    async def test_get_history_not_connected(self, temp_db_path: Path):
        """Test get_history raises when not connected."""
        db = Database(temp_db_path)
        with pytest.raises(RuntimeError, match="not connected"):
            await db.get_history()

    @pytest.mark.asyncio
    async def test_clear_history_not_connected(self, temp_db_path: Path):
        """Test clear_history raises when not connected."""
        db = Database(temp_db_path)
        with pytest.raises(RuntimeError, match="not connected"):
            await db.clear_history()
