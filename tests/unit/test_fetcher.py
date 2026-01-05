"""Tests for feed fetcher."""

from pathlib import Path

import httpx
import pytest
import respx
from lxml import etree

from feedback.feeds import FeedFetcher, FeedFetchError, FeedParseError
from feedback.feeds.fetcher import _get_attr, _get_text, _parse_date

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "feeds"


class TestParseDateHelper:
    """Tests for _parse_date helper function."""

    def test_parse_rfc822(self) -> None:
        """Test parsing RFC 822 date format."""
        result = _parse_date("Mon, 01 Jan 2024 12:00:00 +0000")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_parse_iso8601(self) -> None:
        """Test parsing ISO 8601 date format."""
        result = _parse_date("2024-01-01T12:00:00Z")
        assert result is not None
        assert result.year == 2024

    def test_parse_iso8601_with_timezone(self) -> None:
        """Test parsing ISO 8601 with timezone."""
        result = _parse_date("2024-01-01T12:00:00+0000")
        assert result is not None
        assert result.year == 2024

    def test_parse_date_only(self) -> None:
        """Test parsing date-only format."""
        result = _parse_date("2024-01-15")
        assert result is not None
        assert result.day == 15

    def test_parse_none(self) -> None:
        """Test parsing None returns None."""
        assert _parse_date(None) is None

    def test_parse_empty(self) -> None:
        """Test parsing empty string returns None."""
        assert _parse_date("") is None

    def test_parse_invalid(self) -> None:
        """Test parsing invalid date returns None."""
        assert _parse_date("not a date") is None

    def test_parse_strips_whitespace(self) -> None:
        """Test that whitespace is stripped."""
        result = _parse_date("  2024-01-01  ")
        assert result is not None


class TestGetTextHelper:
    """Tests for _get_text helper function."""

    def test_get_text_with_content(self) -> None:
        """Test getting text from element with content."""
        elem = etree.fromstring("<title>Hello World</title>")
        assert _get_text(elem) == "Hello World"

    def test_get_text_none_element(self) -> None:
        """Test getting text from None returns default."""
        assert _get_text(None) == ""
        assert _get_text(None, "default") == "default"

    def test_get_text_empty_element(self) -> None:
        """Test getting text from empty element."""
        elem = etree.fromstring("<title></title>")
        assert _get_text(elem) == ""

    def test_get_text_strips_whitespace(self) -> None:
        """Test that whitespace is stripped."""
        elem = etree.fromstring("<title>  spaced  </title>")
        assert _get_text(elem) == "spaced"


class TestGetAttrHelper:
    """Tests for _get_attr helper function."""

    def test_get_attr_exists(self) -> None:
        """Test getting existing attribute."""
        elem = etree.fromstring('<link href="https://example.com"/>')
        assert _get_attr(elem, "href") == "https://example.com"

    def test_get_attr_none_element(self) -> None:
        """Test getting attribute from None returns default."""
        assert _get_attr(None, "href") == ""
        assert _get_attr(None, "href", "default") == "default"

    def test_get_attr_missing(self) -> None:
        """Test getting missing attribute returns default."""
        elem = etree.fromstring("<link/>")
        assert _get_attr(elem, "href") == ""
        assert _get_attr(elem, "href", "default") == "default"


class TestFeedFetcherInit:
    """Tests for FeedFetcher initialization."""

    def test_default_values(self) -> None:
        """Test default initialization values."""
        fetcher = FeedFetcher()
        assert fetcher.timeout == 30.0
        assert fetcher.max_episodes == -1
        assert fetcher.user_agent == "Feedback/0.1.0"

    def test_custom_values(self) -> None:
        """Test custom initialization values."""
        fetcher = FeedFetcher(timeout=60.0, max_episodes=10, user_agent="Test/1.0")
        assert fetcher.timeout == 60.0
        assert fetcher.max_episodes == 10
        assert fetcher.user_agent == "Test/1.0"


class TestFeedFetcherParseRSS:
    """Tests for RSS parsing."""

    def test_parse_valid_rss(self) -> None:
        """Test parsing a valid RSS feed."""
        fetcher = FeedFetcher()
        content = (FIXTURES_DIR / "valid_rss.xml").read_bytes()
        feed, episodes = fetcher._parse_feed("https://example.com/feed", content)

        assert feed.key == "https://example.com/feed"
        assert feed.title == "Test Podcast"
        assert feed.description == "A test podcast for unit testing"
        assert feed.link == "https://example.com/podcast"
        assert feed.last_build_date is not None
        assert feed.copyright == "2024 Test Author"

        # Should have 2 episodes (one has no enclosure)
        assert len(episodes) == 2
        assert episodes[0].title == "Episode 1"
        assert episodes[0].enclosure == "https://example.com/ep1.mp3"
        assert episodes[0].pubdate is not None
        assert episodes[1].title == "Episode 2"
        assert episodes[1].copyright == "Episode 2 copyright"

    def test_parse_minimal_rss(self) -> None:
        """Test parsing minimal RSS with defaults."""
        fetcher = FeedFetcher()
        content = (FIXTURES_DIR / "minimal_rss.xml").read_bytes()
        feed, episodes = fetcher._parse_feed("https://example.com/feed", content)

        assert feed.title == "Minimal Podcast"
        assert feed.description == ""
        assert len(episodes) == 1
        assert episodes[0].title == "Untitled"

    def test_parse_rss_no_channel(self) -> None:
        """Test parsing RSS without channel raises error."""
        fetcher = FeedFetcher()
        content = (FIXTURES_DIR / "no_channel.xml").read_bytes()

        with pytest.raises(FeedParseError, match="Missing <channel>"):
            fetcher._parse_feed("https://example.com/feed", content)

    def test_parse_rss_max_episodes(self) -> None:
        """Test max_episodes limits results."""
        fetcher = FeedFetcher(max_episodes=1)
        content = (FIXTURES_DIR / "valid_rss.xml").read_bytes()
        _feed, episodes = fetcher._parse_feed("https://example.com/feed", content)

        assert len(episodes) == 1
        assert episodes[0].title == "Episode 1"


class TestFeedFetcherParseAtom:
    """Tests for Atom parsing."""

    def test_parse_valid_atom(self) -> None:
        """Test parsing a valid Atom feed."""
        fetcher = FeedFetcher()
        content = (FIXTURES_DIR / "valid_atom.xml").read_bytes()
        feed, episodes = fetcher._parse_feed("https://example.com/feed", content)

        assert feed.key == "https://example.com/feed"
        assert feed.title == "Atom Test Feed"
        assert feed.description == "An Atom feed for testing"
        assert feed.link == "https://example.com"
        assert feed.last_build_date is not None
        assert feed.copyright == "2024 Atom Author"

        # Should have 2 episodes (one has no enclosure)
        assert len(episodes) == 2
        assert episodes[0].title == "Atom Episode 1"
        assert episodes[0].enclosure == "https://example.com/atom1.mp3"
        assert episodes[0].description == "First Atom episode"
        assert episodes[1].title == "Atom Episode 2"
        assert episodes[1].description == "Full content for episode 2"
        assert episodes[1].copyright == "Episode rights"

    def test_parse_atom_max_episodes(self) -> None:
        """Test max_episodes limits Atom results."""
        fetcher = FeedFetcher(max_episodes=1)
        content = (FIXTURES_DIR / "valid_atom.xml").read_bytes()
        _feed, episodes = fetcher._parse_feed("https://example.com/feed", content)

        assert len(episodes) == 1


class TestFeedFetcherParseYouTube:
    """Tests for YouTube Atom feed parsing."""

    def test_parse_youtube_atom(self) -> None:
        """Test parsing a YouTube Atom feed."""
        fetcher = FeedFetcher()
        content = (FIXTURES_DIR / "youtube_atom.xml").read_bytes()
        feed, episodes = fetcher._parse_feed(
            "https://www.youtube.com/feeds/videos.xml?channel_id=UC123", content
        )

        assert feed.key == "https://www.youtube.com/feeds/videos.xml?channel_id=UC123"
        assert feed.title == "Test YouTube Channel"
        assert feed.link == "https://www.youtube.com/channel/UC123"

        # Should have 2 episodes
        assert len(episodes) == 2

        # Check first episode - uses media:content URL
        assert episodes[0].title == "Test Video 1"
        assert "youtube.com" in episodes[0].enclosure
        assert episodes[0].description == "This is the first test video description."
        assert episodes[0].link == "https://www.youtube.com/watch?v=abc123"
        assert episodes[0].pubdate is not None

        # Check second episode
        assert episodes[1].title == "Test Video 2"
        assert "youtube.com" in episodes[1].enclosure
        assert episodes[1].description == "This is the second test video description."

    def test_parse_youtube_uses_video_id(self) -> None:
        """Test YouTube parsing falls back to yt:videoId."""
        fetcher = FeedFetcher()
        content = (FIXTURES_DIR / "youtube_atom.xml").read_bytes()
        _feed, episodes = fetcher._parse_feed(
            "https://www.youtube.com/feeds/videos.xml?channel_id=UC123", content
        )

        # All episodes should have enclosure URLs
        for episode in episodes:
            assert episode.enclosure != ""
            assert "youtube.com" in episode.enclosure


class TestFeedFetcherParseErrors:
    """Tests for parsing error handling."""

    def test_parse_invalid_xml(self) -> None:
        """Test parsing invalid XML raises error."""
        fetcher = FeedFetcher()
        content = (FIXTURES_DIR / "invalid.xml").read_bytes()

        with pytest.raises(FeedParseError, match="Invalid XML"):
            fetcher._parse_feed("https://example.com/feed", content)

    def test_parse_unknown_format(self) -> None:
        """Test parsing unknown format raises error."""
        fetcher = FeedFetcher()
        content = (FIXTURES_DIR / "unknown_format.xml").read_bytes()

        with pytest.raises(FeedParseError, match="Unknown feed format"):
            fetcher._parse_feed("https://example.com/feed", content)


class TestFeedFetcherHTTP:
    """Tests for HTTP fetching with mocked responses."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_success(self) -> None:
        """Test successful feed fetch."""
        content = (FIXTURES_DIR / "valid_rss.xml").read_bytes()
        respx.get("https://example.com/feed").respond(200, content=content)

        fetcher = FeedFetcher()
        feed, episodes = await fetcher.fetch("https://example.com/feed")

        assert feed.title == "Test Podcast"
        assert len(episodes) == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_timeout(self) -> None:
        """Test fetch timeout raises error."""
        respx.get("https://example.com/feed").mock(
            side_effect=httpx.TimeoutException("timeout")
        )

        fetcher = FeedFetcher()
        with pytest.raises(FeedFetchError, match="timed out"):
            await fetcher.fetch("https://example.com/feed")

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_http_error(self) -> None:
        """Test HTTP error raises FeedFetchError."""
        respx.get("https://example.com/feed").respond(404)

        fetcher = FeedFetcher()
        with pytest.raises(FeedFetchError, match="HTTP 404"):
            await fetcher.fetch("https://example.com/feed")

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_connection_error(self) -> None:
        """Test connection error raises FeedFetchError."""
        respx.get("https://example.com/feed").mock(
            side_effect=httpx.ConnectError("connection failed")
        )

        fetcher = FeedFetcher()
        with pytest.raises(FeedFetchError, match="connection failed"):
            await fetcher.fetch("https://example.com/feed")

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_many_success(self) -> None:
        """Test fetching multiple feeds."""
        content1 = (FIXTURES_DIR / "valid_rss.xml").read_bytes()
        content2 = (FIXTURES_DIR / "valid_atom.xml").read_bytes()

        respx.get("https://example.com/feed1").respond(200, content=content1)
        respx.get("https://example.com/feed2").respond(200, content=content2)

        fetcher = FeedFetcher()
        results = await fetcher.fetch_many(
            [
                "https://example.com/feed1",
                "https://example.com/feed2",
            ]
        )

        assert len(results) == 2
        # Results may be in any order due to as_completed
        titles = set()
        for result in results:
            assert not isinstance(result, Exception)
            feed, _ = result
            titles.add(feed.title)
        assert titles == {"Test Podcast", "Atom Test Feed"}

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_many_partial_failure(self) -> None:
        """Test fetch_many handles partial failures."""
        content = (FIXTURES_DIR / "valid_rss.xml").read_bytes()

        respx.get("https://example.com/feed1").respond(200, content=content)
        respx.get("https://example.com/feed2").respond(500)

        fetcher = FeedFetcher()
        results = await fetcher.fetch_many(
            [
                "https://example.com/feed1",
                "https://example.com/feed2",
            ]
        )

        assert len(results) == 2
        successes = [r for r in results if not isinstance(r, Exception)]
        failures = [r for r in results if isinstance(r, Exception)]
        assert len(successes) == 1
        assert len(failures) == 1


class TestFeedFetcherContentEncoded:
    """Tests for content:encoded handling."""

    def test_content_encoded_preferred(self) -> None:
        """Test that content:encoded is preferred over description."""
        fetcher = FeedFetcher()
        content = b"""<?xml version="1.0"?>
        <rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
          <channel>
            <title>Test</title>
            <item>
              <title>Ep</title>
              <description>Short desc</description>
              <content:encoded><![CDATA[<p>Full HTML content</p>]]></content:encoded>
              <enclosure url="https://example.com/ep.mp3" type="audio/mpeg"/>
            </item>
          </channel>
        </rss>
        """
        _feed, episodes = fetcher._parse_feed("https://example.com/feed", content)
        assert "<p>Full HTML content</p>" in episodes[0].description


class TestFeedFetcherItunesSummary:
    """Tests for itunes:summary handling."""

    def test_itunes_summary_fallback(self) -> None:
        """Test itunes:summary is used when description is missing."""
        fetcher = FeedFetcher()
        content = b"""<?xml version="1.0"?>
        <rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
          <channel>
            <title>Test</title>
            <item>
              <title>Ep</title>
              <itunes:summary>iTunes summary text</itunes:summary>
              <enclosure url="https://example.com/ep.mp3" type="audio/mpeg"/>
            </item>
          </channel>
        </rss>
        """
        _feed, episodes = fetcher._parse_feed("https://example.com/feed", content)
        assert episodes[0].description == "iTunes summary text"


class TestFeedFetcherAtomNoNamespace:
    """Tests for Atom feeds without namespace prefix."""

    def test_atom_without_namespace(self) -> None:
        """Test parsing Atom feed without namespace prefix."""
        fetcher = FeedFetcher()
        content = b"""<?xml version="1.0"?>
        <feed>
          <title>No NS Feed</title>
          <entry>
            <title>Entry</title>
            <link href="https://example.com/ep.mp3" rel="enclosure"/>
            <published>2024-01-01T00:00:00Z</published>
          </entry>
        </feed>
        """
        feed, episodes = fetcher._parse_feed("https://example.com/feed", content)
        assert feed.title == "No NS Feed"
        assert len(episodes) == 1


class TestFeedFetcherAtomLinkFallback:
    """Tests for Atom link fallback behavior."""

    def test_atom_self_link_fallback(self) -> None:
        """Test Atom uses self link when no alternate."""
        fetcher = FeedFetcher()
        content = b"""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>Self Link Only</title>
          <link href="https://example.com/self" rel="self"/>
          <entry>
            <title>Entry</title>
            <link href="https://example.com/ep.mp3" rel="enclosure"/>
          </entry>
        </feed>
        """
        feed, _episodes = fetcher._parse_feed("https://example.com/feed", content)
        assert feed.link == "https://example.com/self"


class TestFeedFetcherEdgeCases:
    """Tests for edge cases and full branch coverage."""

    def test_rss_enclosure_without_url(self) -> None:
        """Test RSS item with enclosure element but no url attribute."""
        fetcher = FeedFetcher()
        content = b"""<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Test</title>
            <item>
              <title>No URL</title>
              <enclosure type="audio/mpeg"/>
            </item>
          </channel>
        </rss>
        """
        _feed, episodes = fetcher._parse_feed("https://example.com/feed", content)
        assert len(episodes) == 0

    def test_atom_entry_with_alternate_link(self) -> None:
        """Test Atom entry with both enclosure and alternate links."""
        fetcher = FeedFetcher()
        content = b"""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>Test</title>
          <entry>
            <title>Entry</title>
            <link href="https://example.com/page" rel="alternate"/>
            <link href="https://example.com/ep.mp3" rel="enclosure"/>
          </entry>
        </feed>
        """
        _feed, episodes = fetcher._parse_feed("https://example.com/feed", content)
        assert len(episodes) == 1
        assert episodes[0].link == "https://example.com/page"

    def test_atom_feed_alternate_before_self(self) -> None:
        """Test Atom feed with alternate link appearing before self."""
        fetcher = FeedFetcher()
        content = b"""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>Test</title>
          <link href="https://example.com/alt" rel="alternate"/>
          <link href="https://example.com/self" rel="self"/>
          <entry>
            <title>Entry</title>
            <link href="https://example.com/ep.mp3" rel="enclosure"/>
          </entry>
        </feed>
        """
        feed, _episodes = fetcher._parse_feed("https://example.com/feed", content)
        assert feed.link == "https://example.com/alt"

    def test_atom_feed_self_then_alternate(self) -> None:
        """Test Atom feed where self link comes before alternate."""
        fetcher = FeedFetcher()
        content = b"""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>Test</title>
          <link href="https://example.com/self" rel="self"/>
          <link href="https://example.com/other" rel="other"/>
          <link href="https://example.com/alt" rel="alternate"/>
          <entry>
            <title>Entry</title>
            <link href="https://example.com/ep.mp3" rel="enclosure"/>
          </entry>
        </feed>
        """
        feed, _episodes = fetcher._parse_feed("https://example.com/feed", content)
        # Should prefer alternate even though self came first
        assert feed.link == "https://example.com/alt"

    def test_atom_entry_multiple_links(self) -> None:
        """Test Atom entry with multiple link types to cover all branches."""
        fetcher = FeedFetcher()
        content = b"""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <title>Test</title>
          <entry>
            <title>Entry</title>
            <link href="https://example.com/other" rel="other"/>
            <link href="https://example.com/alt" rel="alternate"/>
            <link href="https://example.com/ep.mp3" rel="enclosure"/>
          </entry>
        </feed>
        """
        _feed, episodes = fetcher._parse_feed("https://example.com/feed", content)
        assert len(episodes) == 1
        assert episodes[0].link == "https://example.com/alt"
