# Contributing to vibe-kb

Thank you for your interest in contributing. This document covers how to set up your development environment, the conventions we follow, and the process for getting changes merged.

---

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Writing Tests](#writing-tests)
- [Code Style](#code-style)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [What to Work On](#what-to-work-on)
- [Design Principles](#design-principles)

---

## Development Setup

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/)

```bash
git clone git@github.com:mlgruby/vibe-kb.git
cd vibe-kb

# Install all dependencies including dev tools
uv sync

# Verify the CLI works
uv run kb --help

# Run the full test suite
uv run pytest
```

That's it. No virtual environment activation needed — `uv run` handles it.

---

## Project Structure

```
vibe-kb/
├── src/vibe_kb/
│   ├── cli.py              # All Click commands live here
│   ├── config.py           # KBConfig dataclass (.kbconfig read/write)
│   ├── search.py           # search_wiki() — pure function, no CLI
│   ├── add/
│   │   ├── epub.py         # extract_epub_to_markdown(), get_epub_metadata()
│   │   ├── youtube.py      # extract_youtube_transcript(), _parse_vtt()
│   │   ├── url.py          # stub — not yet implemented
│   │   └── arxiv.py        # stub — not yet implemented
│   └── utils/
│       ├── files.py        # generate_filename(), create_metadata()
│       ├── git.py          # stub — not yet implemented
│       └── markdown.py     # stub — not yet implemented
├── skills/                 # Claude Code skill prompt files (markdown)
├── tests/
│   ├── test_properties.py  # Hypothesis property-based tests
│   ├── test_search.py
│   ├── test_config.py
│   ├── test_cli_create.py
│   ├── test_cli_stats.py
│   ├── conftest.py         # Hypothesis profile configuration
│   └── test_add/
│       ├── test_epub.py
│       └── test_youtube.py
├── docs/
│   └── specs/              # Design specification documents
└── .github/workflows/ci.yml
```

**Key separation:** the `add/` modules contain pure extraction logic — no Click, no `sys.exit`. The CLI wiring (argument parsing, user feedback, error display) lives in `cli.py`. Keep them separate.

---

## Development Workflow

We follow **Test-Driven Development**. The cycle is:

1. Write a failing test that captures the intended behaviour
2. Run it to confirm it fails for the right reason
3. Implement the minimum code to make it pass
4. Run the full suite to check for regressions
5. Refactor if needed

```bash
# Run a single test file while developing
uv run pytest tests/test_add/test_epub.py -v

# Run a single test
uv run pytest tests/test_add/test_epub.py::test_extract_epub_basic -v

# Run the full suite
uv run pytest

# Run property tests (slower — uses Hypothesis)
uv run pytest tests/test_properties.py -v
```

---

## Writing Tests

### Unit tests

Each module in `src/vibe_kb/` has a corresponding test file. Tests use `pytest` and `tmp_path` for file system operations.

```python
def test_generate_filename_basic(tmp_path):
    result = generate_filename("Attention Is All You Need")
    assert result.startswith(date.today().isoformat())
    assert result.endswith(".md")
    assert "/" not in result
```

### CLI integration tests

Use Click's `CliRunner` to test commands end-to-end:

```python
from click.testing import CliRunner
from vibe_kb.cli import cli

def test_create_command(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "knowledge-bases" / "test-kb").exists()
```

### Property-based tests

For functions that process strings or paths, add Hypothesis tests in `tests/test_properties.py`:

```python
from hypothesis import given, settings
from hypothesis import strategies as st

@given(st.text(min_size=1).filter(lambda t: re.search(r'[a-zA-Z0-9]', t)))
@settings(max_examples=200)
def test_generate_filename_never_has_path_separator(title):
    result = generate_filename(title)
    assert "/" not in result
    assert "\\" not in result
```

### Mocking external services

Use `unittest.mock.patch` to avoid network calls in tests. Both `epub.py` and `youtube.py` have examples showing how to mock `ebooklib` and `yt_dlp` respectively.

### Coverage expectations

- New CLI commands: integration test + edge case tests (missing KB, invalid input, partial failure rollback)
- New ingestion modules: unit tests for extraction logic + CLI integration test
- New utility functions: unit tests + property tests if the function processes strings or paths

---

## Code Style

We use [ruff](https://docs.astral.sh/ruff/) for both linting and formatting. It runs automatically in CI.

```bash
# Check for issues
uv run ruff check src/ tests/

# Auto-fix fixable issues
uv run ruff check --fix src/ tests/

# Format
uv run ruff format src/ tests/
```

**Style conventions:**

- Line length: 100 characters
- String quotes: double quotes (ruff enforces this)
- Imports: standard library first, then third-party, then local
- Type hints: required on all public functions
- Docstrings: required on all public functions and classes; use Google style (`Args:`, `Returns:`, `Raises:`)
- Encoding: always specify `encoding='utf-8'` on `read_text()` / `write_text()` calls
- Error handling: raise `ValueError` for user-input problems, let the CLI layer catch and display them

**What not to do:**

- Do not add `as e` to `except` clauses unless you use `e`
- Do not catch broad `Exception` in library code — only in CLI command handlers
- Do not use `~/...` in shell examples in skill files (tilde does not expand in double-quoted strings) — use `$HOME/...`

---

## Submitting a Pull Request

1. **Fork** the repo and create a branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** following the TDD workflow above.

3. **Run the full suite locally** before pushing:
   ```bash
   uv run pytest
   uv run ruff check src/ tests/
   uv run ruff format --check src/ tests/
   ```

4. **Push and open a PR** against `main`. The CI pipeline will run automatically:
   - Lint (ruff check + format)
   - Tests on Python 3.11 and 3.12
   - Property tests (1000 Hypothesis examples)
   - Security audit (pip-audit)

5. **PR description** — briefly explain what the change does and why. If it closes an issue, reference it.

### Commit messages

Use conventional commit format:

```
feat: add kb add --url command for web article ingestion
fix: roll back epub markdown on metadata write failure
docs: expand README with installation walkthrough
test: add property tests for url slug generation
chore: add Apache 2.0 license
ci: add security audit job to CI workflow
```

---

## What to Work On

The clearest contribution opportunities, in rough priority order:

### High priority (MVP gaps)

- **`kb add --url`** — implement `add/url.py` using `requests` + `beautifulsoup4` to fetch a URL, strip boilerplate, and convert to markdown. Wire up `--url` option in `cli.py`. See `add/epub.py` for the pattern to follow.
- **`kb:health-check` skill** — write `skills/kb-health-check.md` following the spec in `docs/specs/`. The skill should check for orphaned articles, dead wikilinks, stale summaries, missing metadata, and unindexed sources.
- **`kb list`** — add a `list` command to `cli.py` that scans `vault/knowledge-bases/` and prints each KB with its topic and last-compile time.

### Medium priority

- **`kb add --arxiv`** — implement `add/arxiv.py` using the arXiv API (no API key required). The spec describes `kb add <name> --arxiv <query> [--limit N]`.
- **`wiki/_index.md`, `_concepts.md`, `_sources.md` scaffolding** — `kb create` should create these empty index files so the research skill can read them before the first compile.
- **`utils/git.py`** — implement the git utility layer (stage, commit, log) so the compile skill can call `kb` Python functions rather than raw shell commands.

### Good first issues

- **`kb add --file` auto-detection** — detect file type by extension (`.epub` → books, `.pdf` → papers, `.md` → articles, directories → repos) and route to the appropriate ingestion path.
- **Improve `kb stats` output** — add per-category source counts (books: 3, videos: 5, articles: 2).
- **`--format` flag for `kb search`** — support `--format json` for programmatic output.

---

## Design Principles

Keep these in mind when making changes:

**1. The CLI is AI-free.**
`src/vibe_kb/` must work with no network access and no API keys. If you need to call an LLM, that logic belongs in a skill file (`skills/`), not in Python.

**2. The wiki format is the interface.**
The knowledge base is plain markdown with `[[wikilinks]]`. Any AI tool should be able to read and write it. Avoid formats or structures that couple the wiki to any specific tool.

**3. Ingestion is transactional.**
If an ingestion command fails partway through (extraction succeeded, metadata write failed), it must clean up any files it created so a retry starts clean. See `_add_epub()` and `_add_youtube()` for the pattern: track `output_created = False`, set to `True` after writing, and roll back in the `except` block.

**4. Security at the boundary.**
Validate KB names (`_validate_kb_name()`), skip symlinks in directory traversal (`is_symlink()` checks), and check parent directory names when filtering wiki files. These guards exist because the CLI accepts user-controlled strings that become file paths.

**5. Test invariants, not just examples.**
When adding functions that process strings or paths, add a Hypothesis property test in `tests/test_properties.py` as well as concrete examples. The property tests have already caught real bugs (URL validation logic, path traversal).

---

## Questions?

Open an issue on GitHub — [mlgruby/vibe-kb](https://github.com/mlgruby/vibe-kb/issues).
