"""Entry point for the feedback application."""

import asyncio
import sys


def main() -> int:
    """Run the feedback application."""
    from feedback.app import FeedbackApp

    app = FeedbackApp()
    asyncio.run(app.run_async())
    return 0


if __name__ == "__main__":
    sys.exit(main())
