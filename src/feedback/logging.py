"""Logging configuration for Feedback."""

from __future__ import annotations

import logging
import sys

from feedback.config import get_data_path

# Create module-level logger
logger = logging.getLogger("feedback")


def setup_logging(
    *,
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = False,
) -> None:
    """Configure logging for the application.

    Args:
        level: Logging level (default INFO).
        log_to_file: Whether to log to a file in the data directory.
        log_to_console: Whether to log to stderr (useful for debugging).
    """
    logger.setLevel(level)

    # Clear existing handlers
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if log_to_file:
        log_path = get_data_path() / "feedback.log"
        # Ensure parent directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Rotate log if it gets too big (>5MB)
        if log_path.exists() and log_path.stat().st_size > 5 * 1024 * 1024:
            old_log = log_path.with_suffix(".log.old")
            if old_log.exists():
                old_log.unlink()
            log_path.rename(old_log)

        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if log_to_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: Logger name (will be prefixed with 'feedback.').

    Returns:
        Logger instance.
    """
    return logging.getLogger(f"feedback.{name}")
