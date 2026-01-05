"""Podcast discovery using the Podcast Index API.

This module provides search functionality using the free and open
Podcast Index API (https://podcastindex.org/).

To use this feature, users must register at https://api.podcastindex.org
to obtain an API key and secret.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from collections.abc import Sequence


class DiscoveryError(Exception):
    """Base exception for discovery errors."""


class DiscoveryAuthError(DiscoveryError):
    """Authentication error (invalid or missing API credentials)."""


class DiscoverySearchError(DiscoveryError):
    """Error performing search."""


@dataclass(frozen=True)
class PodcastResult:
    """A podcast search result from the Podcast Index API."""

    id: int
    title: str
    url: str
    description: str
    author: str
    image_url: str
    categories: dict[str, str]
    episode_count: int
    language: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> PodcastResult:
        """Create a PodcastResult from API response data.

        Args:
            data: Feed data from the Podcast Index API.

        Returns:
            PodcastResult instance.
        """
        return cls(
            id=data.get("id", 0),
            title=data.get("title", ""),
            url=data.get("url", ""),
            description=data.get("description", ""),
            author=data.get("author", ""),
            image_url=data.get("image", ""),
            categories=data.get("categories", {}),
            episode_count=data.get("episodeCount", 0),
            language=data.get("language", ""),
        )


class PodcastIndexClient:
    """Client for the Podcast Index API.

    The Podcast Index is a free and open podcast directory.
    Register at https://api.podcastindex.org to get API credentials.
    """

    BASE_URL = "https://api.podcastindex.org/api/1.0"
    USER_AGENT = "Feedback/0.1.0"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the Podcast Index client.

        Args:
            api_key: Podcast Index API key.
            api_secret: Podcast Index API secret.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout

    def _get_auth_headers(self) -> dict[str, str]:
        """Generate authentication headers for the API.

        Returns:
            Dictionary of authentication headers.
        """
        epoch_time = int(time.time())
        auth_string = f"{self.api_key}{self.api_secret}{epoch_time}"
        auth_hash = hashlib.sha1(auth_string.encode()).hexdigest()

        return {
            "X-Auth-Date": str(epoch_time),
            "X-Auth-Key": self.api_key,
            "Authorization": auth_hash,
            "User-Agent": self.USER_AGENT,
        }

    async def search(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[PodcastResult]:
        """Search for podcasts by title or keyword.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return.

        Returns:
            List of matching podcasts.

        Raises:
            DiscoveryAuthError: If API credentials are invalid.
            DiscoverySearchError: If search fails.
        """
        if not self.api_key or not self.api_secret:
            raise DiscoveryAuthError(
                "Podcast Index API credentials not configured. "
                "Register at https://api.podcastindex.org to get an API key."
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/search/byterm",
                    params={"q": query, "max": max_results},
                    headers=self._get_auth_headers(),
                )

                if response.status_code == 401:
                    raise DiscoveryAuthError("Invalid API credentials")

                response.raise_for_status()
                data = response.json()

                if data.get("status") == "false":
                    return []

                feeds = data.get("feeds", [])
                return [PodcastResult.from_api(feed) for feed in feeds]

        except httpx.HTTPStatusError as e:
            raise DiscoverySearchError(f"HTTP error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise DiscoverySearchError(f"Request failed: {e}") from e

    async def search_by_title(
        self,
        title: str,
        max_results: int = 20,
    ) -> list[PodcastResult]:
        """Search for podcasts by exact title match.

        Args:
            title: Podcast title to search for.
            max_results: Maximum number of results to return.

        Returns:
            List of matching podcasts.

        Raises:
            DiscoveryAuthError: If API credentials are invalid.
            DiscoverySearchError: If search fails.
        """
        if not self.api_key or not self.api_secret:
            raise DiscoveryAuthError(
                "Podcast Index API credentials not configured. "
                "Register at https://api.podcastindex.org to get an API key."
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/search/bytitle",
                    params={"q": title, "max": max_results},
                    headers=self._get_auth_headers(),
                )

                if response.status_code == 401:
                    raise DiscoveryAuthError("Invalid API credentials")

                response.raise_for_status()
                data = response.json()

                if data.get("status") == "false":
                    return []

                feeds = data.get("feeds", [])
                return [PodcastResult.from_api(feed) for feed in feeds]

        except httpx.HTTPStatusError as e:
            raise DiscoverySearchError(f"HTTP error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise DiscoverySearchError(f"Request failed: {e}") from e

    async def trending(
        self,
        max_results: int = 20,
        language: str = "",
        categories: Sequence[str] | None = None,
    ) -> list[PodcastResult]:
        """Get trending podcasts.

        Args:
            max_results: Maximum number of results to return.
            language: Optional language filter (e.g., "en", "es").
            categories: Optional list of category names to filter by.

        Returns:
            List of trending podcasts.

        Raises:
            DiscoveryAuthError: If API credentials are invalid.
            DiscoverySearchError: If request fails.
        """
        if not self.api_key or not self.api_secret:
            raise DiscoveryAuthError(
                "Podcast Index API credentials not configured. "
                "Register at https://api.podcastindex.org to get an API key."
            )

        params: dict[str, str | int] = {"max": max_results}
        if language:
            params["lang"] = language
        if categories:
            params["cat"] = ",".join(categories)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/podcasts/trending",
                    params=params,
                    headers=self._get_auth_headers(),
                )

                if response.status_code == 401:
                    raise DiscoveryAuthError("Invalid API credentials")

                response.raise_for_status()
                data = response.json()

                if data.get("status") == "false":
                    return []

                feeds = data.get("feeds", [])
                return [PodcastResult.from_api(feed) for feed in feeds]

        except httpx.HTTPStatusError as e:
            raise DiscoverySearchError(f"HTTP error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise DiscoverySearchError(f"Request failed: {e}") from e

    async def get_by_feed_url(self, feed_url: str) -> PodcastResult | None:
        """Get podcast details by feed URL.

        Args:
            feed_url: The RSS feed URL.

        Returns:
            Podcast details or None if not found.

        Raises:
            DiscoveryAuthError: If API credentials are invalid.
            DiscoverySearchError: If request fails.
        """
        if not self.api_key or not self.api_secret:
            raise DiscoveryAuthError(
                "Podcast Index API credentials not configured. "
                "Register at https://api.podcastindex.org to get an API key."
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.BASE_URL}/podcasts/byfeedurl",
                    params={"url": feed_url},
                    headers=self._get_auth_headers(),
                )

                if response.status_code == 401:
                    raise DiscoveryAuthError("Invalid API credentials")

                response.raise_for_status()
                data = response.json()

                if data.get("status") == "false":
                    return None

                feed = data.get("feed")
                if not feed:
                    return None

                return PodcastResult.from_api(feed)

        except httpx.HTTPStatusError as e:
            raise DiscoverySearchError(f"HTTP error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise DiscoverySearchError(f"Request failed: {e}") from e
