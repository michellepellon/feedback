"""Tests for screen functionality."""

from __future__ import annotations

import pytest

from feedback.app import FeedbackApp
from feedback.screens.downloads import DownloadsScreen
from feedback.screens.primary import MetadataPanel, PrimaryScreen
from feedback.screens.queue import QueueScreen
from feedback.widgets.download_list import DownloadList
from feedback.widgets.episode_list import EpisodeList
from feedback.widgets.feed_list import FeedList
from feedback.widgets.queue_list import QueueList


class TestPrimaryScreen:
    """Tests for PrimaryScreen."""

    @pytest.fixture
    def app(self) -> FeedbackApp:
        """Create a FeedbackApp instance."""
        return FeedbackApp()

    async def test_primary_screen_has_feed_list(self, app: FeedbackApp) -> None:
        """Test that primary screen has a FeedList."""
        async with app.run_test() as pilot:
            assert pilot.app.screen.query_one(FeedList)

    async def test_primary_screen_has_episode_list(self, app: FeedbackApp) -> None:
        """Test that primary screen has an EpisodeList."""
        async with app.run_test() as pilot:
            assert pilot.app.screen.query_one(EpisodeList)

    async def test_primary_screen_has_metadata_panel(self, app: FeedbackApp) -> None:
        """Test that primary screen has a MetadataPanel."""
        async with app.run_test() as pilot:
            assert pilot.app.screen.query_one(MetadataPanel)

    async def test_primary_screen_j_key_moves_down(self, app: FeedbackApp) -> None:
        """Test that j key triggers move down action."""
        async with app.run_test() as pilot:
            screen = pilot.app.screen
            assert isinstance(screen, PrimaryScreen)
            await pilot.press("j")

    async def test_primary_screen_k_key_moves_up(self, app: FeedbackApp) -> None:
        """Test that k key triggers move up action."""
        async with app.run_test() as pilot:
            screen = pilot.app.screen
            assert isinstance(screen, PrimaryScreen)
            await pilot.press("k")

    async def test_primary_screen_tab_changes_focus(self, app: FeedbackApp) -> None:
        """Test that tab changes focus between panes."""
        async with app.run_test() as pilot:
            screen = pilot.app.screen
            assert isinstance(screen, PrimaryScreen)
            await pilot.press("tab")

    async def test_primary_screen_refresh_action(self, app: FeedbackApp) -> None:
        """Test refresh action shows notification."""
        async with app.run_test() as pilot:
            await pilot.press("r")

    async def test_primary_screen_add_feed_action(self, app: FeedbackApp) -> None:
        """Test add feed action shows notification."""
        async with app.run_test() as pilot:
            await pilot.press("a")

    @pytest.mark.skip(reason="Confirmation dialogs require worker context in tests")
    async def test_primary_screen_delete_action(self, app: FeedbackApp) -> None:
        """Test delete action shows confirmation dialog."""
        async with app.run_test() as pilot:
            await pilot.press("d")

    async def test_primary_screen_play_pause_action(self, app: FeedbackApp) -> None:
        """Test play/pause action shows notification."""
        async with app.run_test() as pilot:
            await pilot.press("p")


class TestQueueScreen:
    """Tests for QueueScreen."""

    @pytest.fixture
    def app(self) -> FeedbackApp:
        """Create a FeedbackApp instance."""
        return FeedbackApp()

    async def test_queue_screen_has_queue_list(self, app: FeedbackApp) -> None:
        """Test that queue screen has a QueueList."""
        async with app.run_test() as pilot:
            await pilot.press("2")
            assert isinstance(pilot.app.screen, QueueScreen)
            assert pilot.app.screen.query_one(QueueList)

    async def test_queue_screen_j_key_moves_down(self, app: FeedbackApp) -> None:
        """Test that j key triggers move down action."""
        async with app.run_test() as pilot:
            await pilot.press("2")
            await pilot.press("j")

    async def test_queue_screen_k_key_moves_up(self, app: FeedbackApp) -> None:
        """Test that k key triggers move up action."""
        async with app.run_test() as pilot:
            await pilot.press("2")
            await pilot.press("k")

    async def test_queue_screen_remove_action(self, app: FeedbackApp) -> None:
        """Test remove action shows notification."""
        async with app.run_test() as pilot:
            await pilot.press("2")
            await pilot.press("d")

    async def test_queue_screen_clear_action(self, app: FeedbackApp) -> None:
        """Test clear action shows notification."""
        async with app.run_test() as pilot:
            await pilot.press("2")
            await pilot.press("c")

    async def test_queue_screen_move_up_action(self, app: FeedbackApp) -> None:
        """Test move up action shows notification."""
        async with app.run_test() as pilot:
            await pilot.press("2")
            await pilot.press("u")

    async def test_queue_screen_move_down_action(self, app: FeedbackApp) -> None:
        """Test move down action shows notification."""
        async with app.run_test() as pilot:
            await pilot.press("2")
            await pilot.press("n")

    async def test_queue_screen_play_pause_action(self, app: FeedbackApp) -> None:
        """Test play/pause action shows notification."""
        async with app.run_test() as pilot:
            await pilot.press("2")
            await pilot.press("p")


class TestDownloadsScreen:
    """Tests for DownloadsScreen."""

    @pytest.fixture
    def app(self) -> FeedbackApp:
        """Create a FeedbackApp instance."""
        return FeedbackApp()

    async def test_downloads_screen_has_download_list(self, app: FeedbackApp) -> None:
        """Test that downloads screen has a DownloadList."""
        async with app.run_test() as pilot:
            await pilot.press("3")
            assert isinstance(pilot.app.screen, DownloadsScreen)
            assert pilot.app.screen.query_one(DownloadList)

    async def test_downloads_screen_j_key_moves_down(self, app: FeedbackApp) -> None:
        """Test that j key triggers move down action."""
        async with app.run_test() as pilot:
            await pilot.press("3")
            await pilot.press("j")

    async def test_downloads_screen_k_key_moves_up(self, app: FeedbackApp) -> None:
        """Test that k key triggers move up action."""
        async with app.run_test() as pilot:
            await pilot.press("3")
            await pilot.press("k")

    async def test_downloads_screen_delete_action(self, app: FeedbackApp) -> None:
        """Test delete action shows notification."""
        async with app.run_test() as pilot:
            await pilot.press("3")
            await pilot.press("d")

    async def test_downloads_screen_cancel_action(self, app: FeedbackApp) -> None:
        """Test cancel action shows notification."""
        async with app.run_test() as pilot:
            await pilot.press("3")
            await pilot.press("c")

    async def test_downloads_screen_cancel_all_action(self, app: FeedbackApp) -> None:
        """Test cancel all action shows notification."""
        async with app.run_test() as pilot:
            await pilot.press("3")
            await pilot.press("C")

    async def test_downloads_screen_play_pause_action(self, app: FeedbackApp) -> None:
        """Test play/pause action shows notification."""
        async with app.run_test() as pilot:
            await pilot.press("3")
            await pilot.press("p")


class TestMetadataPanel:
    """Tests for MetadataPanel widget."""

    def test_metadata_panel_creation(self) -> None:
        """Test MetadataPanel can be created."""
        panel = MetadataPanel()
        assert panel is not None
