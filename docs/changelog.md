# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-04

### Added

- Complete rewrite using [Textual](https://textual.textualize.io/) for the TUI
- Modern async-first architecture with `asyncio`
- RSS 2.0 and Atom feed support
- YouTube channel feed support via `yt:videoId` and `media:group` parsing
- VLC and MPV player backends with unified interface
- Concurrent download queue with configurable limits
- Key modifier support (`ctrl+`, `alt+`, `shift+`) in keybindings
- Multiple keybindings per action (e.g., `play_pause = ["p", "space"]`)
- Podcast discovery via Podcast Index API integration
- TOML-based configuration
- SQLite database with async support via `aiosqlite`
- Pydantic models for type-safe data handling
- Comprehensive test suite with 95%+ coverage
- MkDocs documentation with migration guide

### Changed

- Migrated from curses to Textual for better terminal compatibility
- Switched from synchronous to async I/O throughout
- Renamed project from `castero` to `feedback`
- Configuration moved from INI to TOML format
- Data directory moved from `~/.local/share/castero/` to `~/.local/share/feedback/`

### Fixed

- Episode progress no longer resets on feed refresh
- Improved XML parsing for edge cases in RSS feeds
- Better error handling for network failures
- Fixed freeze issues with player state management

### Removed

- Python 3.11 and earlier support (now requires 3.12+)
- curses-based UI
- Synchronous HTTP requests

## Migration from castero

To migrate from castero:

1. Export your subscriptions: `castero export > podcasts.opml`
2. Install feedback: `pip install feedback`
3. Import subscriptions: `feedback import podcasts.opml`

Your downloaded episodes can be copied from:
- Old: `~/.local/share/castero/downloaded/`
- New: `~/.local/share/feedback/downloads/`
