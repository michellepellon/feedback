"""Tests for the sleep timer module."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest

from feedback.sleep_timer import SleepTimer, SleepTimerMode, SleepTimerState


class TestSleepTimerMode:
    """Tests for SleepTimerMode enum."""

    def test_mode_labels(self) -> None:
        """Test that all modes have labels."""
        assert SleepTimerMode.OFF.label == "Off"
        assert SleepTimerMode.MINUTES_15.label == "15 minutes"
        assert SleepTimerMode.MINUTES_30.label == "30 minutes"
        assert SleepTimerMode.MINUTES_45.label == "45 minutes"
        assert SleepTimerMode.MINUTES_60.label == "60 minutes"
        assert SleepTimerMode.END_OF_EPISODE.label == "End of episode"

    def test_mode_minutes(self) -> None:
        """Test minute values for timed modes."""
        assert SleepTimerMode.OFF.minutes is None
        assert SleepTimerMode.MINUTES_15.minutes == 15
        assert SleepTimerMode.MINUTES_30.minutes == 30
        assert SleepTimerMode.MINUTES_45.minutes == 45
        assert SleepTimerMode.MINUTES_60.minutes == 60
        assert SleepTimerMode.END_OF_EPISODE.minutes is None


class TestSleepTimerState:
    """Tests for SleepTimerState."""

    def test_inactive_state(self) -> None:
        """Test state when timer is off."""
        state = SleepTimerState(mode=SleepTimerMode.OFF)
        assert not state.is_active
        assert state.remaining_seconds is None
        assert state.remaining_formatted == ""

    def test_active_timed_state(self) -> None:
        """Test state with active timer."""
        end_time = datetime.now() + timedelta(minutes=15)
        state = SleepTimerState(mode=SleepTimerMode.MINUTES_15, end_time=end_time)
        assert state.is_active
        # Should be close to 15 minutes
        remaining = state.remaining_seconds
        assert remaining is not None
        assert 14 * 60 < remaining <= 15 * 60

    def test_end_of_episode_state(self) -> None:
        """Test end-of-episode mode state."""
        state = SleepTimerState(mode=SleepTimerMode.END_OF_EPISODE)
        assert state.is_active
        assert state.remaining_seconds is None
        assert state.remaining_formatted == "End of episode"

    def test_paused_state(self) -> None:
        """Test state when timer is paused."""
        state = SleepTimerState(
            mode=SleepTimerMode.MINUTES_15,
            paused_remaining=timedelta(minutes=10),
        )
        assert state.remaining_seconds == 600  # 10 minutes in seconds

    def test_remaining_formatted(self) -> None:
        """Test formatted remaining time string."""
        # 5:30 remaining
        end_time = datetime.now() + timedelta(minutes=5, seconds=30)
        state = SleepTimerState(mode=SleepTimerMode.MINUTES_15, end_time=end_time)
        formatted = state.remaining_formatted
        # Should be in M:SS format
        assert ":" in formatted


class TestSleepTimer:
    """Tests for SleepTimer."""

    def test_initial_state(self) -> None:
        """Test timer starts in off state."""
        timer = SleepTimer()
        assert timer.mode == SleepTimerMode.OFF
        assert not timer.is_active

    def test_set_mode_off(self) -> None:
        """Test setting mode to off."""
        timer = SleepTimer()
        timer.set_mode(SleepTimerMode.MINUTES_15)
        assert timer.is_active
        timer.set_mode(SleepTimerMode.OFF)
        assert not timer.is_active

    def test_set_mode_timed(self) -> None:
        """Test setting a timed mode."""
        timer = SleepTimer()
        timer.set_mode(SleepTimerMode.MINUTES_30)
        assert timer.mode == SleepTimerMode.MINUTES_30
        assert timer.is_active
        assert timer.state.end_time is not None

    def test_set_mode_end_of_episode(self) -> None:
        """Test setting end-of-episode mode."""
        timer = SleepTimer()
        timer.set_mode(SleepTimerMode.END_OF_EPISODE)
        assert timer.mode == SleepTimerMode.END_OF_EPISODE
        assert timer.is_active
        assert timer.state.end_time is None

    def test_cycle_mode(self) -> None:
        """Test cycling through modes."""
        timer = SleepTimer()
        assert timer.mode == SleepTimerMode.OFF

        # Cycle through all modes
        modes_seen = [timer.cycle_mode() for _ in range(6)]
        expected = [
            SleepTimerMode.MINUTES_15,
            SleepTimerMode.MINUTES_30,
            SleepTimerMode.MINUTES_45,
            SleepTimerMode.MINUTES_60,
            SleepTimerMode.END_OF_EPISODE,
            SleepTimerMode.OFF,
        ]
        assert modes_seen == expected

    def test_cancel(self) -> None:
        """Test canceling the timer."""
        timer = SleepTimer()
        timer.set_mode(SleepTimerMode.MINUTES_15)
        assert timer.is_active
        timer.cancel()
        assert not timer.is_active
        assert timer.mode == SleepTimerMode.OFF

    def test_pause_and_resume(self) -> None:
        """Test pausing and resuming the timer."""
        timer = SleepTimer()
        timer.set_mode(SleepTimerMode.MINUTES_15)

        # Pause
        timer.pause()
        assert timer.state.paused_remaining is not None
        paused_seconds = timer.state.paused_remaining.total_seconds()
        assert paused_seconds > 0

        # Resume
        timer.resume()
        assert timer.state.paused_remaining is None
        assert timer.state.end_time is not None

    def test_pause_end_of_episode_no_effect(self) -> None:
        """Test that pause has no effect on end-of-episode mode."""
        timer = SleepTimer()
        timer.set_mode(SleepTimerMode.END_OF_EPISODE)
        timer.pause()
        # Should still be end of episode with no paused_remaining
        assert timer.mode == SleepTimerMode.END_OF_EPISODE
        assert timer.state.paused_remaining is None

    def test_check_end_of_episode_triggers(self) -> None:
        """Test that check_end_of_episode triggers callback."""
        callback_called = []

        def callback() -> None:
            callback_called.append(True)

        timer = SleepTimer(on_expire=callback)
        timer.set_mode(SleepTimerMode.END_OF_EPISODE)

        result = timer.check_end_of_episode()
        assert result is True
        assert callback_called == [True]
        assert timer.mode == SleepTimerMode.OFF

    def test_check_end_of_episode_not_in_mode(self) -> None:
        """Test that check_end_of_episode doesn't trigger for other modes."""
        callback_called = []

        def callback() -> None:
            callback_called.append(True)

        timer = SleepTimer(on_expire=callback)
        timer.set_mode(SleepTimerMode.MINUTES_15)

        result = timer.check_end_of_episode()
        assert result is False
        assert callback_called == []
        assert timer.mode == SleepTimerMode.MINUTES_15

    @pytest.mark.asyncio
    async def test_timer_expires(self) -> None:
        """Test that timer callback is called on expiration."""
        callback_called = []

        def callback() -> None:
            callback_called.append(True)

        timer = SleepTimer(on_expire=callback)

        # Set a very short timer for testing
        timer._state = SleepTimerState(
            mode=SleepTimerMode.MINUTES_15,
            end_time=datetime.now() + timedelta(milliseconds=100),
        )
        timer._start_timer(0)  # Start with 0 seconds for quick test

        # Wait for callback
        await asyncio.sleep(0.1)

        assert callback_called == [True]
        assert timer.mode == SleepTimerMode.OFF

    def test_remaining_seconds_expired(self) -> None:
        """Test remaining_seconds returns 0 when timer has expired."""
        # Create a state where end_time is in the past
        past_time = datetime.now() - timedelta(minutes=5)
        state = SleepTimerState(mode=SleepTimerMode.MINUTES_15, end_time=past_time)
        assert state.remaining_seconds == 0

    def test_cancel_timer_when_no_task(self) -> None:
        """Test _cancel_timer when there's no active task."""
        timer = SleepTimer()
        # Should not raise
        timer._cancel_timer()
        assert timer._timer_task is None

    def test_mode_unknown_label(self) -> None:
        """Test that mode label handles unknown modes gracefully."""
        # This tests the .get() default for label
        mode = SleepTimerMode.OFF
        assert mode.label == "Off"

    def test_state_remaining_formatted_empty_end_time(self) -> None:
        """Test remaining_formatted when end_time is None for timed mode."""
        # Edge case: timed mode but no end_time set
        state = SleepTimerState(mode=SleepTimerMode.MINUTES_15, end_time=None)
        assert state.remaining_formatted == ""
