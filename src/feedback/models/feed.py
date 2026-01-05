"""Feed and Episode models for feedback."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class Feed(BaseModel):
    """A podcast feed (RSS/Atom source)."""

    model_config = ConfigDict(frozen=True)

    key: str = Field(description="Unique identifier (URL or file path)")
    title: str = Field(description="Feed title")
    description: str = Field(default="", description="Feed description")
    link: str = Field(default="", description="Website link")
    last_build_date: datetime | None = Field(
        default=None, description="Last build date"
    )
    copyright: str | None = Field(default=None, description="Copyright notice")
    start_position_ms: Annotated[int, Field(ge=0)] = Field(
        default=0,
        description="Default start position in ms for new episodes (per-podcast setting)",
    )

    def __str__(self) -> str:
        """Return the feed title."""
        return self.title

    @property
    def start_position_seconds(self) -> float:
        """Get default start position in seconds."""
        return self.start_position_ms / 1000.0

    def with_start_position(self, start_position_ms: int) -> "Feed":
        """Return a copy with updated start position.

        Args:
            start_position_ms: New default start position in milliseconds.

        Returns:
            A new Feed instance with the updated start position.
        """
        return Feed(
            key=self.key,
            title=self.title,
            description=self.description,
            link=self.link,
            last_build_date=self.last_build_date,
            copyright=self.copyright,
            start_position_ms=max(0, start_position_ms),
        )


class Episode(BaseModel):
    """A single podcast episode."""

    model_config = ConfigDict(frozen=False)

    id: int | None = Field(default=None, description="Database ID")
    feed_key: str = Field(description="Parent feed key")
    title: str = Field(description="Episode title")
    description: str | None = Field(default=None, description="Episode description")
    link: str | None = Field(default=None, description="Episode webpage link")
    enclosure: str = Field(description="Media file URL")
    pubdate: datetime | None = Field(default=None, description="Publication date")
    copyright: str | None = Field(default=None, description="Copyright notice")
    played: bool = Field(default=False, description="Whether episode has been played")
    progress_ms: Annotated[int, Field(ge=0)] = Field(
        default=0, description="Playback progress in milliseconds"
    )
    downloaded_path: str | None = Field(
        default=None, description="Local file path if downloaded"
    )

    def __str__(self) -> str:
        """Return the episode title."""
        return self.title

    @property
    def is_downloaded(self) -> bool:
        """Check if the episode has been downloaded."""
        return self.downloaded_path is not None

    @property
    def progress_seconds(self) -> float:
        """Get playback progress in seconds."""
        return self.progress_ms / 1000.0

    def with_progress(self, progress_ms: int) -> "Episode":
        """Return a copy with updated progress."""
        return self.model_copy(update={"progress_ms": progress_ms})

    def mark_played(self) -> "Episode":
        """Return a copy marked as played with progress reset."""
        return self.model_copy(update={"played": True, "progress_ms": 0})

    def mark_unplayed(self) -> "Episode":
        """Return a copy marked as unplayed."""
        return self.model_copy(update={"played": False})


class QueueItem(BaseModel):
    """An item in the playback queue."""

    model_config = ConfigDict(frozen=True)

    position: int = Field(description="Position in queue (1-indexed)")
    episode_id: int = Field(description="Episode database ID")
