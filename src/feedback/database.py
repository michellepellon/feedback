"""Async SQLite database layer for feedback."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from feedback.models import Episode, Feed, QueueItem

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

CREATE INDEX IF NOT EXISTS idx_episode_feed_key ON episode(feed_key);
CREATE INDEX IF NOT EXISTS idx_episode_played ON episode(played);
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
