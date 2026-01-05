# Feedback Roadmap

A comprehensive plan for improving the Feedback podcast client.

## Current State Assessment

**Version**: 0.1.0 (Alpha)

### What's Solid
- Database layer with async SQLite, migrations, transactions
- Feed parsing (RSS 2.0, Atom, YouTube channels)
- Podcast Index API integration for discovery
- VLC and MPV player implementations with full controls
- Download manager with concurrent downloads and progress tracking
- Configuration system (TOML-based, comprehensive options)
- Primary screen with three-pane layout
- 98% test coverage (314 tests)

### What Needs Work
- Queue screen actions are stubbed (display only)
- Downloads screen actions are stubbed (display only)
- Playback progress not auto-saved to database
- No OPML import/export
- Limited help system
- No settings UI (config file only)

---

## Phase 1: Complete Core Functionality

**Goal**: Make all screens fully functional

### 1.1 Queue Screen Implementation
**Priority**: Critical

The queue screen currently displays items but all actions show "coming soon" notifications.

**Tasks**:
- [ ] Wire `action_play()` to start playback from queue
- [ ] Implement `action_remove()` with database persistence
- [ ] Implement `action_clear()` to empty queue
- [ ] Implement `action_move_item_up()` and `action_move_item_down()`
- [ ] Add visual feedback when queue changes
- [ ] Auto-advance to next item when episode finishes
- [ ] Show "Now Playing" indicator for current item

**Files**: `src/feedback/screens/queue.py`, `src/feedback/widgets/queue_list.py`

### 1.2 Downloads Screen Implementation
**Priority**: Critical

The downloads screen displays but doesn't connect to the DownloadQueue.

**Tasks**:
- [ ] Connect DownloadQueue to DownloadList widget
- [ ] Implement `action_cancel()` to cancel selected download
- [ ] Implement `action_cancel_all()` to cancel all downloads
- [ ] Implement `action_delete()` to remove downloaded file
- [ ] Wire progress callbacks to update UI in real-time
- [ ] Show download speed and ETA
- [ ] Add "Download Episode" action to primary screen (from episode list)

**Files**: `src/feedback/screens/downloads.py`, `src/feedback/widgets/download_list.py`

### 1.3 Playback Progress Persistence
**Priority**: High

Player tracks position but doesn't save to database.

**Tasks**:
- [ ] Add periodic progress save (every 30 seconds during playback)
- [ ] Save progress on pause/stop
- [ ] Mark episode as played when 90%+ complete
- [ ] Handle app crash/force quit (save on signal)
- [ ] Show resume position in episode list

**Files**: `src/feedback/screens/primary.py`, `src/feedback/app.py`

### 1.4 Primary Screen Enhancements
**Priority**: High

Missing actions that users expect.

**Tasks**:
- [ ] Add "Mark as Played" action (`m` key)
- [ ] Add "Mark as Unplayed" action (`u` key)
- [ ] Add "Add to Queue" action (`space` key)
- [ ] Add "Download Episode" action (`D` key)
- [ ] Implement seek forward/backward (`f`/`b` keys)
- [ ] Add volume control (`+`/`-` keys)
- [ ] Add speed control (`[`/`]` keys)

**Files**: `src/feedback/screens/primary.py`

---

## Phase 2: Essential Features

**Goal**: Feature parity with basic podcast clients

### 2.1 OPML Import/Export
**Priority**: High

Essential for migrating from other clients.

**Tasks**:
- [ ] Create `src/feedback/feeds/opml.py` module
- [ ] Implement OPML 2.0 parser
- [ ] Implement OPML exporter
- [ ] Add `feedback import <file.opml>` CLI command
- [ ] Add `feedback export <file.opml>` CLI command
- [ ] Add import/export actions to UI (via modal or menu)
- [ ] Handle duplicate feeds on import

**New Files**: `src/feedback/feeds/opml.py`, `tests/unit/test_opml.py`

### 2.2 Episode Filtering & Sorting
**Priority**: Medium

Users with many episodes need filtering.

**Tasks**:
- [ ] Add filter dropdown/toggle: All | Unplayed | Downloaded | In Progress
- [ ] Add sort options: Date (newest/oldest) | Title | Duration
- [ ] Persist filter/sort preferences per feed
- [ ] Show filter indicator in UI
- [ ] Add keyboard shortcuts for quick filters

**Files**: `src/feedback/widgets/episode_list.py`, `src/feedback/screens/primary.py`

### 2.3 Feed Management
**Priority**: Medium

Better organization for users with many feeds.

**Tasks**:
- [ ] Add feed categories/folders (database schema change)
- [ ] Implement drag-to-reorder or manual ordering
- [ ] Add "Mark All as Played" for a feed
- [ ] Add feed info modal (show URL, last updated, episode count)
- [ ] Add feed refresh indicator (show when last refreshed)
- [ ] Detect duplicate feed URLs on add

**Files**: `src/feedback/widgets/feed_list.py`, `src/feedback/database.py`, `src/feedback/models/feed.py`

### 2.4 Help System
**Priority**: Medium

Current help is just a notification.

**Tasks**:
- [ ] Create `HelpScreen` with full keybinding reference
- [ ] Organize by category (Navigation, Playback, Management)
- [ ] Make context-sensitive (show relevant keys per screen)
- [ ] Add `?` key binding to toggle help overlay
- [ ] Include version info and links

**New Files**: `src/feedback/screens/help.py`

---

## Phase 3: User Experience Polish

**Goal**: Professional-quality UX

### 3.1 Settings Screen
**Priority**: Medium

Users shouldn't need to edit config files.

**Tasks**:
- [ ] Create `SettingsScreen` with sections
- [ ] Player settings: backend selection, default volume, default speed
- [ ] Network settings: timeout, max episodes, proxy
- [ ] Download settings: directory, concurrent limit
- [ ] Discovery settings: API credentials input
- [ ] Theme/color selector with preview
- [ ] Apply changes without restart (hot reload)
- [ ] Reset to defaults option

**New Files**: `src/feedback/screens/settings.py`

### 3.2 Confirmation Dialogs
**Priority**: Medium

Prevent accidental destructive actions.

**Tasks**:
- [ ] Add confirmation for feed deletion
- [ ] Add confirmation for clearing queue
- [ ] Add confirmation for canceling all downloads
- [ ] Add confirmation for deleting downloaded files
- [ ] Make confirmations optional via config

**Files**: Various screens

### 3.3 Progress Indicators
**Priority**: Low

Better feedback for long operations.

**Tasks**:
- [ ] Add loading spinner for feed refresh
- [ ] Add progress bar for batch operations
- [ ] Show "Refreshing X of Y feeds" during refresh all
- [ ] Add subtle animation for background operations

### 3.4 Error Handling Improvements
**Priority**: Medium

Better recovery from errors.

**Tasks**:
- [ ] Show retry option on network errors
- [ ] Provide specific error messages (not just "failed")
- [ ] Log errors to file for debugging
- [ ] Add "Report Issue" link in error dialogs
- [ ] Graceful degradation when player unavailable

---

## Phase 4: Advanced Features

**Goal**: Competitive feature set

### 4.1 Playback Enhancements
**Priority**: Medium

Power user features.

**Tasks**:
- [ ] Sleep timer (15/30/45/60 min or end of episode)
- [ ] Playback history screen (last 50 episodes)
- [ ] Chapter support (if podcast provides chapters)
- [ ] Skip silence option (requires audio analysis)
- [ ] Per-podcast playback speed memory
- [ ] Audio boost/normalization option

### 4.2 Smart Features
**Priority**: Low

Intelligent automation.

**Tasks**:
- [ ] Auto-download new episodes (configurable per feed)
- [ ] Auto-cleanup old episodes (keep last N)
- [ ] Smart queue: auto-add new episodes from favorites
- [ ] Listening statistics dashboard
- [ ] "Continue Listening" quick action

### 4.3 Discovery Enhancements
**Priority**: Low

Better podcast discovery.

**Tasks**:
- [ ] Browse by category (Podcast Index categories)
- [ ] Trending podcasts screen
- [ ] "Subscribe" button directly from search results
- [ ] Recently added podcasts
- [ ] Curated recommendations

### 4.4 Sync & Backup
**Priority**: Low

Multi-device support.

**Tasks**:
- [ ] Export/import full database
- [ ] gpodder.net sync support
- [ ] Local backup automation
- [ ] Nextcloud sync option

---

## Phase 5: Platform & Distribution

**Goal**: Easy installation everywhere

### 5.1 Packaging
**Priority**: High (for release)

**Tasks**:
- [ ] PyPI release automation (already in CI)
- [ ] Homebrew formula for macOS
- [ ] AUR package for Arch Linux
- [ ] Snap package for Ubuntu
- [ ] Flatpak for Linux desktop
- [ ] Windows installer (if demand exists)

### 5.2 Documentation
**Priority**: High

**Tasks**:
- [ ] Complete user guide with screenshots
- [ ] Video tutorial/demo
- [ ] FAQ section
- [ ] Troubleshooting guide
- [ ] Developer documentation for contributors

### 5.3 Community
**Priority**: Medium

**Tasks**:
- [ ] Issue templates (bug, feature request)
- [ ] Contributing guide
- [ ] Code of conduct
- [ ] Discussion forum or Discord
- [ ] Regular release notes

---

## Technical Debt

Items to address alongside features:

### Code Quality
- [ ] Add pre-commit hooks for all contributors
- [ ] Set up GitHub Actions for PR checks
- [ ] Add integration tests for full user flows
- [ ] Performance profiling for large libraries (1000+ episodes)
- [ ] Memory leak testing for long-running sessions

### Architecture
- [ ] Consider plugin system for player backends
- [ ] Abstract storage layer (for future cloud sync)
- [ ] Event bus for loose coupling between components
- [ ] Consider sqlite-vec for semantic search

### Testing
- [ ] Add end-to-end tests with Textual's pilot
- [ ] Snapshot testing for UI components
- [ ] Stress testing with large datasets
- [ ] Cross-platform CI (Linux, macOS, Windows)

---

## Release Schedule

### v0.1.0 - Alpha (Current)
- Core functionality working
- Primary screen functional
- Queue and Downloads stubbed

### v0.2.0 - Beta
- Phase 1 complete (all screens functional)
- OPML import/export
- Progress persistence
- Basic help system

### v0.3.0 - Release Candidate
- Phase 2 complete
- Settings screen
- Episode filtering
- Polished UX

### v1.0.0 - Stable Release
- Phase 3 complete
- Full documentation
- Package distribution
- Community infrastructure

### v1.x - Feature Releases
- Phase 4 features
- Community-requested features
- Performance improvements

---

## Contributing

We welcome contributions! Priority areas:

1. **High Impact**: Queue screen, Downloads screen, OPML support
2. **Good First Issues**: Help screen, confirmation dialogs, keyboard shortcuts
3. **Documentation**: User guide, screenshots, tutorials

See [CONTRIBUTING.md](docs/development/contributing.md) for guidelines.

---

## Feedback

Have ideas? Open an issue at [github.com/michellepellon/feedback/issues](https://github.com/michellepellon/feedback/issues)
