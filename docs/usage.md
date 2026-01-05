# Usage Guide

## Starting Feedback

Launch feedback from your terminal:

```bash
feedback
```

## Interface Overview

Feedback uses a three-pane layout:

```
┌─────────────────────────────────────────────────────────┐
│                      Player Bar                          │
├──────────────────┬──────────────────────────────────────┤
│                  │                                       │
│    Feed List     │           Episode List                │
│                  │                                       │
│                  ├──────────────────────────────────────┤
│                  │         Episode Details               │
│                  │                                       │
├──────────────────┴──────────────────────────────────────┤
│                      Footer                              │
└─────────────────────────────────────────────────────────┘
```

## Screens

Switch between screens using number keys:

| Key | Screen | Description |
|-----|--------|-------------|
| `1` | Feeds | Main view with feeds and episodes |
| `2` | Queue | Playback queue management |
| `3` | Downloads | Download progress and management |

## Navigation

### Basic Navigation

| Key | Action |
|-----|--------|
| `j` / `↓` | Move down |
| `k` / `↑` | Move up |
| `Enter` | Select / Play |
| `Tab` | Switch pane |
| `Shift+Tab` | Previous pane |

### Feed Management

| Key | Action |
|-----|--------|
| `a` | Add new feed |
| `d` | Delete selected feed |
| `r` | Refresh all feeds |
| `R` | Refresh selected feed |

### Playback Controls

| Key | Action |
|-----|--------|
| `p` / `Space` | Play / Pause |
| `f` / `l` / `Ctrl+→` | Seek forward |
| `b` / `j` / `Ctrl+←` | Seek backward |
| `=` | Volume up |
| `-` | Volume down |
| `]` | Speed up |
| `[` | Speed down |

### Episode Actions

| Key | Action |
|-----|--------|
| `s` | Download episode |
| `x` | Delete download |
| `m` | Mark as played |
| `Space` | Add to queue |

### Queue Management

| Key | Action |
|-----|--------|
| `c` | Clear queue |
| `n` | Next episode |
| `u` | Move item up |
| `n` | Move item down |

### Other

| Key | Action |
|-----|--------|
| `?` | Show help |
| `q` | Quit |

## Adding Feeds

1. Press `a` to open the add feed dialog
2. Enter the RSS/Atom feed URL
3. Press `Enter` to subscribe

Feedback supports:
- Standard RSS 2.0 feeds
- Atom feeds
- YouTube channel feeds (`https://www.youtube.com/feeds/videos.xml?channel_id=...`)

## Playing Episodes

1. Navigate to an episode using `j`/`k`
2. Press `Enter` to start playback
3. Use playback controls to pause, seek, or adjust volume

The player bar at the top shows:
- Current episode title
- Playback status (Playing/Paused/Stopped)
- Progress bar
- Current time / Total duration

## Queue Management

Add episodes to queue for continuous playback:

1. Select an episode
2. Press `Space` to add to queue
3. Press `2` to view queue
4. Press `Enter` to start queue playback

## Downloading Episodes

Download episodes for offline listening:

1. Select an episode
2. Press `s` to start download
3. Press `3` to view download progress

Downloads are saved to `~/.local/share/feedback/downloads/` by default.

## OPML Import/Export

Import subscriptions from other podcast apps:

```bash
feedback import subscriptions.opml
```

Export your subscriptions:

```bash
feedback export > my-podcasts.opml
```
