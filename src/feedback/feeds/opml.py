"""OPML import/export for podcast subscriptions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from pathlib import Path

    from feedback.models import Feed


class OPMLError(Exception):
    """Base exception for OPML operations."""


class OPMLParseError(OPMLError):
    """Error parsing OPML file."""


class OPMLExportError(OPMLError):
    """Error exporting to OPML."""


@dataclass
class OPMLOutline:
    """Represents a single outline entry in OPML.

    Attributes:
        title: The feed title.
        xml_url: The RSS/Atom feed URL.
        html_url: The website URL (optional).
        description: Feed description (optional).
    """

    title: str
    xml_url: str
    html_url: str | None = None
    description: str | None = None


def parse_opml(content: str) -> list[OPMLOutline]:
    """Parse OPML content and extract feed outlines.

    Args:
        content: OPML XML content as string.

    Returns:
        List of OPMLOutline objects representing feeds.

    Raises:
        OPMLParseError: If the OPML content is invalid.
    """
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise OPMLParseError(f"Invalid XML: {e}") from e

    # OPML should have <opml> root with <body> containing <outline> elements
    body = root.find("body")
    if body is None:
        raise OPMLParseError("Missing <body> element in OPML")

    outlines: list[OPMLOutline] = []
    _extract_outlines(body, outlines)

    return outlines


def _extract_outlines(element: ET.Element, outlines: list[OPMLOutline]) -> None:
    """Recursively extract outline elements.

    OPML can have nested outlines (folders), so we traverse recursively.

    Args:
        element: Current XML element to process.
        outlines: List to append found outlines to.
    """
    for outline in element.findall("outline"):
        # Check if this is a feed (has xmlUrl attribute)
        xml_url = outline.get("xmlUrl") or outline.get("xmlurl")

        if xml_url:
            # This is a feed outline
            title = (
                outline.get("title")
                or outline.get("text")
                or xml_url.split("/")[-1]
            )
            html_url = outline.get("htmlUrl") or outline.get("htmlurl")
            description = outline.get("description")

            outlines.append(
                OPMLOutline(
                    title=title,
                    xml_url=xml_url,
                    html_url=html_url,
                    description=description,
                )
            )
        else:
            # This might be a folder, recurse into it
            _extract_outlines(outline, outlines)


def parse_opml_file(path: Path) -> list[OPMLOutline]:
    """Parse an OPML file and extract feed outlines.

    Args:
        path: Path to the OPML file.

    Returns:
        List of OPMLOutline objects representing feeds.

    Raises:
        OPMLParseError: If the file cannot be read or parsed.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        raise OPMLParseError(f"Cannot read file: {e}") from e

    return parse_opml(content)


def export_opml(
    feeds: list[Feed],
    title: str = "Podcast Subscriptions",
) -> str:
    """Export feeds to OPML format.

    Args:
        feeds: List of Feed objects to export.
        title: Title for the OPML document.

    Returns:
        OPML XML content as string.
    """
    # Create OPML structure
    opml = ET.Element("opml", version="2.0")

    # Head section
    head = ET.SubElement(opml, "head")
    title_elem = ET.SubElement(head, "title")
    title_elem.text = title

    date_created = ET.SubElement(head, "dateCreated")
    date_created.text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z").strip()

    # Body section with outlines
    body = ET.SubElement(opml, "body")

    for feed in feeds:
        attribs = {
            "type": "rss",
            "text": feed.title,
            "title": feed.title,
            "xmlUrl": feed.key,
        }

        if feed.link:
            attribs["htmlUrl"] = feed.link

        if feed.description:
            attribs["description"] = feed.description

        ET.SubElement(body, "outline", **attribs)

    # Generate XML string with declaration
    return _prettify_xml(opml)


def _prettify_xml(element: ET.Element, indent: str = "  ") -> str:
    """Convert ElementTree element to pretty-printed XML string.

    Args:
        element: Root element to convert.
        indent: Indentation string.

    Returns:
        Pretty-printed XML string with declaration.
    """
    # Add indentation
    _indent_element(element, level=0, indent=indent)

    # Convert to string
    xml_str = ET.tostring(element, encoding="unicode")

    # Add XML declaration
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'


def _indent_element(elem: ET.Element, level: int, indent: str) -> None:
    """Add indentation to XML element tree.

    Args:
        elem: Element to indent.
        level: Current nesting level.
        indent: Indentation string per level.
    """
    i = "\n" + level * indent

    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + indent
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            _indent_element(child, level + 1, indent)
        if not child.tail or not child.tail.strip():
            child.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def export_opml_file(
    feeds: list[Feed],
    path: Path,
    title: str = "Podcast Subscriptions",
) -> None:
    """Export feeds to an OPML file.

    Args:
        feeds: List of Feed objects to export.
        path: Path to write the OPML file.
        title: Title for the OPML document.

    Raises:
        OPMLExportError: If the file cannot be written.
    """
    try:
        content = export_opml(feeds, title)
        path.write_text(content, encoding="utf-8")
    except OSError as e:
        raise OPMLExportError(f"Cannot write file: {e}") from e


async def import_opml_feeds(
    path: Path,
    database: Database,  # noqa: F821
    fetcher: FeedFetcher,  # noqa: F821
    *,
    skip_duplicates: bool = True,
    on_progress: Callable[[str, int, int], None] | None = None,  # noqa: F821
) -> tuple[int, int, list[str]]:
    """Import feeds from an OPML file into the database.

    Args:
        path: Path to the OPML file.
        database: Database instance to save feeds to.
        fetcher: FeedFetcher instance to fetch feed data.
        skip_duplicates: If True, skip feeds that already exist.
        on_progress: Optional callback(title, current, total) for progress updates.

    Returns:
        Tuple of (imported_count, skipped_count, error_messages).

    Raises:
        OPMLParseError: If the OPML file cannot be parsed.
    """
    from feedback.feeds import FeedError

    outlines = parse_opml_file(path)

    imported = 0
    skipped = 0
    errors: list[str] = []

    # Get existing feed URLs for duplicate detection
    existing_feeds = await database.get_feeds()
    existing_urls = {feed.key for feed in existing_feeds}

    total = len(outlines)

    for i, outline in enumerate(outlines):
        if on_progress:
            on_progress(outline.title, i + 1, total)

        # Check for duplicates
        if skip_duplicates and outline.xml_url in existing_urls:
            skipped += 1
            continue

        try:
            feed, episodes = await fetcher.fetch(outline.xml_url)
            await database.upsert_feed(feed)
            await database.upsert_episodes(episodes)
            existing_urls.add(outline.xml_url)
            imported += 1
        except FeedError as e:
            errors.append(f"{outline.title}: {e}")
        except Exception as e:
            errors.append(f"{outline.title}: Unexpected error - {e}")

    return imported, skipped, errors
