# Contributing

Thank you for your interest in contributing to Feedback!

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Git

### Clone and Install

```bash
git clone https://github.com/xgi/feedback.git
cd feedback
uv sync
```

### Verify Setup

```bash
uv run pytest
uv run feedback
```

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/feedback

# Run specific tests
uv run pytest tests/unit/test_config.py -v
```

### Linting and Formatting

```bash
# Check code style
uv run ruff check src tests

# Auto-fix issues
uv run ruff check --fix src tests

# Format code
uv run ruff format src tests
```

### Type Checking

```bash
uv run mypy src/feedback
```

### Run All Checks

```bash
uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src/feedback && uv run pytest
```

## Code Style

### Python

- **Formatter**: ruff format
- **Linter**: ruff
- **Type checker**: mypy (strict mode)
- **Line length**: 88 characters
- **Python version**: 3.12+

### Imports

```python
# Standard library
from __future__ import annotations
import asyncio
from pathlib import Path

# Third-party
import httpx
from pydantic import BaseModel

# Local
from feedback.models import Feed
```

### Type Annotations

Use modern Python 3.12+ syntax:

```python
# Good
def get_feed(url: str) -> Feed | None: ...
items: list[str] = []

# Avoid
from typing import Optional, List
def get_feed(url: str) -> Optional[Feed]: ...
```

### Async/Await

Prefer async for I/O operations:

```python
# Good
async def fetch_feed(url: str) -> Feed:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        ...

# Avoid synchronous I/O in async context
```

## Pull Request Process

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/your-feature`
3. **Make changes** with tests
4. **Run checks**: `uv run pytest && uv run ruff check && uv run mypy src`
5. **Commit**: `git commit -m "feat: add your feature"`
6. **Push**: `git push origin feature/your-feature`
7. **Open PR** against `main`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add batch download support
fix: episode progress not saving
docs: update configuration guide
test: add YouTube feed tests
refactor: simplify player interface
```

### PR Requirements

- [ ] All tests pass
- [ ] Coverage remains above 95%
- [ ] No linting errors
- [ ] Type checks pass
- [ ] Documentation updated (if needed)

## Testing Guidelines

### Test Organization

```
tests/
├── unit/           # Unit tests (fast, isolated)
├── integration/    # Integration tests (database, HTTP)
├── ui/             # UI tests (Textual pilot)
└── fixtures/       # Test data files
```

### Writing Tests

```python
import pytest
from feedback.config import Config

class TestConfig:
    def test_default_values(self):
        """Test default configuration values."""
        config = Config()
        assert config.player.backend == "vlc"

    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async functionality."""
        result = await some_async_function()
        assert result is not None
```

### Mocking HTTP

Use `respx` for HTTP mocking:

```python
import respx

@pytest.mark.asyncio
@respx.mock
async def test_fetch_feed():
    respx.get("https://example.com/feed").respond(200, content=b"<rss>...")
    result = await fetcher.fetch("https://example.com/feed")
    assert result is not None
```

## Documentation

### Building Docs

```bash
uv run mkdocs serve
```

Visit `http://localhost:8000` to preview.

### Docstrings

Use Google-style docstrings:

```python
def parse_feed(content: bytes) -> tuple[Feed, list[Episode]]:
    """Parse RSS/Atom feed content.

    Args:
        content: Raw XML bytes.

    Returns:
        Tuple of (Feed, list of Episodes).

    Raises:
        FeedParseError: If parsing fails.
    """
```

## Getting Help

- Open an issue for bugs or feature requests
- Discussions for questions and ideas
- Check existing issues before creating new ones
