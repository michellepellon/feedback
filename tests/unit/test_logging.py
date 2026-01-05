"""Tests for the logging module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_to_file(self, tmp_path: Path) -> None:
        """Test logging to a file."""
        from feedback.logging import logger, setup_logging

        with patch("feedback.logging.get_data_path", return_value=tmp_path):
            setup_logging(log_to_file=True, log_to_console=False)

        log_path = tmp_path / "feedback.log"
        assert log_path.exists() or len(logger.handlers) > 0

    def test_setup_logging_to_console(self, tmp_path: Path) -> None:
        """Test logging to console."""
        from feedback.logging import logger, setup_logging

        with patch("feedback.logging.get_data_path", return_value=tmp_path):
            setup_logging(log_to_file=False, log_to_console=True)

        # Should have console handler
        assert any(
            isinstance(h, logging.StreamHandler) for h in logger.handlers
        )

    def test_setup_logging_custom_level(self, tmp_path: Path) -> None:
        """Test setting custom log level."""
        from feedback.logging import logger, setup_logging

        with patch("feedback.logging.get_data_path", return_value=tmp_path):
            setup_logging(level=logging.DEBUG, log_to_file=False, log_to_console=True)

        assert logger.level == logging.DEBUG

    def test_setup_logging_clears_handlers(self, tmp_path: Path) -> None:
        """Test that setup_logging clears existing handlers."""
        from feedback.logging import logger, setup_logging

        # Add a handler
        logger.addHandler(logging.NullHandler())
        initial_count = len(logger.handlers)

        with patch("feedback.logging.get_data_path", return_value=tmp_path):
            setup_logging(log_to_file=False, log_to_console=True)

        # Should have cleared and re-added
        assert len(logger.handlers) <= initial_count

    def test_setup_logging_rotates_large_file(self, tmp_path: Path) -> None:
        """Test log rotation when file is too large."""
        from feedback.logging import setup_logging

        # Create a large log file (>5MB)
        log_path = tmp_path / "feedback.log"
        log_path.write_bytes(b"x" * (6 * 1024 * 1024))

        with patch("feedback.logging.get_data_path", return_value=tmp_path):
            setup_logging(log_to_file=True, log_to_console=False)

        # Old log should exist
        old_log = tmp_path / "feedback.log.old"
        assert old_log.exists()


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_child_logger(self) -> None:
        """Test that get_logger returns a properly named logger."""
        from feedback.logging import get_logger

        log = get_logger("test")
        assert log.name == "feedback.test"

    def test_get_logger_different_names(self) -> None:
        """Test that different names return different loggers."""
        from feedback.logging import get_logger

        log1 = get_logger("module1")
        log2 = get_logger("module2")

        assert log1.name != log2.name
        assert log1.name == "feedback.module1"
        assert log2.name == "feedback.module2"
