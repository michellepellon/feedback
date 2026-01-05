"""Help screen with keybinding reference."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

from feedback import __version__

if TYPE_CHECKING:
    from textual.app import ComposeResult


HELP_TEXT = f"""[bold]Feedback v{__version__}[/bold]
A modern TUI podcast client for the terminal

[bold underline]Navigation[/bold underline]
  [bold]j / k[/bold]           Move down / up
  [bold]Enter[/bold]           Select / Play
  [bold]Tab[/bold]             Next pane
  [bold]Shift+Tab[/bold]       Previous pane
  [bold]1 / 2 / 3 / 4[/bold]   Switch to Feeds / Queue / Downloads / History
  [bold]Ctrl+,[/bold]          Open settings
  [bold]q[/bold]               Quit

[bold underline]Feed Management[/bold underline]
  [bold]a[/bold]               Add feed (enter URL)
  [bold]d[/bold]               Delete selected feed
  [bold]r[/bold]               Refresh all feeds
  [bold]i[/bold]               Show feed info
  [bold]S[/bold]               Search podcasts (Podcast Index)

[bold underline]Episode Management[/bold underline]
  [bold]m[/bold]               Mark episode as played
  [bold]u[/bold]               Mark episode as unplayed
  [bold]M[/bold]               Mark ALL episodes as played
  [bold]Q[/bold]               Add episode to queue
  [bold]D[/bold]               Download episode
  [bold]F[/bold]               Cycle filter (All/Unplayed/Downloaded/In Progress)
  [bold]O[/bold]               Cycle sort (Newest/Oldest/Title)

[bold underline]Playback Controls[/bold underline]
  [bold]p / Space[/bold]       Play / Pause
  [bold]f[/bold]               Seek forward 30 seconds
  [bold]b[/bold]               Seek backward 10 seconds
  [bold]+ / -[/bold]           Volume up / down
  [bold]] / [[/bold]           Speed up / down
  [bold]t[/bold]               Cycle sleep timer (Off/15/30/45/60 min/End)

[bold underline]Queue Screen[/bold underline]
  [bold]Enter[/bold]           Play selected item
  [bold]d[/bold]               Remove from queue
  [bold]c[/bold]               Clear queue
  [bold]u / n[/bold]           Move item up / down

[bold underline]Downloads Screen[/bold underline]
  [bold]Enter[/bold]           Play completed download
  [bold]c[/bold]               Cancel selected download
  [bold]C[/bold]               Cancel all downloads
  [bold]d[/bold]               Delete downloaded file
  [bold]x[/bold]               Clear completed downloads

[bold underline]History Screen[/bold underline]
  [bold]Enter[/bold]           Play episode from history
  [bold]c[/bold]               Clear all history
  [bold]Escape[/bold]          Go back

[bold underline]CLI Commands[/bold underline]
  [dim]feedback[/dim]                    Launch the TUI
  [dim]feedback import <file>[/dim]     Import feeds from OPML
  [dim]feedback export <file>[/dim]     Export feeds to OPML
  [dim]feedback --version[/dim]         Show version

[dim]Press Escape or ? to close this help[/dim]
"""


class HelpScreen(ModalScreen[None]):
    """Modal screen displaying help and keybindings."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "close", "Close"),
        Binding("?", "close", "Close"),
        Binding("q", "close", "Close"),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }

    HelpScreen > Vertical {
        width: 70;
        max-width: 90%;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    HelpScreen > Vertical > VerticalScroll {
        height: auto;
        max-height: 100%;
    }

    HelpScreen Static {
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the help screen."""
        with Vertical(), VerticalScroll():
            yield Static(HELP_TEXT)

    def action_close(self) -> None:
        """Close the help screen."""
        self.dismiss()
