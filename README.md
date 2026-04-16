# vibe-kb

LLM-powered knowledge base system inspired by Andrej Karpathy's approach. Raw source materials (ePubs, articles, YouTube videos) are compiled by LLMs into a navigable markdown wiki with wikilinks and backlinks, queryable through Claude Code.

## Installation

```bash
# Clone repo
git clone git@github.com:mlgruby/vibe-kb.git
cd vibe-kb

# Install with uv
uv sync
uv tool install -e .
```

## Quick Start

```bash
# Create knowledge base
kb create ml-research --vault-path ~/obsidian-vault

# Add sources
kb add ml-research --epub "book.epub"
kb add ml-research --youtube "https://youtube.com/watch?v=..."

# Search wiki
kb search ml-research "transformers"

# Show stats
kb stats ml-research
```

## Claude Code Skills

Use these skills for conversational workflows:

- `/kb:create` - Initialize new knowledge base
- `/kb:add-source` - Add materials conversationally
- `/kb:compile` - Compile raw sources into wiki
- `/kb:research` - Q&A against knowledge base
- `/kb:health-check` - Wiki maintenance (coming soon)

## Architecture

Two-layer design:
- **CLI** (AI-free): File operations, format conversion, search
- **Skills** (AI-powered): Compilation, Q&A, health checks

Knowledge base format is portable - any AI tool can operate on the same markdown files.

## Project Structure

```
knowledge-bases/<name>/
├── raw/          # Source materials
├── wiki/         # LLM-compiled wiki
└── outputs/      # Q&A results
```

## Development

```bash
# Run tests
uv run pytest

# Run CLI in dev mode
uv run kb --help

# Lint
uv run ruff check src/
```

## License

MIT
