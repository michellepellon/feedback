"""Pytest configuration and fixtures for feedback tests."""

import asyncio
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio

from feedback.config import Config
from feedback.database import Database


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default event loop policy."""
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db_path(temp_dir: Path) -> Path:
    """Path for a temporary test database."""
    return temp_dir / "test.db"


@pytest_asyncio.fixture
async def database(temp_db_path: Path) -> AsyncIterator[Database]:
    """Create a connected test database."""
    db = Database(temp_db_path)
    await db.connect()
    try:
        yield db
    finally:
        await db.close()


@pytest.fixture
def default_config() -> Config:
    """Create a default configuration."""
    return Config()


@pytest.fixture
def temp_config_path(temp_dir: Path) -> Path:
    """Path for a temporary config file."""
    return temp_dir / "config.toml"


@pytest.fixture
def sample_feed_data() -> dict:
    """Sample feed data for testing."""
    return {
        "key": "https://example.com/feed.xml",
        "title": "Test Podcast",
        "description": "A test podcast feed",
        "link": "https://example.com",
    }


@pytest.fixture
def sample_episode_data() -> dict:
    """Sample episode data for testing."""
    return {
        "feed_key": "https://example.com/feed.xml",
        "title": "Episode 1",
        "description": "The first episode",
        "enclosure": "https://example.com/episode1.mp3",
    }


# Sample RSS feed XML for testing
SAMPLE_RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Podcast</title>
    <link>https://example.com</link>
    <description>A test podcast</description>
    <lastBuildDate>Mon, 01 Jan 2024 00:00:00 +0000</lastBuildDate>
    <item>
      <title>Episode 1</title>
      <description>First episode description</description>
      <link>https://example.com/ep1</link>
      <pubDate>Mon, 01 Jan 2024 00:00:00 +0000</pubDate>
      <enclosure url="https://example.com/ep1.mp3" type="audio/mpeg" length="12345"/>
    </item>
    <item>
      <title>Episode 2</title>
      <description>Second episode description</description>
      <link>https://example.com/ep2</link>
      <pubDate>Tue, 02 Jan 2024 00:00:00 +0000</pubDate>
      <enclosure url="https://example.com/ep2.mp3" type="audio/mpeg" length="67890"/>
    </item>
  </channel>
</rss>
"""


@pytest.fixture
def sample_rss_feed() -> str:
    """Sample RSS feed XML."""
    return SAMPLE_RSS_FEED
