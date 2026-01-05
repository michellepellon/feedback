"""Tests for OPML import/export functionality."""

from pathlib import Path

import pytest

from feedback.feeds.opml import (
    OPMLOutline,
    OPMLParseError,
    export_opml,
    parse_opml,
    parse_opml_file,
)
from feedback.models import Feed


class TestParseOPML:
    """Tests for OPML parsing."""

    def test_parse_simple_opml(self) -> None:
        """Test parsing a simple OPML file."""
        content = """<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
            <head>
                <title>My Podcasts</title>
            </head>
            <body>
                <outline type="rss" text="Podcast One" title="Podcast One"
                         xmlUrl="https://example.com/feed1.xml"
                         htmlUrl="https://example.com"/>
                <outline type="rss" text="Podcast Two"
                         xmlUrl="https://example.com/feed2.xml"/>
            </body>
        </opml>
        """
        outlines = parse_opml(content)

        assert len(outlines) == 2
        assert outlines[0].title == "Podcast One"
        assert outlines[0].xml_url == "https://example.com/feed1.xml"
        assert outlines[0].html_url == "https://example.com"
        assert outlines[1].title == "Podcast Two"
        assert outlines[1].xml_url == "https://example.com/feed2.xml"
        assert outlines[1].html_url is None

    def test_parse_nested_opml(self) -> None:
        """Test parsing OPML with nested folders."""
        content = """<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
            <head><title>Podcasts</title></head>
            <body>
                <outline text="Tech">
                    <outline type="rss" text="Tech Podcast"
                             xmlUrl="https://example.com/tech.xml"/>
                </outline>
                <outline text="News">
                    <outline type="rss" text="News Daily"
                             xmlUrl="https://example.com/news.xml"/>
                    <outline type="rss" text="World Report"
                             xmlUrl="https://example.com/world.xml"/>
                </outline>
                <outline type="rss" text="Uncategorized"
                         xmlUrl="https://example.com/other.xml"/>
            </body>
        </opml>
        """
        outlines = parse_opml(content)

        assert len(outlines) == 4
        urls = {o.xml_url for o in outlines}
        assert "https://example.com/tech.xml" in urls
        assert "https://example.com/news.xml" in urls
        assert "https://example.com/world.xml" in urls
        assert "https://example.com/other.xml" in urls

    def test_parse_with_description(self) -> None:
        """Test parsing OPML with description attribute."""
        content = """<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
            <head><title>Podcasts</title></head>
            <body>
                <outline type="rss" text="My Podcast"
                         xmlUrl="https://example.com/feed.xml"
                         description="A great podcast about stuff"/>
            </body>
        </opml>
        """
        outlines = parse_opml(content)

        assert len(outlines) == 1
        assert outlines[0].description == "A great podcast about stuff"

    def test_parse_lowercase_attributes(self) -> None:
        """Test parsing OPML with lowercase attribute names."""
        content = """<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
            <head><title>Podcasts</title></head>
            <body>
                <outline type="rss" text="Podcast"
                         xmlurl="https://example.com/feed.xml"
                         htmlurl="https://example.com"/>
            </body>
        </opml>
        """
        outlines = parse_opml(content)

        assert len(outlines) == 1
        assert outlines[0].xml_url == "https://example.com/feed.xml"
        assert outlines[0].html_url == "https://example.com"

    def test_parse_uses_text_when_no_title(self) -> None:
        """Test that text attribute is used when title is missing."""
        content = """<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
            <head><title>Podcasts</title></head>
            <body>
                <outline type="rss" text="Text Title"
                         xmlUrl="https://example.com/feed.xml"/>
            </body>
        </opml>
        """
        outlines = parse_opml(content)

        assert outlines[0].title == "Text Title"

    def test_parse_invalid_xml(self) -> None:
        """Test that invalid XML raises OPMLParseError."""
        content = "not valid xml <><>"

        with pytest.raises(OPMLParseError, match="Invalid XML"):
            parse_opml(content)

    def test_parse_missing_body(self) -> None:
        """Test that missing body element raises OPMLParseError."""
        content = """<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
            <head><title>Podcasts</title></head>
        </opml>
        """

        with pytest.raises(OPMLParseError, match="Missing <body>"):
            parse_opml(content)

    def test_parse_empty_opml(self) -> None:
        """Test parsing OPML with no feeds."""
        content = """<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
            <head><title>Empty</title></head>
            <body></body>
        </opml>
        """
        outlines = parse_opml(content)

        assert len(outlines) == 0

    def test_parse_skips_non_feed_outlines(self) -> None:
        """Test that outlines without xmlUrl are skipped (unless folders)."""
        content = """<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
            <head><title>Mixed</title></head>
            <body>
                <outline text="Just a note"/>
                <outline type="rss" text="Real Feed"
                         xmlUrl="https://example.com/feed.xml"/>
            </body>
        </opml>
        """
        outlines = parse_opml(content)

        assert len(outlines) == 1
        assert outlines[0].title == "Real Feed"


class TestParseOPMLFile:
    """Tests for parsing OPML from files."""

    def test_parse_file(self, tmp_path: Path) -> None:
        """Test parsing OPML from a file."""
        opml_file = tmp_path / "podcasts.opml"
        opml_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
            <head><title>Podcasts</title></head>
            <body>
                <outline type="rss" text="Test" xmlUrl="https://example.com/feed.xml"/>
            </body>
        </opml>
        """)

        outlines = parse_opml_file(opml_file)

        assert len(outlines) == 1
        assert outlines[0].xml_url == "https://example.com/feed.xml"

    def test_parse_nonexistent_file(self, tmp_path: Path) -> None:
        """Test that nonexistent file raises OPMLParseError."""
        with pytest.raises(OPMLParseError, match="Cannot read file"):
            parse_opml_file(tmp_path / "nonexistent.opml")


class TestExportOPML:
    """Tests for OPML export."""

    def test_export_single_feed(self) -> None:
        """Test exporting a single feed."""
        feeds = [
            Feed(
                key="https://example.com/feed.xml",
                title="Test Podcast",
                description="A test podcast",
                link="https://example.com",
            )
        ]

        opml = export_opml(feeds)

        assert '<?xml version="1.0" encoding="UTF-8"?>' in opml
        assert '<opml version="2.0">' in opml
        assert 'title="Test Podcast"' in opml
        assert 'xmlUrl="https://example.com/feed.xml"' in opml
        assert 'htmlUrl="https://example.com"' in opml
        assert 'description="A test podcast"' in opml

    def test_export_multiple_feeds(self) -> None:
        """Test exporting multiple feeds."""
        feeds = [
            Feed(key="https://example.com/feed1.xml", title="Podcast 1"),
            Feed(key="https://example.com/feed2.xml", title="Podcast 2"),
            Feed(key="https://example.com/feed3.xml", title="Podcast 3"),
        ]

        opml = export_opml(feeds)

        assert opml.count("<outline") == 3
        assert "Podcast 1" in opml
        assert "Podcast 2" in opml
        assert "Podcast 3" in opml

    def test_export_with_custom_title(self) -> None:
        """Test exporting with custom document title."""
        feeds = [Feed(key="https://example.com/feed.xml", title="Test")]

        opml = export_opml(feeds, title="My Custom Title")

        assert "<title>My Custom Title</title>" in opml

    def test_export_empty_list(self) -> None:
        """Test exporting empty feed list."""
        opml = export_opml([])

        assert "<opml" in opml
        assert "<body" in opml  # May be <body> or <body />
        assert "<outline" not in opml

    def test_export_feed_without_optional_fields(self) -> None:
        """Test exporting feed without description or link."""
        feeds = [
            Feed(key="https://example.com/feed.xml", title="Minimal")
        ]

        opml = export_opml(feeds)

        assert 'title="Minimal"' in opml
        assert 'xmlUrl="https://example.com/feed.xml"' in opml
        # Should not have htmlUrl or description if not set
        assert "htmlUrl" not in opml or 'htmlUrl=""' not in opml

    def test_export_roundtrip(self) -> None:
        """Test that exported OPML can be parsed back."""
        original_feeds = [
            Feed(
                key="https://example.com/feed1.xml",
                title="Podcast One",
                description="First podcast",
                link="https://example.com/1",
            ),
            Feed(
                key="https://example.com/feed2.xml",
                title="Podcast Two",
            ),
        ]

        # Export
        opml = export_opml(original_feeds)

        # Parse back
        outlines = parse_opml(opml)

        assert len(outlines) == 2
        assert outlines[0].xml_url == "https://example.com/feed1.xml"
        assert outlines[0].title == "Podcast One"
        assert outlines[0].description == "First podcast"
        assert outlines[1].xml_url == "https://example.com/feed2.xml"
        assert outlines[1].title == "Podcast Two"


class TestExportOPMLFile:
    """Tests for exporting OPML to files."""

    def test_export_file(self, tmp_path: Path) -> None:
        """Test exporting OPML to a file."""
        from feedback.feeds.opml import export_opml_file

        feeds = [
            Feed(key="https://example.com/feed.xml", title="Test Podcast")
        ]
        opml_file = tmp_path / "export.opml"

        export_opml_file(feeds, opml_file)

        assert opml_file.exists()
        content = opml_file.read_text()
        assert "Test Podcast" in content
        assert "https://example.com/feed.xml" in content

    def test_export_file_custom_title(self, tmp_path: Path) -> None:
        """Test exporting with custom title."""
        from feedback.feeds.opml import export_opml_file

        feeds = [Feed(key="https://example.com/feed.xml", title="Test")]
        opml_file = tmp_path / "export.opml"

        export_opml_file(feeds, opml_file, title="My Exports")

        content = opml_file.read_text()
        assert "<title>My Exports</title>" in content

    def test_export_file_error(self, tmp_path: Path) -> None:
        """Test that export to invalid path raises OPMLExportError."""
        from feedback.feeds.opml import OPMLExportError, export_opml_file

        feeds = [Feed(key="https://example.com/feed.xml", title="Test")]
        # Try to write to a directory that doesn't exist
        invalid_path = tmp_path / "nonexistent" / "subdir" / "export.opml"

        with pytest.raises(OPMLExportError, match="Cannot write file"):
            export_opml_file(feeds, invalid_path)


class TestOPMLOutline:
    """Tests for OPMLOutline dataclass."""

    def test_outline_creation(self) -> None:
        """Test creating an OPMLOutline."""
        outline = OPMLOutline(
            title="My Podcast",
            xml_url="https://example.com/feed.xml",
            html_url="https://example.com",
            description="A great show",
        )

        assert outline.title == "My Podcast"
        assert outline.xml_url == "https://example.com/feed.xml"
        assert outline.html_url == "https://example.com"
        assert outline.description == "A great show"

    def test_outline_defaults(self) -> None:
        """Test OPMLOutline default values."""
        outline = OPMLOutline(
            title="Minimal",
            xml_url="https://example.com/feed.xml",
        )

        assert outline.html_url is None
        assert outline.description is None
