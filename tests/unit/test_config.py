"""Tests for feedback configuration."""

from pathlib import Path

import pytest

import feedback.config
from feedback.config import (
    ColorConfig,
    Config,
    DownloadConfig,
    KeyConfig,
    NetworkConfig,
    PlayerConfig,
    UIConfig,
    _parse_config,
    get_config,
    get_config_path,
    get_data_path,
    get_default_config_toml,
    load_config,
    reload_config,
)


class TestPlayerConfig:
    """Tests for PlayerConfig."""

    def test_default_values(self):
        """Test default player config values."""
        config = PlayerConfig()
        assert config.backend == "vlc"
        assert config.default_volume == 100
        assert config.default_speed == 1.0
        assert config.seek_forward == 30
        assert config.seek_backward == 10
        assert config.resume_rewind == 5

    def test_custom_values(self):
        """Test custom player config values."""
        config = PlayerConfig(
            backend="mpv",
            default_volume=50,
            default_speed=1.5,
        )
        assert config.backend == "mpv"
        assert config.default_volume == 50
        assert config.default_speed == 1.5

    def test_volume_validation(self):
        """Test volume validation."""
        with pytest.raises(ValueError):
            PlayerConfig(default_volume=101)
        with pytest.raises(ValueError):
            PlayerConfig(default_volume=-1)

    def test_speed_validation(self):
        """Test speed validation."""
        with pytest.raises(ValueError):
            PlayerConfig(default_speed=0.4)
        with pytest.raises(ValueError):
            PlayerConfig(default_speed=2.1)


class TestUIConfig:
    """Tests for UIConfig."""

    def test_default_values(self):
        """Test default UI config values."""
        config = UIConfig()
        assert config.theme == "dark"
        assert config.default_layout == 1
        assert config.show_descriptions is True
        assert config.disable_vertical_borders is False
        assert config.refresh_delay == 100


class TestKeyConfig:
    """Tests for KeyConfig."""

    def test_default_values(self):
        """Test default key config values."""
        config = KeyConfig()
        assert config.quit == "q"
        assert config.help == "h"
        # play_pause defaults to a list
        assert config.play_pause == ["p", "space"]
        # seek keys include modifiers
        assert config.seek_forward == ["f", "l", "ctrl+right"]
        assert config.seek_backward == ["b", "j", "ctrl+left"]

    def test_get_keys_single_string(self):
        """Test get_keys returns list for single string."""
        config = KeyConfig()
        keys = config.get_keys("quit")
        assert keys == ["q"]

    def test_get_keys_list(self):
        """Test get_keys returns list for list value."""
        config = KeyConfig()
        keys = config.get_keys("play_pause")
        assert keys == ["p", "space"]

    def test_get_keys_with_modifiers(self):
        """Test get_keys returns modifier keys."""
        config = KeyConfig()
        keys = config.get_keys("seek_forward")
        assert "ctrl+right" in keys
        assert "f" in keys
        assert "l" in keys

    def test_get_keys_unknown_action(self):
        """Test get_keys returns empty list for unknown action."""
        config = KeyConfig()
        keys = config.get_keys("unknown_action")
        assert keys == []

    def test_custom_key_list(self):
        """Test custom key list configuration."""
        config = KeyConfig(quit=["q", "ctrl+q", "escape"])
        assert config.quit == ["q", "ctrl+q", "escape"]
        assert config.get_keys("quit") == ["q", "ctrl+q", "escape"]


class TestNetworkConfig:
    """Tests for NetworkConfig."""

    def test_default_values(self):
        """Test default network config values."""
        config = NetworkConfig()
        assert config.timeout == 30.0
        assert config.max_episodes == -1
        assert config.reload_on_start is False
        assert config.proxy_http == ""
        assert config.proxy_https == ""


class TestDownloadConfig:
    """Tests for DownloadConfig."""

    def test_default_values(self):
        """Test default download config values."""
        config = DownloadConfig()
        assert config.directory == ""
        assert config.concurrent == 3

    def test_concurrent_validation(self):
        """Test concurrent validation."""
        with pytest.raises(ValueError):
            DownloadConfig(concurrent=0)
        with pytest.raises(ValueError):
            DownloadConfig(concurrent=11)


class TestColorConfig:
    """Tests for ColorConfig."""

    def test_default_values(self):
        """Test default color config values."""
        config = ColorConfig()
        assert config.foreground == "white"
        assert config.background == "transparent"
        assert config.foreground_alt == "white"
        assert config.background_alt == "black"


class TestConfig:
    """Tests for the complete Config."""

    def test_default_config(self):
        """Test default complete config."""
        config = Config()
        assert isinstance(config.player, PlayerConfig)
        assert isinstance(config.ui, UIConfig)
        assert isinstance(config.keys, KeyConfig)
        assert isinstance(config.network, NetworkConfig)
        assert isinstance(config.download, DownloadConfig)
        assert isinstance(config.colors, ColorConfig)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_missing_file_creates_default(self, temp_config_path: Path):
        """Test that loading missing file creates default config."""
        config = load_config(temp_config_path)
        assert isinstance(config, Config)
        assert temp_config_path.exists()

    def test_load_existing_file(self, temp_config_path: Path):
        """Test loading an existing config file."""
        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_config_path.write_text("""
[player]
backend = "mpv"
default_volume = 75

[ui]
theme = "light"
""")
        config = load_config(temp_config_path)
        assert config.player.backend == "mpv"
        assert config.player.default_volume == 75
        assert config.ui.theme == "light"

    def test_load_partial_config(self, temp_config_path: Path):
        """Test loading a partial config file with defaults for missing."""
        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_config_path.write_text("""
[player]
backend = "mpv"
""")
        config = load_config(temp_config_path)
        assert config.player.backend == "mpv"
        assert config.player.default_volume == 100  # default
        assert config.ui.theme == "dark"  # default

    def test_load_invalid_toml(self, temp_config_path: Path):
        """Test loading an invalid TOML file returns defaults."""
        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_config_path.write_text("this is not valid toml [[[")
        config = load_config(temp_config_path)
        assert isinstance(config, Config)
        assert config.player.backend == "vlc"  # default


class TestParseConfig:
    """Tests for _parse_config function."""

    def test_parse_empty_dict(self):
        """Test parsing an empty dictionary."""
        config = _parse_config({})
        assert isinstance(config, Config)

    def test_parse_full_dict(self):
        """Test parsing a full dictionary."""
        data = {
            "player": {"backend": "mpv"},
            "ui": {"theme": "light"},
            "keys": {"quit": "x"},
            "network": {"timeout": 60.0},
            "download": {"concurrent": 5},
            "colors": {"foreground": "green"},
        }
        config = _parse_config(data)
        assert config.player.backend == "mpv"
        assert config.ui.theme == "light"
        assert config.keys.quit == "x"
        assert config.network.timeout == 60.0
        assert config.download.concurrent == 5
        assert config.colors.foreground == "green"


class TestGetDefaultConfigToml:
    """Tests for get_default_config_toml function."""

    def test_generates_valid_toml(self, temp_config_path: Path):
        """Test that the default config TOML is valid."""
        import tomllib

        content = get_default_config_toml()
        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_config_path.write_text(content)

        with temp_config_path.open("rb") as f:
            data = tomllib.load(f)

        assert "player" in data
        assert "ui" in data
        assert "keys" in data
        assert "network" in data

    def test_contains_expected_sections(self):
        """Test that the default config contains expected sections."""
        content = get_default_config_toml()
        assert "[player]" in content
        assert "[ui]" in content
        assert "[keys]" in content
        assert "[network]" in content
        assert "[download]" in content
        assert "[colors]" in content


class TestGetConfigPath:
    """Tests for get_config_path function."""

    def test_returns_path(self):
        """Test that get_config_path returns a Path."""
        path = get_config_path()
        assert isinstance(path, Path)
        assert path.name == "config.toml"
        assert "feedback" in str(path)


class TestGetDataPath:
    """Tests for get_data_path function."""

    def test_returns_path(self):
        """Test that get_data_path returns a Path."""
        path = get_data_path()
        assert isinstance(path, Path)
        assert "feedback" in str(path)


class TestGetConfig:
    """Tests for get_config function."""

    def test_returns_config(self) -> None:
        """Test that get_config returns a Config."""
        # Reset global config
        feedback.config._config = None
        config = get_config()
        assert isinstance(config, Config)

    def test_caches_config(self):
        """Test that get_config caches the result."""
        # Reset global config
        feedback.config._config = None
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2


class TestReloadConfig:
    """Tests for reload_config function."""

    def test_reloads_config(self, temp_config_path: Path):
        """Test that reload_config reloads the config."""
        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_config_path.write_text('[player]\nbackend = "mpv"')

        config = reload_config(temp_config_path)
        assert config.player.backend == "mpv"

    def test_reloads_replaces_cached(self, temp_config_path: Path):
        """Test that reload_config replaces the cached config."""
        # Reset global config
        feedback.config._config = Config()
        assert feedback.config._config.player.backend == "vlc"

        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_config_path.write_text('[player]\nbackend = "mpv"')

        reload_config(temp_config_path)
        assert feedback.config._config.player.backend == "mpv"
