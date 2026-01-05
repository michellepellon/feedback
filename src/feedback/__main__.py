"""Entry point for the feedback application."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def main() -> int:
    """Run the feedback application or CLI commands."""
    parser = argparse.ArgumentParser(
        prog="feedback",
        description="A modern TUI podcast client for the terminal",
    )
    parser.add_argument(
        "--version", "-v", action="store_true", help="Show version and exit"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Import command
    import_parser = subparsers.add_parser(
        "import", help="Import feeds from an OPML file"
    )
    import_parser.add_argument(
        "file", type=Path, help="Path to the OPML file to import"
    )
    import_parser.add_argument(
        "--no-skip-duplicates",
        action="store_true",
        help="Import feeds even if they already exist",
    )

    # Export command
    export_parser = subparsers.add_parser(
        "export", help="Export feeds to an OPML file"
    )
    export_parser.add_argument(
        "file", type=Path, help="Path to write the OPML file"
    )
    export_parser.add_argument(
        "--title", "-t", default="Feedback Subscriptions", help="OPML document title"
    )

    args = parser.parse_args()

    if args.version:
        from feedback import __version__

        print(f"feedback {__version__}")
        return 0

    if args.command == "import":
        return asyncio.run(cmd_import(args.file, skip_duplicates=not args.no_skip_duplicates))
    elif args.command == "export":
        return asyncio.run(cmd_export(args.file, title=args.title))
    else:
        # No command specified, run the TUI app
        return run_app()


def run_app() -> int:
    """Run the TUI application."""
    from feedback.app import FeedbackApp

    app = FeedbackApp()
    asyncio.run(app.run_async())
    return 0


async def cmd_import(file: Path, *, skip_duplicates: bool = True) -> int:
    """Import feeds from an OPML file.

    Args:
        file: Path to the OPML file.
        skip_duplicates: Whether to skip feeds that already exist.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    from feedback.config import get_config, get_data_path
    from feedback.database import Database
    from feedback.feeds import FeedFetcher
    from feedback.feeds.opml import OPMLParseError, import_opml_feeds

    if not file.exists():
        print(f"Error: File not found: {file}", file=sys.stderr)
        return 1

    print(f"Importing feeds from {file}...")

    # Initialize database
    config = get_config()
    db_path = get_data_path() / "feedback.db"
    database = Database(db_path)
    await database.connect()

    try:
        # Create fetcher
        fetcher = FeedFetcher(
            timeout=config.network.timeout,
            max_episodes=config.network.max_episodes,
        )

        # Progress callback
        def on_progress(title: str, current: int, total: int) -> None:
            print(f"  [{current}/{total}] {title}")

        # Import feeds
        imported, skipped, errors = await import_opml_feeds(
            file,
            database,
            fetcher,
            skip_duplicates=skip_duplicates,
            on_progress=on_progress,
        )

        # Print summary
        print()
        print("Import complete:")
        print(f"  Imported: {imported}")
        print(f"  Skipped (duplicates): {skipped}")
        print(f"  Errors: {len(errors)}")

        if errors:
            print()
            print("Errors:")
            for error in errors:
                print(f"  - {error}")

        return 0 if not errors else 1

    except OPMLParseError as e:
        print(f"Error parsing OPML: {e}", file=sys.stderr)
        return 1
    finally:
        await database.close()


async def cmd_export(file: Path, *, title: str = "Feedback Subscriptions") -> int:
    """Export feeds to an OPML file.

    Args:
        file: Path to write the OPML file.
        title: Title for the OPML document.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    from feedback.config import get_data_path
    from feedback.database import Database
    from feedback.feeds.opml import OPMLExportError, export_opml_file

    # Initialize database
    db_path = get_data_path() / "feedback.db"

    if not db_path.exists():
        print("Error: No database found. Add some feeds first.", file=sys.stderr)
        return 1

    database = Database(db_path)
    await database.connect()

    try:
        # Get all feeds
        feeds = await database.get_feeds()

        if not feeds:
            print("No feeds to export.", file=sys.stderr)
            return 1

        # Export to file
        export_opml_file(feeds, file, title=title)

        print(f"Exported {len(feeds)} feeds to {file}")
        return 0

    except OPMLExportError as e:
        print(f"Error exporting OPML: {e}", file=sys.stderr)
        return 1
    finally:
        await database.close()


if __name__ == "__main__":
    sys.exit(main())
