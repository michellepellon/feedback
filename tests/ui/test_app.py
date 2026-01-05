"""Tests for the main FeedbackApp."""

from __future__ import annotations

import pytest
from textual.widgets import Footer, Header

from feedback.app import FeedbackApp
from feedback.screens.downloads import DownloadsScreen
from feedback.screens.primary import PrimaryScreen
from feedback.screens.queue import QueueScreen
from feedback.widgets.player_bar import PlayerBar


class TestFeedbackApp:
    """Tests for FeedbackApp."""

    @pytest.fixture
    def app(self) -> FeedbackApp:
        """Create a FeedbackApp instance for testing."""
        return FeedbackApp()

    async def test_app_title(self, app: FeedbackApp) -> None:
        """Test that app has correct title."""
        assert app.TITLE == "Feedback"

    async def test_app_has_screens_defined(self, app: FeedbackApp) -> None:
        """Test that app has screens defined."""
        assert "primary" in app.SCREENS
        assert "queue" in app.SCREENS
        assert "downloads" in app.SCREENS

    async def test_app_initial_screen(self, app: FeedbackApp) -> None:
        """Test that primary screen is pushed on mount."""
        async with app.run_test() as pilot:
            assert isinstance(pilot.app.screen, PrimaryScreen)

    async def test_switch_to_queue_screen(self, app: FeedbackApp) -> None:
        """Test switching to queue screen with key binding."""
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert isinstance(pilot.app.screen, QueueScreen)

    async def test_switch_to_downloads_screen(self, app: FeedbackApp) -> None:
        """Test switching to downloads screen with key binding."""
        async with app.run_test() as pilot:
            await pilot.press("3")
            assert isinstance(pilot.app.screen, DownloadsScreen)

    async def test_switch_back_to_primary_screen(self, app: FeedbackApp) -> None:
        """Test switching back to primary screen."""
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert isinstance(pilot.app.screen, QueueScreen)
            await pilot.press("1")
            assert isinstance(pilot.app.screen, PrimaryScreen)

    async def test_help_toggle_shows_notification(self, app: FeedbackApp) -> None:
        """Test that help toggle shows notification."""
        async with app.run_test() as pilot:
            await pilot.press("?")

    async def test_quit_binding(self, app: FeedbackApp) -> None:
        """Test that q quits the app."""
        async with app.run_test() as pilot:
            await pilot.press("q")
            assert not pilot.app._running


class TestScreenComponents:
    """Tests for screen components."""

    @pytest.fixture
    def app(self) -> FeedbackApp:
        """Create a FeedbackApp instance."""
        return FeedbackApp()

    async def test_primary_screen_has_header(self, app: FeedbackApp) -> None:
        """Test that primary screen has a Header."""
        async with app.run_test() as pilot:
            assert pilot.app.screen.query_one(Header)

    async def test_primary_screen_has_footer(self, app: FeedbackApp) -> None:
        """Test that primary screen has a Footer."""
        async with app.run_test() as pilot:
            assert pilot.app.screen.query_one(Footer)

    async def test_primary_screen_has_player_bar(self, app: FeedbackApp) -> None:
        """Test that primary screen has a PlayerBar."""
        async with app.run_test() as pilot:
            assert pilot.app.screen.query_one(PlayerBar)

    async def test_queue_screen_has_player_bar(self, app: FeedbackApp) -> None:
        """Test that queue screen has a PlayerBar."""
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert pilot.app.screen.query_one(PlayerBar)

    async def test_downloads_screen_has_player_bar(self, app: FeedbackApp) -> None:
        """Test that downloads screen has a PlayerBar."""
        async with app.run_test() as pilot:
            await pilot.press("3")
            assert pilot.app.screen.query_one(PlayerBar)
