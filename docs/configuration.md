# Configuration

Feedback uses a TOML configuration file located at:

```
~/.config/feedback/config.toml
```

A default configuration is created on first run.

## Configuration Sections

### Player

```toml
[player]
backend = "vlc"        # Player backend: "vlc" or "mpv"
default_volume = 100   # Default volume (0-100)
default_speed = 1.0    # Default playback speed (0.5-2.0)
seek_forward = 30      # Seconds to seek forward
seek_backward = 10     # Seconds to seek backward
resume_rewind = 5      # Seconds to rewind when resuming
```

### UI

```toml
[ui]
theme = "dark"                    # UI theme
default_layout = 1                # Default screen (1-3)
show_descriptions = true          # Show episode descriptions
disable_vertical_borders = false  # Hide vertical borders
refresh_delay = 100               # Refresh delay in milliseconds
```

### Keys

Keys can be single values or lists for multiple bindings:

```toml
[keys]
# Single key binding
quit = "q"

# Multiple key bindings
play_pause = ["p", "space"]
seek_forward = ["f", "l", "ctrl+right"]
seek_backward = ["b", "j", "ctrl+left"]
```

Supported modifiers: `ctrl+`, `alt+`, `shift+`

Full key reference:

```toml
[keys]
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
```

### Network

```toml
[network]
timeout = 30.0         # Request timeout in seconds
max_episodes = -1      # Max episodes per feed (-1 = unlimited)
reload_on_start = false  # Reload feeds on startup
proxy_http = ""        # HTTP proxy URL
proxy_https = ""       # HTTPS proxy URL
```

### Download

```toml
[download]
directory = ""   # Custom download directory (empty = default)
concurrent = 3   # Maximum concurrent downloads (1-10)
```

Default download directory: `~/.local/share/feedback/downloads/`

### Colors

```toml
[colors]
foreground = "white"
background = "transparent"
foreground_alt = "white"      # Selection foreground
background_alt = "black"      # Selection background
foreground_dim = "white"      # Played episodes
foreground_status = "yellow"  # Status messages
foreground_heading = "yellow" # Headings
foreground_dividers = "yellow" # Divider lines
```

### Discovery

Enable podcast search using the [Podcast Index API](https://podcastindex.org/):

```toml
[discovery]
api_key = ""      # Your Podcast Index API key
api_secret = ""   # Your Podcast Index API secret
```

To get API credentials:

1. Register at [api.podcastindex.org](https://api.podcastindex.org)
2. Create an API key
3. Add your credentials to the config

Once configured, press `S` to search for podcasts.

## Complete Example

```toml
# ~/.config/feedback/config.toml

[player]
backend = "mpv"
default_volume = 80
default_speed = 1.0
seek_forward = 30
seek_backward = 10

[ui]
theme = "dark"
show_descriptions = true

[keys]
quit = ["q", "ctrl+c"]
play_pause = ["p", "space"]
seek_forward = ["f", "ctrl+right"]
seek_backward = ["b", "ctrl+left"]

[network]
timeout = 60.0
max_episodes = 50

[download]
directory = "~/Podcasts"
concurrent = 5
```

## Data Locations

| Path | Description |
|------|-------------|
| `~/.config/feedback/config.toml` | Configuration file |
| `~/.local/share/feedback/` | Data directory |
| `~/.local/share/feedback/feeds.db` | Feed database |
| `~/.local/share/feedback/downloads/` | Downloaded episodes |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `XDG_CONFIG_HOME` | Override config directory |
| `XDG_DATA_HOME` | Override data directory |
