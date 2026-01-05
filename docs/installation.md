# Installation

## Requirements

- Python 3.12 or higher
- VLC or MPV media player

## Install from PyPI

```bash
pip install feedback
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv tool install feedback
```

## Install from Source

```bash
git clone https://github.com/xgi/feedback.git
cd feedback
uv sync
uv run feedback
```

## Player Setup

Feedback requires either VLC or MPV for audio playback.

### VLC (Recommended)

**macOS:**
```bash
brew install vlc
```

**Ubuntu/Debian:**
```bash
sudo apt install vlc
```

**Fedora:**
```bash
sudo dnf install vlc
```

### MPV

**macOS:**
```bash
brew install mpv
```

**Ubuntu/Debian:**
```bash
sudo apt install mpv
```

**Fedora:**
```bash
sudo dnf install mpv
```

## Verify Installation

```bash
feedback --version
```

## Troubleshooting

### "No module named 'vlc'"

Install python-vlc bindings:
```bash
pip install python-vlc
```

### "MPV not found"

Ensure MPV is in your PATH:
```bash
which mpv
```

### Permission Issues

If you encounter permission issues with the config directory:
```bash
mkdir -p ~/.config/feedback
chmod 755 ~/.config/feedback
```
