"""VLC player backend for feedback."""

from __future__ import annotations

import asyncio

import vlc

from feedback.player.base import BasePlayer, PlayerState


class VLCPlayer(BasePlayer):
    """Player implementation using python-vlc (libVLC).

    This player uses VLC's media player capabilities for audio playback.
    Requires VLC to be installed on the system.
    """

    def __init__(self) -> None:
        """Initialize the VLC player."""
        super().__init__()
        self._instance = vlc.Instance("--no-video", "--quiet")
        self._player: vlc.MediaPlayer = self._instance.media_player_new()
        self._media: vlc.Media | None = None
        self._poll_task: asyncio.Task[None] | None = None
        self._poll_interval = 0.5  # seconds

    async def play(self, path: str, start_ms: int = 0) -> None:
        """Start playback from the given path.

        Args:
            path: URL or file path to play.
            start_ms: Starting position in milliseconds.
        """
        # Stop any existing playback
        await self.stop()

        # Create new media
        self._media = self._instance.media_new(path)
        self._player.set_media(self._media)

        # Start playback
        self._player.play()
        self._state = PlayerState.PLAYING

        # Wait for VLC to start playing before seeking
        await asyncio.sleep(0.1)

        # Seek to start position if specified
        if start_ms > 0:
            self._player.set_time(start_ms)
            self._position_ms = start_ms

        # Start polling for position updates
        self._start_polling()

    async def pause(self) -> None:
        """Pause playback."""
        if self._state == PlayerState.PLAYING:
            self._player.pause()
            self._state = PlayerState.PAUSED

    async def resume(self) -> None:
        """Resume playback."""
        if self._state == PlayerState.PAUSED:
            self._player.play()
            self._state = PlayerState.PLAYING

    async def stop(self) -> None:
        """Stop playback."""
        self._stop_polling()
        self._player.stop()
        self._state = PlayerState.STOPPED
        self._position_ms = 0
        self._duration_ms = 0
        self._media = None

    async def seek(self, position_ms: int) -> None:
        """Seek to the given position.

        Args:
            position_ms: Target position in milliseconds.
        """
        if self._state != PlayerState.STOPPED:
            clamped = max(0, min(position_ms, self._duration_ms))
            self._player.set_time(clamped)
            self._position_ms = clamped

    async def set_volume(self, volume: int) -> None:
        """Set the playback volume.

        Args:
            volume: Volume level (0-100).
        """
        self._volume = self._clamp_volume(volume)
        self._player.audio_set_volume(self._volume)

    async def set_rate(self, rate: float) -> None:
        """Set the playback rate.

        Args:
            rate: Playback rate (0.5-2.0).
        """
        self._rate = self._clamp_rate(rate)
        self._player.set_rate(self._rate)

    def _start_polling(self) -> None:
        """Start the position polling task."""
        if self._poll_task is None or self._poll_task.done():
            self._poll_task = asyncio.create_task(self._poll_position())

    def _stop_polling(self) -> None:
        """Stop the position polling task."""
        if self._poll_task is not None and not self._poll_task.done():
            self._poll_task.cancel()
            self._poll_task = None

    async def _poll_position(self) -> None:
        """Poll VLC for position and duration updates."""
        try:
            while True:
                if self._state == PlayerState.PLAYING:
                    # Update position
                    pos = self._player.get_time()
                    if pos >= 0:
                        self._position_ms = pos

                    # Update duration
                    dur = self._player.get_length()
                    if dur > 0:
                        self._duration_ms = dur

                    # Check if playback ended
                    state = self._player.get_state()
                    if state == vlc.State.Ended:
                        self._state = PlayerState.STOPPED
                        self._position_ms = self._duration_ms
                        break

                await asyncio.sleep(self._poll_interval)
        except asyncio.CancelledError:
            pass

    def __del__(self) -> None:
        """Clean up VLC resources."""
        self._stop_polling()
        if self._player:
            self._player.stop()
            self._player.release()
        if self._instance:
            self._instance.release()
