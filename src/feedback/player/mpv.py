"""MPV player backend for feedback."""

from __future__ import annotations

import asyncio

import mpv

from feedback.player.base import BasePlayer, PlayerState


class MPVPlayer(BasePlayer):
    """Player implementation using python-mpv.

    This player uses mpv's powerful media playback capabilities.
    Requires mpv to be installed on the system.
    """

    def __init__(self) -> None:
        """Initialize the MPV player."""
        super().__init__()
        self._player = mpv.MPV(
            video=False,
            terminal=False,
            input_default_bindings=False,
            input_vo_keyboard=False,
        )
        self._poll_task: asyncio.Task[None] | None = None
        self._poll_interval = 0.5  # seconds

        # Register event handlers
        @self._player.event_callback("end-file")  # type: ignore[untyped-decorator]
        def on_end_file(_event: mpv.MpvEvent) -> None:
            self._state = PlayerState.STOPPED
            if self._duration_ms > 0:
                self._position_ms = self._duration_ms

    async def play(self, path: str, start_ms: int = 0) -> None:
        """Start playback from the given path.

        Args:
            path: URL or file path to play.
            start_ms: Starting position in milliseconds.
        """
        # Stop any existing playback
        await self.stop()

        # Start playback
        self._player.play(path)
        self._state = PlayerState.PLAYING

        # Wait for mpv to start
        await asyncio.sleep(0.1)

        # Seek to start position if specified
        if start_ms > 0:
            self._player.seek(start_ms / 1000.0, reference="absolute")
            self._position_ms = start_ms

        # Apply current volume and rate
        self._player.volume = self._volume
        self._player.speed = self._rate

        # Start polling for position updates
        self._start_polling()

    async def pause(self) -> None:
        """Pause playback."""
        if self._state == PlayerState.PLAYING:
            self._player.pause = True
            self._state = PlayerState.PAUSED

    async def resume(self) -> None:
        """Resume playback."""
        if self._state == PlayerState.PAUSED:
            self._player.pause = False
            self._state = PlayerState.PLAYING

    async def stop(self) -> None:
        """Stop playback."""
        self._stop_polling()
        self._player.stop()
        self._state = PlayerState.STOPPED
        self._position_ms = 0
        self._duration_ms = 0

    async def seek(self, position_ms: int) -> None:
        """Seek to the given position.

        Args:
            position_ms: Target position in milliseconds.
        """
        if self._state != PlayerState.STOPPED:
            clamped = max(0, min(position_ms, self._duration_ms))
            self._player.seek(clamped / 1000.0, reference="absolute")
            self._position_ms = clamped

    async def set_volume(self, volume: int) -> None:
        """Set the playback volume.

        Args:
            volume: Volume level (0-100).
        """
        self._volume = self._clamp_volume(volume)
        self._player.volume = self._volume

    async def set_rate(self, rate: float) -> None:
        """Set the playback rate.

        Args:
            rate: Playback rate (0.5-2.0).
        """
        self._rate = self._clamp_rate(rate)
        self._player.speed = self._rate

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
        """Poll mpv for position and duration updates."""
        try:
            while True:
                if self._state == PlayerState.PLAYING:
                    # Update position
                    try:
                        pos = self._player.time_pos
                        if pos is not None:
                            self._position_ms = int(pos * 1000)
                    except mpv.ShutdownError:
                        break

                    # Update duration
                    try:
                        dur = self._player.duration
                        if dur is not None:
                            self._duration_ms = int(dur * 1000)
                    except mpv.ShutdownError:
                        break

                await asyncio.sleep(self._poll_interval)
        except asyncio.CancelledError:
            pass

    def __del__(self) -> None:
        """Clean up mpv resources."""
        self._stop_polling()
        if self._player:
            self._player.terminate()
