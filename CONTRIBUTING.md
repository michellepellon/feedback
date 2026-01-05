# Contributing to Feedback

First off, thank you for considering contributing to Feedback! It's people like you that make Feedback such a great tool for podcast lovers.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)
- [Priority Areas](#priority-areas)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

### Good First Issues

Looking for a place to start? Check out issues labeled [`good first issue`](https://github.com/michellepellon/feedback/labels/good%20first%20issue) - these are specifically curated for new contributors.

### Types of Contributions

We welcome many types of contributions:

- **Bug fixes**: Found a bug? We'd love a fix!
- **Features**: Check the [ROADMAP.md](ROADMAP.md) for planned features
- **Documentation**: Help improve our docs, README, or code comments
- **Tests**: More test coverage is always welcome
- **UI/UX**: Suggestions for better user experience

## Development Setup

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- VLC or MPV for audio playback (optional but recommended)

### Setup Steps

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/feedback.git
   cd feedback
   ```

2. **Install dependencies with uv**

   ```bash
   uv sync
   ```

3. **Verify setup**

   ```bash
   uv run pytest tests/
   uv run feedback --version
   ```

4. **Run the application**

   ```bash
   uv run feedback
   ```

### Project Structure

```
feedback/
├── src/feedback/           # Main source code
│   ├── screens/            # TUI screens (primary, queue, downloads, etc.)
│   ├── widgets/            # Reusable UI widgets
│   ├── feeds/              # Feed fetching and parsing
│   ├── player/             # Audio player backends
│   ├── models/             # Data models (Pydantic)
│   ├── app.py              # Main application class
│   ├── database.py         # SQLite database layer
│   └── config.py           # Configuration management
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── ui/                 # UI/screen tests
├── pyproject.toml          # Project configuration
└── ROADMAP.md              # Development roadmap
```

## Making Changes

### Branching Strategy

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes in small, focused commits

3. Keep your branch up to date with main:
   ```bash
   git fetch origin
   git rebase origin/main
   ```

### Commit Messages

Write clear, concise commit messages:

- Use the imperative mood ("Add feature" not "Added feature")
- Keep the first line under 72 characters
- Reference issues when relevant: "Fix #123: Handle empty feed gracefully"

Examples:
```
Add sleep timer with configurable durations

- Support 15/30/45/60 minute timers
- Add end-of-episode mode
- Integrate with player bar display
```

## Testing

We maintain high test coverage (95%+). All changes should include appropriate tests.

### Running Tests

```bash
# Run all tests
uv run pytest tests/

# Run with coverage
uv run pytest tests/ --cov=src/feedback

# Run specific test file
uv run pytest tests/unit/test_models.py

# Run tests matching a pattern
uv run pytest -k "test_sleep"
```

### Writing Tests

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Place UI tests in `tests/ui/`
- Follow existing test patterns and naming conventions
- Use pytest fixtures from `conftest.py`

## Pull Request Process

1. **Before submitting:**
   - Ensure all tests pass: `uv run pytest tests/`
   - Check code style: `uv run ruff check src/ tests/`
   - Format code: `uv run ruff format src/ tests/`
   - Run type checking: `uv run mypy src/`

2. **PR Description:**
   - Clearly describe what your PR does
   - Reference any related issues
   - Include screenshots for UI changes
   - List any breaking changes

3. **Review Process:**
   - PRs require at least one approval
   - Address review feedback promptly
   - Keep PRs focused and reasonably sized

## Style Guidelines

### Python Style

We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check style
uv run ruff check src/ tests/

# Auto-fix issues
uv run ruff check --fix src/ tests/

# Format code
uv run ruff format src/ tests/
```

Key conventions:
- Use type hints for all function signatures
- Write docstrings for public functions and classes
- Keep functions focused and under 50 lines when possible
- Prefer explicit over implicit

### UI Guidelines

- Follow Textual's widget patterns
- Use consistent keybindings (j/k for navigation, etc.)
- Show user feedback for all actions (notifications)
- Handle errors gracefully with clear messages

## Priority Areas

We especially welcome contributions in these areas:

### High Impact
- Player backend improvements (VLC/MPV stability)
- Performance optimization for large libraries
- Cross-platform testing and fixes

### Good First Issues
- Documentation improvements
- Additional keyboard shortcuts
- UI polish and consistency

### Advanced
- New player backends
- Sync providers (gpodder.net, etc.)
- Plugin system design

## Questions?

- Open a [Discussion](https://github.com/michellepellon/feedback/discussions) for questions
- Check existing issues before opening a new one
- Join our community chat (coming soon)

Thank you for contributing to Feedback!
