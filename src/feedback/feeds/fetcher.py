"""Async feed fetcher for RSS and Atom feeds."""

from __future__ import annotations

import asyncio
from collections.abc import (
    Callable,  # noqa: TC003 - used at runtime in function signature
)
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

import httpx
from lxml import etree  # type: ignore[import-untyped]

from feedback.models import Episode, Feed

if TYPE_CHECKING:
    from collections.abc import Sequence


class FeedError(Exception):
    """Base exception for feed errors."""


class FeedFetchError(FeedError):
    """Error fetching feed from URL."""

    def __init__(self, url: str, message: str) -> None:
        self.url = url
        super().__init__(f"Failed to fetch {url}: {message}")


class FeedParseError(FeedError):
    """Error parsing feed content."""

    def __init__(self, url: str, message: str) -> None:
        self.url = url
        super().__init__(f"Failed to parse {url}: {message}")


# Common date formats used in RSS/Atom feeds
DATE_FORMATS = [
    "%a, %d %b %Y %H:%M:%S %z",  # RFC 822 (RSS)
    "%a, %d %b %Y %H:%M:%S %Z",  # RFC 822 with timezone name
    "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601 (Atom)
    "%Y-%m-%dT%H:%M:%SZ",  # ISO 8601 UTC
    "%Y-%m-%d %H:%M:%S",  # Simple datetime
    "%Y-%m-%d",  # Date only
]


def _parse_date(date_str: str | None) -> datetime | None:
    """Parse a date string using common feed date formats.

    Args:
        date_str: Date string to parse.

    Returns:
        Parsed datetime or None if parsing fails.
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def _get_text(element: etree._Element | None, default: str = "") -> str:
    """Get text content from an element safely.

    Args:
        element: XML element or None.
        default: Default value if element is None or empty.

    Returns:
        Text content or default.
    """
    if element is None:
        return default
    return (element.text or default).strip()


def _get_attr(element: etree._Element | None, attr: str, default: str = "") -> str:
    """Get attribute value from an element safely.

    Args:
        element: XML element or None.
        attr: Attribute name.
        default: Default value if not found.

    Returns:
        Attribute value or default.
    """
    if element is None:
        return default
    return element.get(attr, default)  # type: ignore[no-any-return]


class FeedFetcher:
    """Async fetcher for RSS and Atom feeds."""

    # XML namespaces used in feeds
    NAMESPACES: ClassVar[dict[str, str]] = {
        "atom": "http://www.w3.org/2005/Atom",
        "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
        "content": "http://purl.org/rss/1.0/modules/content/",
        "media": "http://search.yahoo.com/mrss/",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }

    def __init__(
        self,
        timeout: float = 30.0,
        max_episodes: int = -1,
        user_agent: str = "Feedback/0.1.0",
    ) -> None:
        """Initialize the feed fetcher.

        Args:
            timeout: Request timeout in seconds.
            max_episodes: Maximum episodes to fetch per feed (-1 for unlimited).
            user_agent: User-Agent header for requests.
        """
        self.timeout = timeout
        self.max_episodes = max_episodes
        self.user_agent = user_agent

    async def fetch(self, url: str) -> tuple[Feed, list[Episode]]:
        """Fetch and parse a feed from a URL.

        Args:
            url: Feed URL.

        Returns:
            Tuple of (Feed, list of Episodes).

        Raises:
            FeedFetchError: If fetching fails.
            FeedParseError: If parsing fails.
        """
        content = await self._fetch_content(url)
        return self._parse_feed(url, content)

    async def fetch_many(
        self, urls: Sequence[str]
    ) -> list[tuple[Feed, list[Episode]] | FeedError]:
        """Fetch multiple feeds concurrently.

        Args:
            urls: List of feed URLs.

        Returns:
            List of results (Feed, Episodes) or FeedError for each URL.
        """
        tasks = [self.fetch(url) for url in urls]
        results: list[tuple[Feed, list[Episode]] | FeedError] = []

        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                results.append(result)
            except FeedError as e:
                results.append(e)

        return results

    async def _fetch_content(self, url: str) -> bytes:
        """Fetch raw content from URL.

        Args:
            url: URL to fetch.

        Returns:
            Raw content bytes.

        Raises:
            FeedFetchError: If fetching fails.
        """
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": self.user_agent},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.content
        except httpx.TimeoutException as e:
            raise FeedFetchError(url, "Request timed out") from e
        except httpx.HTTPStatusError as e:
            raise FeedFetchError(url, f"HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise FeedFetchError(url, str(e)) from e

    def _parse_feed(self, url: str, content: bytes) -> tuple[Feed, list[Episode]]:
        """Parse feed content into Feed and Episode objects.

        Args:
            url: Original feed URL (used as key).
            content: Raw XML content.

        Returns:
            Tuple of (Feed, list of Episodes).

        Raises:
            FeedParseError: If parsing fails.
        """
        try:
            root = etree.fromstring(content)
        except etree.XMLSyntaxError as e:
            raise FeedParseError(url, f"Invalid XML: {e}") from e

        # Detect feed type and parse accordingly
        if root.tag == "rss" or root.tag.endswith("}rss"):
            return self._parse_rss(url, root)
        elif root.tag == "{http://www.w3.org/2005/Atom}feed" or root.tag == "feed":
            return self._parse_atom(url, root)
        else:
            raise FeedParseError(url, f"Unknown feed format: {root.tag}")

    def _parse_rss(self, url: str, root: etree._Element) -> tuple[Feed, list[Episode]]:
        """Parse RSS 2.0 feed.

        Args:
            url: Feed URL.
            root: Root XML element.

        Returns:
            Tuple of (Feed, list of Episodes).
        """
        channel = root.find("channel")
        if channel is None:
            raise FeedParseError(url, "Missing <channel> element")

        feed = Feed(
            key=url,
            title=_get_text(channel.find("title"), "Untitled"),
            description=_get_text(channel.find("description")),
            link=_get_text(channel.find("link")),
            last_build_date=_parse_date(_get_text(channel.find("lastBuildDate"))),
            copyright=_get_text(channel.find("copyright")) or None,
        )

        episodes: list[Episode] = []
        items = channel.findall("item")

        if self.max_episodes > 0:
            items = items[: self.max_episodes]

        for item in items:
            episode = self._parse_rss_item(url, item)
            if episode:
                episodes.append(episode)

        return feed, episodes

    def _parse_rss_item(self, feed_key: str, item: etree._Element) -> Episode | None:
        """Parse an RSS item into an Episode.

        Args:
            feed_key: Parent feed key.
            item: Item XML element.

        Returns:
            Episode or None if no enclosure found.
        """
        enclosure = item.find("enclosure")
        if enclosure is None:
            return None

        enclosure_url = _get_attr(enclosure, "url")
        if not enclosure_url:
            return None

        return Episode(
            feed_key=feed_key,
            title=_get_text(item.find("title"), "Untitled"),
            description=self._get_description(item),
            link=_get_text(item.find("link")),
            enclosure=enclosure_url,
            pubdate=_parse_date(_get_text(item.find("pubDate"))),
            copyright=_get_text(item.find("copyright")) or None,
        )

    def _parse_atom(self, url: str, root: etree._Element) -> tuple[Feed, list[Episode]]:
        """Parse Atom feed.

        Args:
            url: Feed URL.
            root: Root XML element.

        Returns:
            Tuple of (Feed, list of Episodes).
        """
        ns = self.NAMESPACES

        # Handle both namespaced and non-namespaced Atom
        def find(element: etree._Element, tag: str) -> etree._Element | None:
            result = element.find(f"atom:{tag}", ns)
            if result is None:
                result = element.find(tag)
            return result

        def findall(element: etree._Element, tag: str) -> list[Any]:
            result = element.findall(f"atom:{tag}", ns)
            if not result:
                result = element.findall(tag)
            return result  # type: ignore[no-any-return]

        title_el = find(root, "title")
        subtitle_el = find(root, "subtitle")

        # Get link - prefer alternate, fall back to self
        link = ""
        for link_el in findall(root, "link"):
            rel = link_el.get("rel", "alternate")
            if rel == "alternate":
                link = link_el.get("href", "")
                break
            elif rel == "self" and not link:
                link = link_el.get("href", "")

        feed = Feed(
            key=url,
            title=_get_text(title_el, "Untitled"),
            description=_get_text(subtitle_el),
            link=link,
            last_build_date=_parse_date(_get_text(find(root, "updated"))),
            copyright=_get_text(find(root, "rights")) or None,
        )

        episodes: list[Episode] = []
        entries = findall(root, "entry")

        if self.max_episodes > 0:
            entries = entries[: self.max_episodes]

        for entry in entries:
            episode = self._parse_atom_entry(url, entry, find, findall)
            if episode:
                episodes.append(episode)

        return feed, episodes

    def _parse_atom_entry(
        self,
        feed_key: str,
        entry: etree._Element,
        find: Callable[[etree._Element, str], etree._Element | None],
        findall: Callable[[etree._Element, str], list[Any]],
    ) -> Episode | None:
        """Parse an Atom entry into an Episode.

        Args:
            feed_key: Parent feed key.
            entry: Entry XML element.
            find: Namespace-aware find function.
            findall: Namespace-aware findall function.

        Returns:
            Episode or None if no enclosure found.
        """
        ns = self.NAMESPACES

        # Find enclosure link
        enclosure_url = ""
        episode_link = ""

        for link in findall(entry, "link"):
            rel = link.get("rel", "alternate")
            if rel == "enclosure":
                enclosure_url = link.get("href", "")
            elif rel == "alternate":
                episode_link = link.get("href", "")

        # YouTube-specific: check for media:group/media:content
        if not enclosure_url:
            media_group = entry.find("media:group", ns)
            if media_group is not None:
                media_content = media_group.find("media:content", ns)
                if media_content is not None:
                    enclosure_url = media_content.get("url", "")

            # Also try yt:videoId to construct YouTube watch URL
            if not enclosure_url:
                video_id = entry.find("yt:videoId", ns)
                if video_id is not None and video_id.text:
                    # Use the watch URL as the enclosure for YouTube videos
                    enclosure_url = f"https://www.youtube.com/watch?v={video_id.text}"
                    if not episode_link:
                        episode_link = enclosure_url

        if not enclosure_url:
            return None

        # Get content/summary for description
        content_el = find(entry, "content")
        summary_el = find(entry, "summary")
        description = _get_text(content_el) or _get_text(summary_el)

        # YouTube-specific: try media:group/media:description
        if not description:
            media_group = entry.find("media:group", ns)
            if media_group is not None:
                media_desc = media_group.find("media:description", ns)
                if media_desc is not None:
                    description = _get_text(media_desc)

        return Episode(
            feed_key=feed_key,
            title=_get_text(find(entry, "title"), "Untitled"),
            description=description,
            link=episode_link,
            enclosure=enclosure_url,
            pubdate=_parse_date(_get_text(find(entry, "published")))
            or _parse_date(_get_text(find(entry, "updated"))),
            copyright=_get_text(find(entry, "rights")) or None,
        )

    def _get_description(self, item: etree._Element) -> str:
        """Get description from RSS item, preferring content:encoded.

        Args:
            item: RSS item element.

        Returns:
            Description text.
        """
        # Try content:encoded first (often has full HTML content)
        content = item.find("content:encoded", self.NAMESPACES)
        if content is not None and content.text:
            return str(content.text).strip()

        # Fall back to description
        desc = item.find("description")
        if desc is not None and desc.text:
            return str(desc.text).strip()

        # Try itunes:summary
        summary = item.find("itunes:summary", self.NAMESPACES)
        if summary is not None and summary.text:
            return str(summary.text).strip()

        return ""
