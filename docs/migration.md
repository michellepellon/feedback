# Migration from castero

This guide helps existing castero users migrate to feedback.

## Overview

Feedback is a complete rewrite of castero using modern Python and the Textual framework. While it maintains the same core functionality, the underlying architecture has been rebuilt from scratch.

## Key Differences

| Aspect | castero | feedback |
|--------|---------|----------|
| Python version | 3.6+ | 3.12+ |
| UI framework | curses | Textual |
| I/O model | Synchronous | Async |
| Config format | INI | TOML |
| Database | SQLite | SQLite (async) |

## Step-by-Step Migration

### 1. Export Your Subscriptions

Before installing feedback, export your podcast subscriptions from castero:

```bash
castero export > podcasts.opml
```

This creates an OPML file containing all your feed URLs.

### 2. Install Feedback

Install feedback using pip:

```bash
pip install feedback
```

Or with pipx for isolated installation:

```bash
pipx install feedback
```

### 3. Import Your Subscriptions

Import your subscriptions into feedback:

```bash
feedback import podcasts.opml
```

### 4. Copy Downloaded Episodes (Optional)

If you want to keep your downloaded episodes, copy them to the new location:

```bash
# Create the new downloads directory
mkdir -p ~/.local/share/feedback/downloads/

# Copy your existing downloads
cp -r ~/.local/share/castero/downloaded/* ~/.local/share/feedback/downloads/
```

### 5. Migrate Configuration

Your castero configuration at `~/.config/castero/castero.conf` uses INI format. Feedback uses TOML format at `~/.config/feedback/config.toml`.

Here's how common settings map between the two:

#### Player Settings

**castero.conf (INI):**
```ini
[client]
player = vlc
default_playback_speed = 1.25
seek_distance_forward = 30
seek_distance_backward = 10
```

**config.toml (TOML):**
```toml
[player]
backend = "vlc"
default_speed = 1.25
seek_forward = 30
seek_backward = 10
```

#### Key Bindings

**castero.conf (INI):**
```ini
[keys]
key_quit = q
key_help = h
key_play_pause = p
```

**config.toml (TOML):**
```toml
[keys]
quit = "q"
help = "h"
play_pause = ["p", "space"]  # Now supports multiple bindings!
```

#### UI Settings

**castero.conf (INI):**
```ini
[client]
default_layout = 1
disable_vertical_borders = false
```

**config.toml (TOML):**
```toml
[ui]
default_layout = 1
disable_vertical_borders = false
```

### 6. First Run

Start feedback:

```bash
feedback
```

On first run, feedback will:

1. Create the data directory at `~/.local/share/feedback/`
2. Create a default config at `~/.config/feedback/config.toml`
3. Initialize the database

## Data Locations

| Data | castero | feedback |
|------|---------|----------|
| Config | `~/.config/castero/castero.conf` | `~/.config/feedback/config.toml` |
| Database | `~/.local/share/castero/castero.db` | `~/.local/share/feedback/feedback.db` |
| Downloads | `~/.local/share/castero/downloaded/` | `~/.local/share/feedback/downloads/` |

## New Features in Feedback

Migrating to feedback gives you access to several new features:

### Key Modifier Support

Bind keys with modifiers like `ctrl+`, `alt+`, and `shift+`:

```toml
[keys]
seek_forward = ["f", "ctrl+right"]
seek_backward = ["b", "ctrl+left"]
```

### Multiple Key Bindings

Assign multiple keys to the same action:

```toml
[keys]
play_pause = ["p", "space", "enter"]
```

### Podcast Discovery

Search for new podcasts using the Podcast Index API:

```toml
[discovery]
api_key = "your-api-key"
api_secret = "your-api-secret"
```

Register for free at [podcastindex.org](https://api.podcastindex.org) to get credentials.

### Improved Async Performance

Feedback uses async I/O throughout, resulting in:

- Faster feed refreshes (concurrent fetching)
- Non-blocking downloads
- Smoother UI responsiveness

## Troubleshooting

### Missing Episodes After Migration

If episodes don't appear after importing your OPML:

1. Refresh all feeds: Press `r` in the app
2. Check feed URLs are accessible
3. Verify network connectivity

### Player Not Working

Ensure you have VLC or MPV installed:

```bash
# macOS
brew install vlc
# or
brew install mpv

# Ubuntu/Debian
sudo apt install vlc
# or
sudo apt install mpv
```

Set your preferred player in config:

```toml
[player]
backend = "vlc"  # or "mpv"
```

### Configuration Errors

If feedback fails to start, check your TOML syntax:

```bash
# Validate TOML syntax
python -c "import tomllib; tomllib.load(open('~/.config/feedback/config.toml', 'rb'))"
```

Delete the config to reset to defaults:

```bash
rm ~/.config/feedback/config.toml
feedback  # Will regenerate default config
```

## Getting Help

- Report issues: [github.com/michellepellon/feedback/issues](https://github.com/michellepellon/feedback/issues)
- Documentation: [michellepellon.github.io/feedback](https://michellepellon.github.io/feedback)
