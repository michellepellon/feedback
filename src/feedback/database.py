"""Async SQLite database layer for feedback."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from feedback.models import Episode, Feed, HistoryItem, QueueItem

# SQL schema
SCHEMA = """
CREATE TABLE IF NOT EXISTS feed (
    key TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    link TEXT DEFAULT '',
    last_build_date TEXT,
    copyright TEXT,
    start_position_ms INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS episode (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_key TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    link TEXT,
    enclosure TEXT NOT NULL,
    pubdate TEXT,
    copyright TEXT,
    played INTEGER DEFAULT 0,
    progress_ms INTEGER DEFAULT 0,
    downloaded_path TEXT,
    FOREIGN KEY (feed_key) REFERENCES feed(key) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS queue (
    position INTEGER PRIMARY KEY,
    episode_id INTEGER NOT NULL,
    FOREIGN KEY (episode_id) REFERENCES episode(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS playback_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER NOT NULL,
    played_at TEXT NOT NULL,
    duration_listened_ms INTEGER DEFAULT 0,
    FOREIGN KEY (episode_id) REFERENCES episode(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_episode_feed_key ON episode(feed_key);
CREATE INDEX IF NOT EXISTS idx_episode_played ON episode(played);
CREATE INDEX IF NOT EXISTS idx_history_played_at ON playback_history(played_at);
"""


class Database:
    """Async SQLite database for podcast data."""

    def __init__(self, path: Path) -> None:
        """Initialize the database.

        Args:
            path: Path to the SQLite database file.
        """
        self.path = path
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Connect to the database and ensure schema exists."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.executescript(SCHEMA)
        await self._run_migrations()
        await self._conn.commit()

    async def _run_migrations(self) -> None:
        """Run database migrations for schema updates."""
        if self._conn is None:
            return

        # Migration: Add start_position_ms column to feed table if missing
        async with self._conn.execute("PRAGMA table_info(feed)") as cursor:
            columns = await cursor.fetchall()
            column_names = [col["name"] for col in columns]

        if "start_position_ms" not in column_names:
            await self._conn.execute(
                "ALTER TABLE feed ADD COLUMN start_position_ms INTEGER DEFAULT 0"
            )

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """Context manager for database transactions."""
        if self._conn is None:
            raise RuntimeError("Database not connected")
        async with self._lock:
            try:
                yield self._conn
                await self._conn.commit()
            except Exception:
                await self._conn.rollback()
                raise

    # Feed operations

    async def get_feeds(self) -> list[Feed]:
        """Get all feeds ordered by title."""
        if self._conn is None:
            raise RuntimeError("Database not connected")

        async with self._conn.execute(
            "SELECT * FROM feed ORDER BY LOWER(title)"
        ) as cursor:
            rows = await cursor.fetchall()

        return [self._row_to_feed(row) for row in rows]

    async def get_feed(self, key: str) -> Feed | None:
        """Get a feed by its key."""
        if self._conn is None:
            raise RuntimeError("Database not connected")

        async with self._conn.execute(
            "SELECT * FROM feed WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()

        return self._row_to_feed(row) if row else None

    async def upsert_feed(self, feed: Feed) -> None:
        """Insert or update a feed."""
        async with self.transaction() as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO feed (key, title, description, link, last_build_date,
                                            copyright, start_position_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feed.key,
                    feed.title,
                    feed.description,
                    feed.link,
                    feed.last_build_date.isoformat() if feed.last_build_date else None,
                    feed.copyright,
                    feed.start_position_ms,
                ),
            )

    async def delete_feed(self, key: str) -> None:
        """Delete a feed and its episodes."""
        async with self.transaction() as conn:
            await conn.execute("DELETE FROM feed WHERE key = ?", (key,))

    async def update_feed_start_position(
        self, key: str, start_position_ms: int
    ) -> None:
        """Update the default start position for a feed.

        Args:
            key: The feed key (URL).
            start_position_ms: Default start position in milliseconds.
        """
        async with self.transaction() as conn:
            await conn.execute(
                "UPDATE feed SET start_position_ms = ? WHERE key = ?",
                (max(0, start_position_ms), key),
            )

    # Episode operations

    async def get_episodes(self, feed_key: str) -> list[Episode]:
        """Get all episodes for a feed."""
        if self._conn is None:
            raise RuntimeError("Database not connected")

        async with self._conn.execute(
            "SELECT * FROM episode WHERE feed_key = ? ORDER BY id DESC",
            (feed_key,),
        ) as cursor:
            rows = await cursor.fetchall()

        return [self._row_to_episode(row) for row in rows]

    async def get_episode(self, episode_id: int) -> Episode | None:
        """Get an episode by its ID."""
        if self._conn is None:
            raise RuntimeError("Database not connected")

        async with self._conn.execute(
            "SELECT * FROM episode WHERE id = ?", (episode_id,)
        ) as cursor:
            row = await cursor.fetchone()

        return self._row_to_episode(row) if row else None

    async def get_unplayed_episodes(self, feed_key: str) -> list[Episode]:
        """Get unplayed episodes for a feed."""
        if self._conn is None:
            raise RuntimeError("Database not connected")

        async with self._conn.execute(
            "SELECT * FROM episode WHERE feed_key = ? AND played = 0 ORDER BY id DESC",
            (feed_key,),
        ) as cursor:
            rows = await cursor.fetchall()

        return [self._row_to_episode(row) for row in rows]

    async def upsert_episode(self, episode: Episode) -> int:
        """Insert or update an episode. Returns the episode ID."""
        async with self.transaction() as conn:
            if episode.id is None:
                cursor = await conn.execute(
                    """
                    INSERT INTO episode (feed_key, title, description, link, enclosure,
                                        pubdate, copyright, played, progress_ms, downloaded_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        episode.feed_key,
                        episode.title,
                        episode.description,
                        episode.link,
                        episode.enclosure,
                        episode.pubdate.isoformat() if episode.pubdate else None,
                        episode.copyright,
                        1 if episode.played else 0,
                        episode.progress_ms,
                        episode.downloaded_path,
                    ),
                )
                return cursor.lastrowid or 0
            else:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO episode (id, feed_key, title, description, link, enclosure,
                                                   pubdate, copyright, played, progress_ms, downloaded_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        episode.id,
                        episode.feed_key,
                        episode.title,
                        episode.description,
                        episode.link,
                        episode.enclosure,
                        episode.pubdate.isoformat() if episode.pubdate else None,
                        episode.copyright,
                        1 if episode.played else 0,
                        episode.progress_ms,
                        episode.downloaded_path,
                    ),
                )
                return episode.id

    async def upsert_episodes(self, episodes: list[Episode]) -> None:
        """Bulk insert or update episodes."""
        for episode in episodes:
            await self.upsert_episode(episode)

    async def update_progress(self, episode_id: int, progress_ms: int) -> None:
        """Update the playback progress for an episode."""
        async with self.transaction() as conn:
            await conn.execute(
                "UPDATE episode SET progress_ms = ? WHERE id = ?",
                (progress_ms, episode_id),
            )

    async def mark_played(self, episode_id: int, played: bool = True) -> None:
        """Mark an episode as played/unplayed."""
        async with self.transaction() as conn:
            await conn.execute(
                "UPDATE episode SET played = ?, progress_ms = 0 WHERE id = ?",
                (1 if played else 0, episode_id),
            )

    async def mark_all_played(self, feed_key: str, played: bool = True) -> int:
        """Mark all episodes of a feed as played/unplayed.

        Args:
            feed_key: The feed key.
            played: True to mark as played, False for unplayed.

        Returns:
            Number of episodes updated.
        """
        async with self.transaction() as conn:
            cursor = await conn.execute(
                "UPDATE episode SET played = ?, progress_ms = 0 WHERE feed_key = ?",
                (1 if played else 0, feed_key),
            )
            return cursor.rowcount

    async def get_episode_count(self, feed_key: str) -> tuple[int, int]:
        """Get episode counts for a feed.

        Args:
            feed_key: The feed key.

        Returns:
            Tuple of (total_count, unplayed_count).
        """
        if self._conn is None:
            raise RuntimeError("Database not connected")

        async with self._conn.execute(
            "SELECT COUNT(*) FROM episode WHERE feed_key = ?", (feed_key,)
        ) as cursor:
            total = (await cursor.fetchone())[0]

        async with self._conn.execute(
            "SELECT COUNT(*) FROM episode WHERE feed_key = ? AND played = 0",
            (feed_key,),
        ) as cursor:
            unplayed = (await cursor.fetchone())[0]

        return total, unplayed

    async def delete_episode(self, episode_id: int) -> None:
        """Delete an episode."""
        async with self.transaction() as conn:
            await conn.execute("DELETE FROM episode WHERE id = ?", (episode_id,))

    # Queue operations

    async def get_queue(self) -> list[QueueItem]:
        """Get the playback queue."""
        if self._conn is None:
            raise RuntimeError("Database not connected")

        async with self._conn.execute(
            "SELECT position, episode_id FROM queue ORDER BY position"
        ) as cursor:
            rows = await cursor.fetchall()

        return [
            QueueItem(position=row["position"], episode_id=row["episode_id"])
            for row in rows
        ]

    async def save_queue(self, items: list[QueueItem]) -> None:
        """Save the playback queue (replaces existing)."""
        async with self.transaction() as conn:
            await conn.execute("DELETE FROM queue")
            for item in items:
                await conn.execute(
                    "INSERT INTO queue (position, episode_id) VALUES (?, ?)",
                    (item.position, item.episode_id),
                )

    async def clear_queue(self) -> None:
        """Clear the playback queue."""
        async with self.transaction() as conn:
            await conn.execute("DELETE FROM queue")

    # Playback history operations

    async def add_to_history(
        self, episode_id: int, duration_listened_ms: int = 0
    ) -> HistoryItem:
        """Add an episode to playback history.

        Args:
            episode_id: Episode database ID.
            duration_listened_ms: How long the user listened.

        Returns:
            The created history item.
        """
        from datetime import datetime

        if self._conn is None:
            raise RuntimeError("Database not connected")

        played_at = datetime.now()
        async with self.transaction() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO playback_history (episode_id, played_at, duration_listened_ms)
                VALUES (?, ?, ?)
                """,
                (episode_id, played_at.isoformat(), duration_listened_ms),
            )
            history_id = cursor.lastrowid

        return HistoryItem(
            id=history_id,
            episode_id=episode_id,
            played_at=played_at,
            duration_listened_ms=duration_listened_ms,
        )

    async def get_history(self, limit: int = 50) -> list[tuple[HistoryItem, Episode]]:
        """Get playback history with episode details.

        Args:
            limit: Maximum number of history items to return.

        Returns:
            List of (HistoryItem, Episode) tuples, newest first.
        """
        if self._conn is None:
            raise RuntimeError("Database not connected")

        async with self._conn.execute(
            """
            SELECT h.id, h.episode_id, h.played_at, h.duration_listened_ms,
                   e.id as e_id, e.feed_key, e.title, e.description, e.link,
                   e.enclosure, e.pubdate, e.copyright, e.played, e.progress_ms,
                   e.downloaded_path
            FROM playback_history h
            JOIN episode e ON h.episode_id = e.id
            ORDER BY h.played_at DESC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()

        return [self._rows_to_history_item(row) for row in rows]

    async def clear_history(self) -> int:
        """Clear all playback history.

        Returns:
            Number of items cleared.
        """
        if self._conn is None:
            raise RuntimeError("Database not connected")

        async with self.transaction() as conn:
            cursor = await conn.execute("DELETE FROM playback_history")
            return cursor.rowcount

    @staticmethod
    def _rows_to_history_item(row: aiosqlite.Row) -> tuple[HistoryItem, Episode]:
        """Convert a joined row to HistoryItem and Episode."""
        import contextlib
        from datetime import datetime

        played_at = datetime.fromisoformat(row["played_at"])

        history = HistoryItem(
            id=row["id"],
            episode_id=row["episode_id"],
            played_at=played_at,
            duration_listened_ms=row["duration_listened_ms"] or 0,
        )

        pubdate = None
        if row["pubdate"]:
            with contextlib.suppress(ValueError):
                pubdate = datetime.fromisoformat(row["pubdate"])

        episode = Episode(
            id=row["e_id"],
            feed_key=row["feed_key"],
            title=row["title"],
            description=row["description"],
            link=row["link"],
            enclosure=row["enclosure"],
            pubdate=pubdate,
            copyright=row["copyright"],
            played=bool(row["played"]),
            progress_ms=row["progress_ms"] or 0,
            downloaded_path=row["downloaded_path"],
        )

        return history, episode

    # Helper methods

    @staticmethod
    def _row_to_feed(row: aiosqlite.Row) -> Feed:
        """Convert a database row to a Feed model."""
        import contextlib
        from datetime import datetime

        last_build_date = None
        if row["last_build_date"]:
            with contextlib.suppress(ValueError):
                last_build_date = datetime.fromisoformat(row["last_build_date"])

        return Feed(
            key=row["key"],
            title=row["title"],
            description=row["description"] or "",
            link=row["link"] or "",
            last_build_date=last_build_date,
            copyright=row["copyright"],
            start_position_ms=row["start_position_ms"] or 0,
        )

    @staticmethod
    def _row_to_episode(row: aiosqlite.Row) -> Episode:
        """Convert a database row to an Episode model."""
        import contextlib
        from datetime import datetime

        pubdate = None
        if row["pubdate"]:
            with contextlib.suppress(ValueError):
                pubdate = datetime.fromisoformat(row["pubdate"])

        return Episode(
            id=row["id"],
            feed_key=row["feed_key"],
            title=row["title"],
            description=row["description"],
            link=row["link"],
            enclosure=row["enclosure"],
            pubdate=pubdate,
            copyright=row["copyright"],
            played=bool(row["played"]),
            progress_ms=row["progress_ms"] or 0,
            downloaded_path=row["downloaded_path"],
        )


@asynccontextmanager
async def get_database(path: Path) -> AsyncIterator[Database]:
    """Context manager for database access.

    Args:
        path: Path to the SQLite database file.

    Yields:
        Connected database instance.
    """
    db = Database(path)
    await db.connect()
    try:
        yield db
    finally:
        await db.close()
