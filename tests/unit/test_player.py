"""Tests for feedback player module."""

import pytest

from feedback.player import NullPlayer, Player, PlayerState


class TestPlayerState:
    """Tests for PlayerState enum."""

    def test_states_exist(self):
        """Test that all states exist."""
        assert PlayerState.STOPPED == 0
        assert PlayerState.PLAYING == 1
        assert PlayerState.PAUSED == 2


class TestPlayerProtocol:
    """Tests for the Player protocol."""

    def test_null_player_satisfies_protocol(self):
        """Test that NullPlayer satisfies the Player protocol."""
        player = NullPlayer()
        assert isinstance(player, Player)


class TestBasePlayer:
    """Tests for BasePlayer abstract class."""

    def test_initial_state(self):
        """Test initial player state."""
        player = NullPlayer()
        assert player.state == PlayerState.STOPPED
        assert player.position_ms == 0
        assert player.duration_ms == 0
        assert player.volume == 100
        assert player.rate == 1.0

    def test_time_remaining(self):
        """Test time_remaining_ms property."""
        player = NullPlayer()
        player._duration_ms = 60000
        player._position_ms = 30000
        assert player.time_remaining_ms == 30000

    def test_time_remaining_negative_clamped(self):
        """Test time_remaining_ms is clamped to 0."""
        player = NullPlayer()
        player._duration_ms = 30000
        player._position_ms = 40000
        assert player.time_remaining_ms == 0

    def test_progress_fraction(self):
        """Test progress_fraction property."""
        player = NullPlayer()
        player._duration_ms = 100000
        player._position_ms = 25000
        assert player.progress_fraction == 0.25

    def test_progress_fraction_zero_duration(self):
        """Test progress_fraction with zero duration."""
        player = NullPlayer()
        assert player.progress_fraction == 0.0

    def test_format_time(self):
        """Test format_time method."""
        player = NullPlayer()
        assert player.format_time(0) == "00:00:00"
        assert player.format_time(1000) == "00:00:01"
        assert player.format_time(61000) == "00:01:01"
        assert player.format_time(3661000) == "01:01:01"

    def test_format_time_negative(self):
        """Test format_time with negative value."""
        player = NullPlayer()
        assert player.format_time(-1000) == "00:00:00"

    def test_time_str(self):
        """Test time_str property."""
        player = NullPlayer()
        player._position_ms = 30000
        player._duration_ms = 120000
        assert player.time_str == "00:00:30/00:02:00"

    def test_clamp_volume(self):
        """Test _clamp_volume method."""
        player = NullPlayer()
        assert player._clamp_volume(-10) == 0
        assert player._clamp_volume(50) == 50
        assert player._clamp_volume(150) == 100

    def test_clamp_rate(self):
        """Test _clamp_rate method."""
        player = NullPlayer()
        assert player._clamp_rate(0.3) == 0.5
        assert player._clamp_rate(1.0) == 1.0
        assert player._clamp_rate(3.0) == 2.0


class TestNullPlayer:
    """Tests for NullPlayer implementation."""

    @pytest.mark.asyncio
    async def test_play(self):
        """Test play method."""
        player = NullPlayer()
        await player.play("https://example.com/audio.mp3")
        assert player.state == PlayerState.PLAYING
        assert player.duration_ms == 60000

    @pytest.mark.asyncio
    async def test_play_with_start_position(self):
        """Test play with start position."""
        player = NullPlayer()
        await player.play("https://example.com/audio.mp3", start_ms=30000)
        assert player.state == PlayerState.PLAYING
        assert player.position_ms == 30000

    @pytest.mark.asyncio
    async def test_pause(self):
        """Test pause method."""
        player = NullPlayer()
        await player.play("https://example.com/audio.mp3")
        await player.pause()
        assert player.state == PlayerState.PAUSED

    @pytest.mark.asyncio
    async def test_pause_when_stopped(self):
        """Test pause when already stopped does nothing."""
        player = NullPlayer()
        await player.pause()
        assert player.state == PlayerState.STOPPED

    @pytest.mark.asyncio
    async def test_resume(self):
        """Test resume method."""
        player = NullPlayer()
        await player.play("https://example.com/audio.mp3")
        await player.pause()
        await player.resume()
        assert player.state == PlayerState.PLAYING

    @pytest.mark.asyncio
    async def test_resume_when_not_paused(self):
        """Test resume when not paused does nothing."""
        player = NullPlayer()
        await player.resume()
        assert player.state == PlayerState.STOPPED

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test stop method."""
        player = NullPlayer()
        await player.play("https://example.com/audio.mp3")
        player._position_ms = 30000
        await player.stop()
        assert player.state == PlayerState.STOPPED
        assert player.position_ms == 0

    @pytest.mark.asyncio
    async def test_seek(self):
        """Test seek method."""
        player = NullPlayer()
        await player.play("https://example.com/audio.mp3")
        await player.seek(30000)
        assert player.position_ms == 30000

    @pytest.mark.asyncio
    async def test_seek_clamps_to_duration(self):
        """Test seek clamps to duration."""
        player = NullPlayer()
        await player.play("https://example.com/audio.mp3")
        await player.seek(120000)  # > 60000 default duration
        assert player.position_ms == 60000

    @pytest.mark.asyncio
    async def test_seek_clamps_negative(self):
        """Test seek clamps negative values."""
        player = NullPlayer()
        await player.play("https://example.com/audio.mp3")
        await player.seek(-10000)
        assert player.position_ms == 0

    @pytest.mark.asyncio
    async def test_set_volume(self):
        """Test set_volume method."""
        player = NullPlayer()
        await player.set_volume(50)
        assert player.volume == 50

    @pytest.mark.asyncio
    async def test_set_volume_clamps(self):
        """Test set_volume clamps to valid range."""
        player = NullPlayer()
        await player.set_volume(150)
        assert player.volume == 100
        await player.set_volume(-10)
        assert player.volume == 0

    @pytest.mark.asyncio
    async def test_set_rate(self):
        """Test set_rate method."""
        player = NullPlayer()
        await player.set_rate(1.5)
        assert player.rate == 1.5

    @pytest.mark.asyncio
    async def test_set_rate_clamps(self):
        """Test set_rate clamps to valid range."""
        player = NullPlayer()
        await player.set_rate(3.0)
        assert player.rate == 2.0
        await player.set_rate(0.1)
        assert player.rate == 0.5
