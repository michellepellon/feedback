"""Settings screen for configuring the application."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult


class SettingsScreen(ModalScreen[bool]):
    """Modal screen for application settings.

    Returns True if settings were saved, False if cancelled.
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    SettingsScreen {
        align: center middle;
    }

    SettingsScreen > Vertical {
        width: 70;
        max-width: 90%;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    SettingsScreen .settings-title {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
        border-bottom: solid $primary;
        margin-bottom: 1;
    }

    SettingsScreen .section-title {
        text-style: bold underline;
        margin-top: 1;
        margin-bottom: 1;
        color: $text;
    }

    SettingsScreen .setting-row {
        height: auto;
        margin-bottom: 1;
    }

    SettingsScreen .setting-label {
        width: 20;
        padding-right: 1;
    }

    SettingsScreen .setting-input {
        width: 1fr;
    }

    SettingsScreen Input {
        width: 100%;
    }

    SettingsScreen Select {
        width: 100%;
    }

    SettingsScreen .button-row {
        height: auto;
        margin-top: 1;
        padding-top: 1;
        border-top: solid $primary;
        align: center middle;
    }

    SettingsScreen Button {
        margin: 0 1;
    }
    """

    def __init__(self) -> None:
        """Initialize the settings screen."""
        super().__init__()
        self._original_values: dict[str, str | int | float | bool] = {}

    def compose(self) -> ComposeResult:
        """Compose the settings screen."""
        from feedback.config import get_config

        config = get_config()

        with Vertical():
            yield Static("Settings", classes="settings-title")

            with VerticalScroll():
                # Player Settings
                yield Static("Player", classes="section-title")

                with Horizontal(classes="setting-row"):
                    yield Label("Backend:", classes="setting-label")
                    yield Select(
                        [("VLC", "vlc"), ("MPV", "mpv")],
                        value=config.player.backend.lower(),
                        id="player-backend",
                        classes="setting-input",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("Default Volume:", classes="setting-label")
                    yield Input(
                        str(config.player.default_volume),
                        id="player-volume",
                        classes="setting-input",
                        type="integer",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("Default Speed:", classes="setting-label")
                    yield Input(
                        str(config.player.default_speed),
                        id="player-speed",
                        classes="setting-input",
                        type="number",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("Seek Forward (s):", classes="setting-label")
                    yield Input(
                        str(config.player.seek_forward),
                        id="player-seek-forward",
                        classes="setting-input",
                        type="integer",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("Seek Backward (s):", classes="setting-label")
                    yield Input(
                        str(config.player.seek_backward),
                        id="player-seek-backward",
                        classes="setting-input",
                        type="integer",
                    )

                # Network Settings
                yield Static("Network", classes="section-title")

                with Horizontal(classes="setting-row"):
                    yield Label("Timeout (s):", classes="setting-label")
                    yield Input(
                        str(config.network.timeout),
                        id="network-timeout",
                        classes="setting-input",
                        type="number",
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("Max Episodes:", classes="setting-label")
                    yield Input(
                        str(config.network.max_episodes),
                        id="network-max-episodes",
                        classes="setting-input",
                        type="integer",
                    )

                # Download Settings
                yield Static("Downloads", classes="section-title")

                with Horizontal(classes="setting-row"):
                    yield Label("Concurrent:", classes="setting-label")
                    yield Input(
                        str(config.download.concurrent),
                        id="download-concurrent",
                        classes="setting-input",
                        type="integer",
                    )

                # Discovery Settings
                yield Static("Podcast Index API", classes="section-title")

                with Horizontal(classes="setting-row"):
                    yield Label("API Key:", classes="setting-label")
                    yield Input(
                        config.discovery.api_key or "",
                        id="discovery-api-key",
                        classes="setting-input",
                        password=True,
                    )

                with Horizontal(classes="setting-row"):
                    yield Label("API Secret:", classes="setting-label")
                    yield Input(
                        config.discovery.api_secret or "",
                        id="discovery-api-secret",
                        classes="setting-input",
                        password=True,
                    )

            # Buttons
            with Horizontal(classes="button-row"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            await self._save_settings()
            self.dismiss(True)
        elif event.button.id == "cancel-btn":
            self.dismiss(False)

    def action_cancel(self) -> None:
        """Cancel and close the settings screen."""
        self.dismiss(False)

    async def _save_settings(self) -> None:
        """Save settings to config file."""
        from feedback.config import get_config_path

        # Collect values from inputs
        try:
            backend = self.query_one("#player-backend", Select).value
            volume = int(self.query_one("#player-volume", Input).value)
            speed = float(self.query_one("#player-speed", Input).value)
            seek_forward = int(self.query_one("#player-seek-forward", Input).value)
            seek_backward = int(self.query_one("#player-seek-backward", Input).value)
            timeout = float(self.query_one("#network-timeout", Input).value)
            max_episodes = int(self.query_one("#network-max-episodes", Input).value)
            concurrent = int(self.query_one("#download-concurrent", Input).value)
            api_key = self.query_one("#discovery-api-key", Input).value
            api_secret = self.query_one("#discovery-api-secret", Input).value

            # Validate ranges
            volume = max(0, min(100, volume))
            speed = max(0.5, min(2.0, speed))
            seek_forward = max(1, seek_forward)
            seek_backward = max(1, seek_backward)
            timeout = max(1.0, timeout)
            concurrent = max(1, min(10, concurrent))

        except ValueError as e:
            self.app.notify(f"Invalid value: {e}", severity="error")
            return

        # Generate TOML content
        config_path = get_config_path()
        toml_content = self._generate_toml(
            backend=str(backend),
            volume=volume,
            speed=speed,
            seek_forward=seek_forward,
            seek_backward=seek_backward,
            timeout=timeout,
            max_episodes=max_episodes,
            concurrent=concurrent,
            api_key=api_key,
            api_secret=api_secret,
        )

        # Write config file
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(toml_content)
            self.app.notify("Settings saved. Restart for some changes to take effect.", severity="information")
        except OSError as e:
            self.app.notify(f"Failed to save settings: {e}", severity="error")

    def _generate_toml(
        self,
        *,
        backend: str,
        volume: int,
        speed: float,
        seek_forward: int,
        seek_backward: int,
        timeout: float,
        max_episodes: int,
        concurrent: int,
        api_key: str,
        api_secret: str,
    ) -> str:
        """Generate TOML config content.

        Returns:
            TOML formatted string.
        """
        lines = [
            "# Feedback Configuration",
            "# Generated by settings screen",
            "",
            "[player]",
            f'backend = "{backend}"',
            f"default_volume = {volume}",
            f"default_speed = {speed}",
            f"seek_forward = {seek_forward}",
            f"seek_backward = {seek_backward}",
            "",
            "[network]",
            f"timeout = {timeout}",
            f"max_episodes = {max_episodes}",
            "",
            "[download]",
            f"concurrent = {concurrent}",
            "",
        ]

        # Only include discovery section if credentials are provided
        if api_key or api_secret:
            lines.extend([
                "[discovery]",
                f'api_key = "{api_key}"',
                f'api_secret = "{api_secret}"',
                "",
            ])

        return "\n".join(lines)
