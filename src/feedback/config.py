"""Configuration system for feedback."""

import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class PlayerConfig(BaseModel):
    """Player configuration."""

    backend: str = Field(default="vlc", description="Player backend (vlc or mpv)")
    default_volume: int = Field(default=100, ge=0, le=100, description="Default volume")
    default_speed: float = Field(
        default=1.0, ge=0.5, le=2.0, description="Default playback speed"
    )
    seek_forward: int = Field(default=30, ge=1, description="Seek forward seconds")
    seek_backward: int = Field(default=10, ge=1, description="Seek backward seconds")
    resume_rewind: int = Field(
        default=5, ge=0, description="Seconds to rewind when resuming"
    )


class UIConfig(BaseModel):
    """UI configuration."""

    theme: str = Field(default="dark", description="UI theme")
    default_layout: int = Field(
        default=1, ge=1, le=5, description="Default screen layout"
    )
    show_descriptions: bool = Field(
        default=True, description="Show episode descriptions"
    )
    disable_vertical_borders: bool = Field(
        default=False, description="Hide vertical borders"
    )
    refresh_delay: int = Field(default=100, ge=50, description="Refresh delay in ms")


class KeyConfig(BaseModel):
    """Keyboard configuration.

    Each key binding can be either a single key string or a list of key strings.
    Key strings support modifiers: ctrl+, alt+, shift+ (e.g., "ctrl+right", "shift+tab").
    """

    quit: str | list[str] = Field(default="q", description="Quit application")
    help: str | list[str] = Field(default="h", description="Show help")
    add_feed: str | list[str] = Field(default="a", description="Add a feed")
    remove_feed: str | list[str] = Field(
        default="d", description="Remove selected feed"
    )
    reload_feeds: str | list[str] = Field(default="r", description="Reload all feeds")
    reload_selected: str | list[str] = Field(
        default="R", description="Reload selected feed"
    )
    play_selected: str | list[str] = Field(default="enter", description="Play selected")
    add_to_queue: str | list[str] = Field(default="space", description="Add to queue")
    clear_queue: str | list[str] = Field(default="c", description="Clear queue")
    next_episode: str | list[str] = Field(default="n", description="Next episode")
    play_pause: str | list[str] = Field(
        default=["p", "space"], description="Play/pause"
    )
    seek_forward: str | list[str] = Field(
        default=["f", "l", "ctrl+right"], description="Seek forward"
    )
    seek_backward: str | list[str] = Field(
        default=["b", "j", "ctrl+left"], description="Seek backward"
    )
    volume_up: str | list[str] = Field(default="=", description="Increase volume")
    volume_down: str | list[str] = Field(default="-", description="Decrease volume")
    speed_up: str | list[str] = Field(default="]", description="Increase speed")
    speed_down: str | list[str] = Field(default="[", description="Decrease speed")
    save_episode: str | list[str] = Field(default="s", description="Save episode")
    delete_episode: str | list[str] = Field(default="x", description="Delete episode")
    mark_played: str | list[str] = Field(default="m", description="Mark as played")
    invert_menu: str | list[str] = Field(default="i", description="Invert menu order")
    filter_menu: str | list[str] = Field(default="/", description="Filter menu")
    show_url: str | list[str] = Field(default="u", description="Show episode URL")
    search_podcasts: str | list[str] = Field(
        default="S", description="Search for podcasts"
    )

    def get_keys(self, action: str) -> list[str]:
        """Get all key bindings for an action.

        Args:
            action: The action name (e.g., 'play_pause').

        Returns:
            List of key strings for the action.
        """
        value = getattr(self, action, None)
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]


class NetworkConfig(BaseModel):
    """Network configuration."""

    timeout: float = Field(
        default=30.0, ge=1.0, description="Request timeout in seconds"
    )
    max_episodes: int = Field(
        default=-1, description="Max episodes per feed (-1 for unlimited)"
    )
    reload_on_start: bool = Field(default=False, description="Reload feeds on startup")
    proxy_http: str = Field(default="", description="HTTP proxy URL")
    proxy_https: str = Field(default="", description="HTTPS proxy URL")


class DownloadConfig(BaseModel):
    """Download configuration."""

    directory: str = Field(default="", description="Custom download directory")
    concurrent: int = Field(
        default=3, ge=1, le=10, description="Max concurrent downloads"
    )


class ColorConfig(BaseModel):
    """Color configuration."""

    foreground: str = Field(default="white", description="Foreground color")
    background: str = Field(default="transparent", description="Background color")
    foreground_alt: str = Field(
        default="white", description="Alt foreground (selection)"
    )
    background_alt: str = Field(
        default="black", description="Alt background (selection)"
    )
    foreground_dim: str = Field(
        default="white", description="Dimmed foreground (played)"
    )
    foreground_status: str = Field(default="yellow", description="Status text color")
    foreground_heading: str = Field(default="yellow", description="Heading color")
    foreground_dividers: str = Field(default="yellow", description="Divider color")


class DiscoveryConfig(BaseModel):
    """Podcast discovery configuration.

    To use podcast discovery, register at https://api.podcastindex.org
    to obtain an API key and secret.
    """

    api_key: str = Field(default="", description="Podcast Index API key")
    api_secret: str = Field(default="", description="Podcast Index API secret")


class Config(BaseModel):
    """Complete application configuration."""

    player: PlayerConfig = Field(default_factory=PlayerConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    keys: KeyConfig = Field(default_factory=KeyConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    download: DownloadConfig = Field(default_factory=DownloadConfig)
    colors: ColorConfig = Field(default_factory=ColorConfig)
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)


def get_config_path() -> Path:
    """Get the configuration file path."""
    return Path.home() / ".config" / "feedback" / "config.toml"


def get_data_path() -> Path:
    """Get the data directory path."""
    xdg_data = Path.home() / ".local" / "share"
    return xdg_data / "feedback"


def get_default_config_toml() -> str:
    """Generate the default configuration as TOML."""
    return """# Feedback Configuration
# This file is auto-generated with default values.
# Uncomment and modify settings as needed.

[player]
backend = "vlc"  # or "mpv"
default_volume = 100
default_speed = 1.0
seek_forward = 30
seek_backward = 10
resume_rewind = 5

[ui]
theme = "dark"
default_layout = 1
show_descriptions = true
disable_vertical_borders = false
refresh_delay = 100

[keys]
# Keys can be single values or lists: key = "q" or key = ["p", "space"]
# Modifiers supported: ctrl+, alt+, shift+ (e.g., "ctrl+right", "shift+tab")
quit = "q"
help = "h"
add_feed = "a"
remove_feed = "d"
reload_feeds = "r"
reload_selected = "R"
play_selected = "enter"
add_to_queue = "space"
clear_queue = "c"
next_episode = "n"
play_pause = ["p", "space"]
seek_forward = ["f", "l", "ctrl+right"]
seek_backward = ["b", "j", "ctrl+left"]
volume_up = "="
volume_down = "-"
speed_up = "]"
speed_down = "["
save_episode = "s"
delete_episode = "x"
mark_played = "m"
invert_menu = "i"
filter_menu = "/"
show_url = "u"
search_podcasts = "S"

[network]
timeout = 30.0
max_episodes = -1
reload_on_start = false
proxy_http = ""
proxy_https = ""

[download]
directory = ""
concurrent = 3

[colors]
foreground = "white"
background = "transparent"
foreground_alt = "white"
background_alt = "black"
foreground_dim = "white"
foreground_status = "yellow"
foreground_heading = "yellow"
foreground_dividers = "yellow"

[discovery]
# Podcast Index API credentials for podcast search.
# Register at https://api.podcastindex.org to get an API key.
api_key = ""
api_secret = ""
"""


def load_config(path: Path | None = None) -> Config:
    """Load configuration from file.

    Args:
        path: Path to config file. If None, uses default location.

    Returns:
        Loaded configuration, with defaults for missing values.
    """
    if path is None:
        path = get_config_path()

    if not path.exists():
        # Create default config file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(get_default_config_toml())
        return Config()

    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
        return _parse_config(data)
    except (tomllib.TOMLDecodeError, ValueError):
        # Return defaults on parse error
        return Config()


def _parse_config(data: dict[str, Any]) -> Config:
    """Parse configuration from dictionary.

    Args:
        data: Dictionary of configuration data from TOML.

    Returns:
        Parsed Config object with all sections populated.
    """
    return Config(
        player=PlayerConfig(**data.get("player", {})),
        ui=UIConfig(**data.get("ui", {})),
        keys=KeyConfig(**data.get("keys", {})),
        network=NetworkConfig(**data.get("network", {})),
        download=DownloadConfig(**data.get("download", {})),
        colors=ColorConfig(**data.get("colors", {})),
        discovery=DiscoveryConfig(**data.get("discovery", {})),
    )


# Global configuration instance (lazy loaded)
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(path: Path | None = None) -> Config:
    """Reload the global configuration."""
    global _config
    _config = load_config(path)
    return _config
