"""Base player interface for feedback."""

from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Protocol, runtime_checkable


class PlayerState(IntEnum):
    """Playback state of a player."""

    STOPPED = 0
    PLAYING = 1
    PAUSED = 2


@runtime_checkable
class Player(Protocol):
    """Protocol defining the player interface.

    All player implementations must satisfy this protocol.
    """

    @property
    def state(self) -> PlayerState:
        """Current playback state."""
        ...

    @property
    def position_ms(self) -> int:
        """Current playback position in milliseconds."""
        ...

    @property
    def duration_ms(self) -> int:
        """Total duration in milliseconds."""
        ...

    @property
    def volume(self) -> int:
        """Current volume (0-100)."""
        ...

    @property
    def rate(self) -> float:
        """Current playback rate (0.5-2.0)."""
        ...

    async def play(self, path: str, start_ms: int = 0) -> None:
        """Start playback from the given path.

        Args:
            path: URL or file path to play.
            start_ms: Starting position in milliseconds.
        """
        ...

    async def pause(self) -> None:
        """Pause playback."""
        ...

    async def resume(self) -> None:
        """Resume playback."""
        ...

    async def stop(self) -> None:
        """Stop playback."""
        ...

    async def seek(self, position_ms: int) -> None:
        """Seek to the given position.

        Args:
            position_ms: Target position in milliseconds.
        """
        ...

    async def set_volume(self, volume: int) -> None:
        """Set the playback volume.

        Args:
            volume: Volume level (0-100).
        """
        ...

    async def set_rate(self, rate: float) -> None:
        """Set the playback rate.

        Args:
            rate: Playback rate (0.5-2.0).
        """
        ...


class BasePlayer(ABC):
    """Abstract base class for player implementations.

    Provides common functionality and enforces the Player protocol.
    """

    MIN_VOLUME = 0
    MAX_VOLUME = 100
    MIN_RATE = 0.5
    MAX_RATE = 2.0

    def __init__(self) -> None:
        """Initialize the base player."""
        self._state = PlayerState.STOPPED
        self._volume = 100
        self._rate = 1.0
        self._position_ms = 0
        self._duration_ms = 0

    @property
    def state(self) -> PlayerState:
        """Current playback state."""
        return self._state

    @property
    def position_ms(self) -> int:
        """Current playback position in milliseconds."""
        return self._position_ms

    @property
    def duration_ms(self) -> int:
        """Total duration in milliseconds."""
        return self._duration_ms

    @property
    def volume(self) -> int:
        """Current volume (0-100)."""
        return self._volume

    @property
    def rate(self) -> float:
        """Current playback rate (0.5-2.0)."""
        return self._rate

    @property
    def time_remaining_ms(self) -> int:
        """Time remaining in milliseconds."""
        return max(0, self._duration_ms - self._position_ms)

    @property
    def progress_fraction(self) -> float:
        """Playback progress as a fraction (0.0-1.0)."""
        if self._duration_ms <= 0:
            return 0.0
        return min(1.0, self._position_ms / self._duration_ms)

    def format_time(self, ms: int) -> str:
        """Format milliseconds as HH:MM:SS.

        Args:
            ms: Time in milliseconds.

        Returns:
            Formatted time string.
        """
        seconds = max(0, ms // 1000)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @property
    def time_str(self) -> str:
        """Formatted current time / duration string."""
        return f"{self.format_time(self._position_ms)}/{self.format_time(self._duration_ms)}"

    def _clamp_volume(self, volume: int) -> int:
        """Clamp volume to valid range."""
        return max(self.MIN_VOLUME, min(self.MAX_VOLUME, volume))

    def _clamp_rate(self, rate: float) -> float:
        """Clamp rate to valid range."""
        return max(self.MIN_RATE, min(self.MAX_RATE, rate))

    @abstractmethod
    async def play(self, path: str, start_ms: int = 0) -> None:
        """Start playback from the given path."""
        ...

    @abstractmethod
    async def pause(self) -> None:
        """Pause playback."""
        ...

    @abstractmethod
    async def resume(self) -> None:
        """Resume playback."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop playback."""
        ...

    @abstractmethod
    async def seek(self, position_ms: int) -> None:
        """Seek to the given position."""
        ...

    @abstractmethod
    async def set_volume(self, volume: int) -> None:
        """Set the playback volume."""
        ...

    @abstractmethod
    async def set_rate(self, rate: float) -> None:
        """Set the playback rate."""
        ...


class NullPlayer(BasePlayer):
    """A no-op player implementation for testing."""

    async def play(self, _path: str, start_ms: int = 0) -> None:
        """Simulate starting playback."""
        self._state = PlayerState.PLAYING
        self._position_ms = start_ms
        self._duration_ms = 60000  # 1 minute default

    async def pause(self) -> None:
        """Simulate pausing playback."""
        if self._state == PlayerState.PLAYING:
            self._state = PlayerState.PAUSED

    async def resume(self) -> None:
        """Simulate resuming playback."""
        if self._state == PlayerState.PAUSED:
            self._state = PlayerState.PLAYING

    async def stop(self) -> None:
        """Simulate stopping playback."""
        self._state = PlayerState.STOPPED
        self._position_ms = 0

    async def seek(self, position_ms: int) -> None:
        """Simulate seeking."""
        self._position_ms = max(0, min(position_ms, self._duration_ms))

    async def set_volume(self, volume: int) -> None:
        """Set volume."""
        self._volume = self._clamp_volume(volume)

    async def set_rate(self, rate: float) -> None:
        """Set playback rate."""
        self._rate = self._clamp_rate(rate)
