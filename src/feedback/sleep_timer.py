"""Sleep timer for automatic playback stopping."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable


class SleepTimerMode(Enum):
    """Sleep timer modes."""

    OFF = "off"
    MINUTES_15 = "15min"
    MINUTES_30 = "30min"
    MINUTES_45 = "45min"
    MINUTES_60 = "60min"
    END_OF_EPISODE = "end_of_episode"

    @property
    def label(self) -> str:
        """Get human-readable label for the mode."""
        labels = {
            SleepTimerMode.OFF: "Off",
            SleepTimerMode.MINUTES_15: "15 minutes",
            SleepTimerMode.MINUTES_30: "30 minutes",
            SleepTimerMode.MINUTES_45: "45 minutes",
            SleepTimerMode.MINUTES_60: "60 minutes",
            SleepTimerMode.END_OF_EPISODE: "End of episode",
        }
        return labels.get(self, "Unknown")

    @property
    def minutes(self) -> int | None:
        """Get duration in minutes, or None for end of episode."""
        durations = {
            SleepTimerMode.OFF: None,
            SleepTimerMode.MINUTES_15: 15,
            SleepTimerMode.MINUTES_30: 30,
            SleepTimerMode.MINUTES_45: 45,
            SleepTimerMode.MINUTES_60: 60,
            SleepTimerMode.END_OF_EPISODE: None,
        }
        return durations.get(self)


@dataclass
class SleepTimerState:
    """Current state of the sleep timer."""

    mode: SleepTimerMode
    end_time: datetime | None = None
    paused_remaining: timedelta | None = None

    @property
    def is_active(self) -> bool:
        """Check if timer is active."""
        return self.mode != SleepTimerMode.OFF

    @property
    def remaining_seconds(self) -> int | None:
        """Get remaining seconds, or None if end of episode mode."""
        if self.mode == SleepTimerMode.OFF:
            return None
        if self.mode == SleepTimerMode.END_OF_EPISODE:
            return None
        if self.paused_remaining is not None:
            return int(self.paused_remaining.total_seconds())
        if self.end_time is None:
            return None
        remaining = (self.end_time - datetime.now()).total_seconds()
        return max(0, int(remaining))

    @property
    def remaining_formatted(self) -> str:
        """Get formatted remaining time string."""
        if self.mode == SleepTimerMode.OFF:
            return ""
        if self.mode == SleepTimerMode.END_OF_EPISODE:
            return "End of episode"
        seconds = self.remaining_seconds
        if seconds is None:
            return ""
        minutes, secs = divmod(seconds, 60)
        return f"{minutes}:{secs:02d}"


class SleepTimer:
    """Sleep timer that stops playback after a set duration."""

    # All available modes in cycle order
    MODES: ClassVar[list[SleepTimerMode]] = [
        SleepTimerMode.OFF,
        SleepTimerMode.MINUTES_15,
        SleepTimerMode.MINUTES_30,
        SleepTimerMode.MINUTES_45,
        SleepTimerMode.MINUTES_60,
        SleepTimerMode.END_OF_EPISODE,
    ]

    def __init__(self, on_expire: Callable[[], None] | None = None) -> None:
        """Initialize the sleep timer.

        Args:
            on_expire: Callback to invoke when timer expires.
        """
        self._state = SleepTimerState(mode=SleepTimerMode.OFF)
        self._on_expire = on_expire
        self._timer_task: asyncio.Task[None] | None = None

    @property
    def state(self) -> SleepTimerState:
        """Get current timer state."""
        return self._state

    @property
    def mode(self) -> SleepTimerMode:
        """Get current timer mode."""
        return self._state.mode

    @property
    def is_active(self) -> bool:
        """Check if timer is active."""
        return self._state.is_active

    def set_mode(self, mode: SleepTimerMode) -> None:
        """Set the timer mode and start/stop accordingly.

        Args:
            mode: The timer mode to set.
        """
        # Cancel existing timer
        self._cancel_timer()

        if mode == SleepTimerMode.OFF:
            self._state = SleepTimerState(mode=SleepTimerMode.OFF)
            return

        if mode == SleepTimerMode.END_OF_EPISODE:
            self._state = SleepTimerState(mode=mode)
            return

        # Calculate end time for timed modes
        minutes = mode.minutes
        if minutes is not None:
            end_time = datetime.now() + timedelta(minutes=minutes)
            self._state = SleepTimerState(mode=mode, end_time=end_time)
            self._start_timer(minutes * 60)

    def cycle_mode(self) -> SleepTimerMode:
        """Cycle to the next timer mode.

        Returns:
            The new mode.
        """
        current_index = self.MODES.index(self._state.mode)
        next_index = (current_index + 1) % len(self.MODES)
        next_mode = self.MODES[next_index]
        self.set_mode(next_mode)
        return next_mode

    def cancel(self) -> None:
        """Cancel the timer."""
        self._cancel_timer()
        self._state = SleepTimerState(mode=SleepTimerMode.OFF)

    def pause(self) -> None:
        """Pause the timer (when playback pauses)."""
        if (
            self._state.mode not in (SleepTimerMode.OFF, SleepTimerMode.END_OF_EPISODE)
            and self._state.end_time is not None
        ):
            remaining = self._state.end_time - datetime.now()
            self._state.paused_remaining = max(remaining, timedelta(seconds=0))
            self._cancel_timer()

    def resume(self) -> None:
        """Resume the timer (when playback resumes)."""
        if (
            self._state.mode not in (SleepTimerMode.OFF, SleepTimerMode.END_OF_EPISODE)
            and self._state.paused_remaining is not None
        ):
            seconds = int(self._state.paused_remaining.total_seconds())
            self._state.end_time = datetime.now() + timedelta(seconds=seconds)
            self._state.paused_remaining = None
            if seconds > 0:
                self._start_timer(seconds)

    def check_end_of_episode(self) -> bool:
        """Check if end-of-episode timer should trigger.

        Call this when an episode finishes.

        Returns:
            True if timer triggered and playback should stop.
        """
        if self._state.mode == SleepTimerMode.END_OF_EPISODE:
            self._state = SleepTimerState(mode=SleepTimerMode.OFF)
            if self._on_expire:
                self._on_expire()
            return True
        return False

    def _start_timer(self, seconds: int) -> None:
        """Start the background timer task.

        Args:
            seconds: Duration in seconds.
        """
        self._cancel_timer()

        async def timer_task() -> None:
            await asyncio.sleep(seconds)
            self._state = SleepTimerState(mode=SleepTimerMode.OFF)
            if self._on_expire:
                self._on_expire()

        # No running event loop (e.g., in tests) - timer won't auto-expire but state is still set
        with contextlib.suppress(RuntimeError):
            self._timer_task = asyncio.create_task(timer_task())

    def _cancel_timer(self) -> None:
        """Cancel the background timer task."""
        if self._timer_task is not None:
            self._timer_task.cancel()
            self._timer_task = None
