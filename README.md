# Feedback

A modern TUI podcast client for the terminal, built with [Textual](https://textual.textualize.io/).

[![CI](https://github.com/michellepellon/feedback/actions/workflows/ci.yml/badge.svg)](https://github.com/michellepellon/feedback/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/michellepellon/feedback/branch/main/graph/badge.svg)](https://codecov.io/gh/michellepellon/feedback)
[![PyPI version](https://badge.fury.io/py/feedback.svg)](https://badge.fury.io/py/feedback)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## Features

- Subscribe to RSS/Atom podcast feeds
- Search podcasts via Podcast Index API
- Stream or download episodes
- Playback with VLC or MPV
- Progress tracking and resume
- Per-podcast start position (skip intros)
- Queue management
- OPML import/export
- Beautiful terminal UI

## Installation

```bash
pip install feedback
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv tool install feedback
```

### Requirements

- Python 3.12+
- VLC or MPV for audio playback

## Usage

```bash
feedback
```

### Key Bindings

| Key | Action |
|-----|--------|
| `q` | Quit |
| `?` | Help |
| `a` | Add feed |
| `d` | Delete feed |
| `r` | Refresh feeds |
| `S` | Search podcasts |
| `Enter` | Play selected |
| `p` / `Space` | Play/Pause |
| `j` / `k` | Navigate down/up |
| `Tab` | Next pane |
| `1` / `2` / `3` | Switch screens |

## Configuration

Configuration file: `~/.config/feedback/config.toml`

```toml
[player]
backend = "vlc"  # or "mpv"
default_volume = 100

[network]
timeout = 30
max_episodes = 100

# Optional: Podcast Index API for search
[discovery]
api_key = "your-api-key"
api_secret = "your-api-secret"
```

Get free API credentials at [podcastindex.org](https://podcastindex.org/).

## Development

```bash
# Clone the repo
git clone https://github.com/michellepellon/feedback
cd feedback

# Install with dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run linting
uv run ruff check src tests
uv run mypy src

# Run the app
uv run feedback
```

## License

MIT License - see [LICENSE](LICENSE) for details.
