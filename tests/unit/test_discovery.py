"""Tests for podcast discovery via Podcast Index API."""

import hashlib
from unittest.mock import patch

import httpx
import pytest
import respx

from feedback.feeds.discovery import (
    DiscoveryAuthError,
    DiscoverySearchError,
    PodcastIndexClient,
    PodcastResult,
)


class TestPodcastResult:
    """Tests for PodcastResult dataclass."""

    def test_from_api_full_data(self) -> None:
        """Test creating PodcastResult from complete API response."""
        data = {
            "id": 12345,
            "title": "Test Podcast",
            "url": "https://example.com/feed.xml",
            "description": "A great podcast about testing",
            "author": "Test Author",
            "image": "https://example.com/image.jpg",
            "categories": {"1": "Technology", "2": "Programming"},
            "episodeCount": 100,
            "language": "en",
        }

        result = PodcastResult.from_api(data)

        assert result.id == 12345
        assert result.title == "Test Podcast"
        assert result.url == "https://example.com/feed.xml"
        assert result.description == "A great podcast about testing"
        assert result.author == "Test Author"
        assert result.image_url == "https://example.com/image.jpg"
        assert result.categories == {"1": "Technology", "2": "Programming"}
        assert result.episode_count == 100
        assert result.language == "en"

    def test_from_api_minimal_data(self) -> None:
        """Test creating PodcastResult from minimal API response."""
        data: dict = {}

        result = PodcastResult.from_api(data)

        assert result.id == 0
        assert result.title == ""
        assert result.url == ""
        assert result.description == ""
        assert result.author == ""
        assert result.image_url == ""
        assert result.categories == {}
        assert result.episode_count == 0
        assert result.language == ""

    def test_from_api_partial_data(self) -> None:
        """Test creating PodcastResult from partial API response."""
        data = {
            "id": 999,
            "title": "Partial Podcast",
            "url": "https://example.com/partial.xml",
        }

        result = PodcastResult.from_api(data)

        assert result.id == 999
        assert result.title == "Partial Podcast"
        assert result.url == "https://example.com/partial.xml"
        assert result.description == ""
        assert result.author == ""

    def test_frozen_dataclass(self) -> None:
        """Test that PodcastResult is immutable (frozen)."""
        result = PodcastResult(
            id=1,
            title="Test",
            url="https://example.com/feed.xml",
            description="",
            author="",
            image_url="",
            categories={},
            episode_count=0,
            language="",
        )

        with pytest.raises(AttributeError):
            result.title = "Modified"  # type: ignore[misc]


class TestPodcastIndexClientInit:
    """Tests for PodcastIndexClient initialization."""

    def test_default_timeout(self) -> None:
        """Test client initializes with default timeout."""
        client = PodcastIndexClient(api_key="key", api_secret="secret")
        assert client.timeout == 30.0

    def test_custom_timeout(self) -> None:
        """Test client accepts custom timeout."""
        client = PodcastIndexClient(api_key="key", api_secret="secret", timeout=60.0)
        assert client.timeout == 60.0

    def test_stores_credentials(self) -> None:
        """Test client stores API credentials."""
        client = PodcastIndexClient(api_key="mykey", api_secret="mysecret")
        assert client.api_key == "mykey"
        assert client.api_secret == "mysecret"


class TestPodcastIndexClientAuth:
    """Tests for authentication header generation."""

    def test_auth_headers_structure(self) -> None:
        """Test authentication headers have correct structure."""
        client = PodcastIndexClient(api_key="testkey", api_secret="testsecret")

        with patch("time.time", return_value=1704067200.0):
            headers = client._get_auth_headers()

        assert "X-Auth-Date" in headers
        assert "X-Auth-Key" in headers
        assert "Authorization" in headers
        assert "User-Agent" in headers

    def test_auth_headers_key(self) -> None:
        """Test X-Auth-Key header contains API key."""
        client = PodcastIndexClient(api_key="myapikey", api_secret="secret")
        headers = client._get_auth_headers()
        assert headers["X-Auth-Key"] == "myapikey"

    def test_auth_headers_date(self) -> None:
        """Test X-Auth-Date header contains epoch time."""
        client = PodcastIndexClient(api_key="key", api_secret="secret")

        with patch("time.time", return_value=1704067200.0):
            headers = client._get_auth_headers()

        assert headers["X-Auth-Date"] == "1704067200"

    def test_auth_headers_hash(self) -> None:
        """Test Authorization header contains correct SHA-1 hash."""
        client = PodcastIndexClient(api_key="key", api_secret="secret")

        with patch("time.time", return_value=1704067200.0):
            headers = client._get_auth_headers()

        # Verify the hash is computed correctly
        expected_string = "keysecret1704067200"
        expected_hash = hashlib.sha1(expected_string.encode()).hexdigest()
        assert headers["Authorization"] == expected_hash

    def test_auth_headers_user_agent(self) -> None:
        """Test User-Agent header is set correctly."""
        client = PodcastIndexClient(api_key="key", api_secret="secret")
        headers = client._get_auth_headers()
        assert headers["User-Agent"] == "Feedback/0.1.0"


class TestPodcastIndexClientSearch:
    """Tests for search functionality."""

    @pytest.mark.asyncio
    async def test_search_no_credentials(self) -> None:
        """Test search raises error when credentials not configured."""
        client = PodcastIndexClient(api_key="", api_secret="")

        with pytest.raises(DiscoveryAuthError, match="credentials not configured"):
            await client.search("python")

    @pytest.mark.asyncio
    async def test_search_missing_key(self) -> None:
        """Test search raises error when API key is missing."""
        client = PodcastIndexClient(api_key="", api_secret="secret")

        with pytest.raises(DiscoveryAuthError):
            await client.search("python")

    @pytest.mark.asyncio
    async def test_search_missing_secret(self) -> None:
        """Test search raises error when API secret is missing."""
        client = PodcastIndexClient(api_key="key", api_secret="")

        with pytest.raises(DiscoveryAuthError):
            await client.search("python")

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_success(self) -> None:
        """Test successful search returns results."""
        response_data = {
            "status": "true",
            "feeds": [
                {
                    "id": 1,
                    "title": "Python Podcast",
                    "url": "https://python.fm/feed.xml",
                    "description": "All about Python",
                    "author": "Pythonista",
                    "image": "https://python.fm/logo.jpg",
                    "categories": {},
                    "episodeCount": 50,
                    "language": "en",
                },
                {
                    "id": 2,
                    "title": "Python Tips",
                    "url": "https://tips.fm/feed.xml",
                    "description": "Quick Python tips",
                    "author": "Tipster",
                    "image": "",
                    "categories": {},
                    "episodeCount": 200,
                    "language": "en",
                },
            ],
        }

        respx.get("https://api.podcastindex.org/api/1.0/search/byterm").respond(
            200, json=response_data
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")
        results = await client.search("python")

        assert len(results) == 2
        assert results[0].title == "Python Podcast"
        assert results[1].title == "Python Tips"

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_empty_results(self) -> None:
        """Test search with no results returns empty list."""
        response_data = {"status": "true", "feeds": []}

        respx.get("https://api.podcastindex.org/api/1.0/search/byterm").respond(
            200, json=response_data
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")
        results = await client.search("xyznonexistent")

        assert len(results) == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_status_false(self) -> None:
        """Test search returns empty when status is false."""
        response_data = {"status": "false"}

        respx.get("https://api.podcastindex.org/api/1.0/search/byterm").respond(
            200, json=response_data
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")
        results = await client.search("test")

        assert len(results) == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_max_results(self) -> None:
        """Test search respects max_results parameter."""
        respx.get("https://api.podcastindex.org/api/1.0/search/byterm").respond(
            200, json={"status": "true", "feeds": []}
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")
        await client.search("test", max_results=5)

        # Verify the request was made with correct params
        request = respx.calls.last.request
        assert "max=5" in str(request.url)

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_401_error(self) -> None:
        """Test search raises auth error on 401 response."""
        respx.get("https://api.podcastindex.org/api/1.0/search/byterm").respond(401)

        client = PodcastIndexClient(api_key="key", api_secret="secret")

        with pytest.raises(DiscoveryAuthError, match="Invalid API credentials"):
            await client.search("test")

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_http_error(self) -> None:
        """Test search raises error on HTTP error."""
        respx.get("https://api.podcastindex.org/api/1.0/search/byterm").respond(500)

        client = PodcastIndexClient(api_key="key", api_secret="secret")

        with pytest.raises(DiscoverySearchError, match="HTTP error"):
            await client.search("test")

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_connection_error(self) -> None:
        """Test search raises error on connection failure."""
        respx.get("https://api.podcastindex.org/api/1.0/search/byterm").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")

        with pytest.raises(DiscoverySearchError, match="Request failed"):
            await client.search("test")


class TestPodcastIndexClientSearchByTitle:
    """Tests for search by title functionality."""

    @pytest.mark.asyncio
    async def test_search_by_title_no_credentials(self) -> None:
        """Test search_by_title raises error when credentials not configured."""
        client = PodcastIndexClient(api_key="", api_secret="")

        with pytest.raises(DiscoveryAuthError):
            await client.search_by_title("Podcast Name")

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_by_title_success(self) -> None:
        """Test successful title search returns results."""
        response_data = {
            "status": "true",
            "feeds": [
                {
                    "id": 1,
                    "title": "The Daily",
                    "url": "https://daily.fm/feed.xml",
                    "description": "Daily news",
                    "author": "NYT",
                    "image": "",
                    "categories": {},
                    "episodeCount": 1000,
                    "language": "en",
                },
            ],
        }

        respx.get("https://api.podcastindex.org/api/1.0/search/bytitle").respond(
            200, json=response_data
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")
        results = await client.search_by_title("The Daily")

        assert len(results) == 1
        assert results[0].title == "The Daily"

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_by_title_status_false(self) -> None:
        """Test search_by_title returns empty when status is false."""
        respx.get("https://api.podcastindex.org/api/1.0/search/bytitle").respond(
            200, json={"status": "false"}
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")
        results = await client.search_by_title("Nonexistent")

        assert len(results) == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_by_title_401_error(self) -> None:
        """Test search_by_title raises auth error on 401."""
        respx.get("https://api.podcastindex.org/api/1.0/search/bytitle").respond(401)

        client = PodcastIndexClient(api_key="key", api_secret="secret")

        with pytest.raises(DiscoveryAuthError):
            await client.search_by_title("test")

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_by_title_http_error(self) -> None:
        """Test search_by_title raises error on HTTP error."""
        respx.get("https://api.podcastindex.org/api/1.0/search/bytitle").respond(503)

        client = PodcastIndexClient(api_key="key", api_secret="secret")

        with pytest.raises(DiscoverySearchError):
            await client.search_by_title("test")

    @pytest.mark.asyncio
    @respx.mock
    async def test_search_by_title_request_error(self) -> None:
        """Test search_by_title raises error on request failure."""
        respx.get("https://api.podcastindex.org/api/1.0/search/bytitle").mock(
            side_effect=httpx.TimeoutException("Timeout")
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")

        with pytest.raises(DiscoverySearchError, match="Request failed"):
            await client.search_by_title("test")


class TestPodcastIndexClientTrending:
    """Tests for trending podcasts functionality."""

    @pytest.mark.asyncio
    async def test_trending_no_credentials(self) -> None:
        """Test trending raises error when credentials not configured."""
        client = PodcastIndexClient(api_key="", api_secret="")

        with pytest.raises(DiscoveryAuthError):
            await client.trending()

    @pytest.mark.asyncio
    @respx.mock
    async def test_trending_success(self) -> None:
        """Test successful trending request returns results."""
        response_data = {
            "status": "true",
            "feeds": [
                {
                    "id": 1,
                    "title": "Trending Podcast 1",
                    "url": "https://trend1.fm/feed.xml",
                    "description": "Hot right now",
                    "author": "Trendy",
                    "image": "",
                    "categories": {"1": "Comedy"},
                    "episodeCount": 50,
                    "language": "en",
                },
                {
                    "id": 2,
                    "title": "Trending Podcast 2",
                    "url": "https://trend2.fm/feed.xml",
                    "description": "Also hot",
                    "author": "Also Trendy",
                    "image": "",
                    "categories": {},
                    "episodeCount": 75,
                    "language": "en",
                },
            ],
        }

        respx.get("https://api.podcastindex.org/api/1.0/podcasts/trending").respond(
            200, json=response_data
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")
        results = await client.trending()

        assert len(results) == 2
        assert results[0].title == "Trending Podcast 1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_trending_with_language_filter(self) -> None:
        """Test trending with language filter."""
        respx.get("https://api.podcastindex.org/api/1.0/podcasts/trending").respond(
            200, json={"status": "true", "feeds": []}
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")
        await client.trending(language="es")

        request = respx.calls.last.request
        assert "lang=es" in str(request.url)

    @pytest.mark.asyncio
    @respx.mock
    async def test_trending_with_categories(self) -> None:
        """Test trending with category filter."""
        respx.get("https://api.podcastindex.org/api/1.0/podcasts/trending").respond(
            200, json={"status": "true", "feeds": []}
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")
        await client.trending(categories=["Technology", "Science"])

        request = respx.calls.last.request
        assert "cat=Technology%2CScience" in str(
            request.url
        ) or "cat=Technology,Science" in str(request.url)

    @pytest.mark.asyncio
    @respx.mock
    async def test_trending_with_max_results(self) -> None:
        """Test trending respects max_results."""
        respx.get("https://api.podcastindex.org/api/1.0/podcasts/trending").respond(
            200, json={"status": "true", "feeds": []}
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")
        await client.trending(max_results=10)

        request = respx.calls.last.request
        assert "max=10" in str(request.url)

    @pytest.mark.asyncio
    @respx.mock
    async def test_trending_status_false(self) -> None:
        """Test trending returns empty when status is false."""
        respx.get("https://api.podcastindex.org/api/1.0/podcasts/trending").respond(
            200, json={"status": "false"}
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")
        results = await client.trending()

        assert len(results) == 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_trending_401_error(self) -> None:
        """Test trending raises auth error on 401."""
        respx.get("https://api.podcastindex.org/api/1.0/podcasts/trending").respond(401)

        client = PodcastIndexClient(api_key="key", api_secret="secret")

        with pytest.raises(DiscoveryAuthError):
            await client.trending()

    @pytest.mark.asyncio
    @respx.mock
    async def test_trending_http_error(self) -> None:
        """Test trending raises error on HTTP error."""
        respx.get("https://api.podcastindex.org/api/1.0/podcasts/trending").respond(502)

        client = PodcastIndexClient(api_key="key", api_secret="secret")

        with pytest.raises(DiscoverySearchError):
            await client.trending()

    @pytest.mark.asyncio
    @respx.mock
    async def test_trending_request_error(self) -> None:
        """Test trending raises error on request failure."""
        respx.get("https://api.podcastindex.org/api/1.0/podcasts/trending").mock(
            side_effect=httpx.ReadError("Read failed")
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")

        with pytest.raises(DiscoverySearchError):
            await client.trending()


class TestPodcastIndexClientGetByFeedUrl:
    """Tests for get by feed URL functionality."""

    @pytest.mark.asyncio
    async def test_get_by_feed_url_no_credentials(self) -> None:
        """Test get_by_feed_url raises error when credentials not configured."""
        client = PodcastIndexClient(api_key="", api_secret="")

        with pytest.raises(DiscoveryAuthError):
            await client.get_by_feed_url("https://example.com/feed.xml")

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_by_feed_url_success(self) -> None:
        """Test successful get_by_feed_url returns result."""
        response_data = {
            "status": "true",
            "feed": {
                "id": 12345,
                "title": "Found Podcast",
                "url": "https://example.com/feed.xml",
                "description": "A podcast",
                "author": "Author",
                "image": "https://example.com/image.jpg",
                "categories": {},
                "episodeCount": 100,
                "language": "en",
            },
        }

        respx.get("https://api.podcastindex.org/api/1.0/podcasts/byfeedurl").respond(
            200, json=response_data
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")
        result = await client.get_by_feed_url("https://example.com/feed.xml")

        assert result is not None
        assert result.title == "Found Podcast"
        assert result.id == 12345

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_by_feed_url_not_found(self) -> None:
        """Test get_by_feed_url returns None when not found."""
        response_data = {"status": "true", "feed": None}

        respx.get("https://api.podcastindex.org/api/1.0/podcasts/byfeedurl").respond(
            200, json=response_data
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")
        result = await client.get_by_feed_url("https://nonexistent.com/feed.xml")

        assert result is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_by_feed_url_status_false(self) -> None:
        """Test get_by_feed_url returns None when status is false."""
        respx.get("https://api.podcastindex.org/api/1.0/podcasts/byfeedurl").respond(
            200, json={"status": "false"}
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")
        result = await client.get_by_feed_url("https://example.com/feed.xml")

        assert result is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_by_feed_url_no_feed_key(self) -> None:
        """Test get_by_feed_url returns None when feed key missing."""
        respx.get("https://api.podcastindex.org/api/1.0/podcasts/byfeedurl").respond(
            200, json={"status": "true"}
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")
        result = await client.get_by_feed_url("https://example.com/feed.xml")

        assert result is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_by_feed_url_401_error(self) -> None:
        """Test get_by_feed_url raises auth error on 401."""
        respx.get("https://api.podcastindex.org/api/1.0/podcasts/byfeedurl").respond(
            401
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")

        with pytest.raises(DiscoveryAuthError):
            await client.get_by_feed_url("https://example.com/feed.xml")

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_by_feed_url_http_error(self) -> None:
        """Test get_by_feed_url raises error on HTTP error."""
        respx.get("https://api.podcastindex.org/api/1.0/podcasts/byfeedurl").respond(
            500
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")

        with pytest.raises(DiscoverySearchError):
            await client.get_by_feed_url("https://example.com/feed.xml")

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_by_feed_url_request_error(self) -> None:
        """Test get_by_feed_url raises error on request failure."""
        respx.get("https://api.podcastindex.org/api/1.0/podcasts/byfeedurl").mock(
            side_effect=httpx.ConnectTimeout("Connection timeout")
        )

        client = PodcastIndexClient(api_key="key", api_secret="secret")

        with pytest.raises(DiscoverySearchError):
            await client.get_by_feed_url("https://example.com/feed.xml")
