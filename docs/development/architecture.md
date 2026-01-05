# Architecture

## Overview

Feedback is built with a modern async-first architecture using Python 3.12+.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Textual UI                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Screens   │  │   Widgets   │  │    Player Bar           │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────────┐
│                      Core Services                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Player    │  │  Fetcher    │  │   Download Queue        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────────┐
│                       Data Layer                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Models    │  │  Database   │  │    Config               │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
src/feedback/
├── __init__.py          # Package metadata
├── __main__.py          # CLI entry point
├── app.py               # Textual App class
├── config.py            # Configuration system
├── database.py          # Async SQLite layer
├── downloads.py         # Download queue
├── feeds/
│   ├── __init__.py
│   └── fetcher.py       # RSS/Atom parser
├── models/
│   ├── __init__.py
│   └── feed.py          # Pydantic models
├── player/
│   ├── __init__.py
│   ├── base.py          # Player protocol
│   ├── vlc.py           # VLC backend
│   └── mpv.py           # MPV backend
├── screens/
│   ├── __init__.py
│   ├── primary.py       # Main feed screen
│   ├── queue.py         # Queue screen
│   └── downloads.py     # Downloads screen
├── styles/
│   └── app.tcss         # Textual CSS
└── widgets/
    ├── __init__.py
    ├── feed_list.py     # Feed list widget
    ├── episode_list.py  # Episode list widget
    ├── player_bar.py    # Playback status
    ├── queue_list.py    # Queue widget
    └── download_list.py # Downloads widget
```

## Key Components

### Models (`models/feed.py`)

Pydantic models for type-safe data:

```python
class Feed(BaseModel):
    key: str              # Unique identifier (URL)
    title: str
    description: str
    link: str
    last_build_date: datetime | None
    copyright: str | None

class Episode(BaseModel):
    id: int | None
    feed_key: str
    title: str
    enclosure: str        # Media URL
    pubdate: datetime | None
    played: bool
    progress_ms: int
```

### Database (`database.py`)

Async SQLite with `aiosqlite`:

```python
class Database:
    async def connect(self) -> None
    async def close(self) -> None

    # Feed operations
    async def get_feeds(self) -> list[Feed]
    async def upsert_feed(self, feed: Feed) -> None
    async def delete_feed(self, key: str) -> None

    # Episode operations
    async def get_episodes(self, feed_key: str) -> list[Episode]
    async def update_progress(self, id: int, progress_ms: int) -> None
```

### Feed Fetcher (`feeds/fetcher.py`)

Async HTTP with RSS/Atom parsing:

```python
class FeedFetcher:
    async def fetch(self, url: str) -> tuple[Feed, list[Episode]]
    async def fetch_many(self, urls: list[str]) -> list[...]

    def _parse_rss(self, root) -> tuple[Feed, list[Episode]]
    def _parse_atom(self, root) -> tuple[Feed, list[Episode]]
```

### Player (`player/base.py`)

Protocol-based player abstraction:

```python
class PlayerState(Enum):
    STOPPED = 0
    PLAYING = 1
    PAUSED = 2

class Player(Protocol):
    @property
    def state(self) -> PlayerState: ...
    @property
    def position_ms(self) -> int: ...

    async def play(self, path: str, start_ms: int = 0) -> None
    async def pause(self) -> None
    async def seek(self, position_ms: int) -> None
```

### Download Queue (`downloads.py`)

Concurrent download manager:

```python
class DownloadQueue:
    max_concurrent: int = 3

    async def add(self, url: str, filename: str) -> DownloadItem
    async def add_batch(self, downloads: list[tuple]) -> list[DownloadItem]
    async def cancel(self, url: str) -> bool
    def set_progress_callback(self, callback) -> None
```

### Textual UI (`app.py`)

Screen-based UI with widgets:

```python
class FeedbackApp(App):
    SCREENS = {
        "primary": PrimaryScreen,
        "queue": QueueScreen,
        "downloads": DownloadsScreen,
    }

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("1", "switch_screen('primary')", "Feeds"),
        ...
    ]
```

## Data Flow

### Feed Refresh

```
User Action → FeedFetcher.fetch() → Parse XML → Database.upsert_feed()
                                              → Database.upsert_episode()
                                              → Update UI
```

### Episode Playback

```
User Select → Database.get_episode() → Player.play() → PlayerBar updates
                                     ↓
                                Update progress_ms periodically
                                     ↓
                                Database.update_progress()
```

### Download

```
User Request → DownloadQueue.add() → HTTP stream → Write to disk
                                   ↓
                           Progress callback → UI update
                                   ↓
                           Database.update downloaded_path
```

## Testing Strategy

- **Unit tests**: Models, config, parsers
- **Integration tests**: Database, HTTP mocking
- **UI tests**: Textual pilot testing

Coverage target: 95%+
