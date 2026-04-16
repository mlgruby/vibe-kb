# vibe-kb

> Build a personal knowledge base that an LLM can reason over — not just search.

Inspired by [Andrej Karpathy's LLM knowledge bases concept](https://x.com/karpathy). You collect raw materials (ePubs, YouTube videos, articles, papers) into a `raw/` directory. An LLM compiles them into a navigable markdown wiki with `[[wikilinks]]` and backlinks. You then query that wiki conversationally through Claude Code skills — getting synthesised answers that cite your own sources, not the internet.

The wiki lives in your Obsidian vault so you can browse it, see the graph view, and take notes alongside it. The LLM does the writing; you do the reading.

---

## Why vibe-kb?

| The problem | How vibe-kb solves it |
|---|---|
| You have 20 books, 50 papers, 100 YouTube talks on a topic — and can't hold it all in your head | One command converts everything into a linked wiki you can query in natural language |
| ChatGPT/Claude answer from their training data, not your curated sources | Every answer cites articles in *your* knowledge base, grounded in what *you've* read |
| Highlights and notes scatter across Kindle, Notion, Apple Notes | One canonical wiki in Obsidian, built from source, always up to date |
| Reading a new paper means re-reading old ones for context | The compile step automatically links new sources to existing concepts you already captured |
| You forget what you've read six months later | The wiki persists and grows — future-you can query it |

---

## How it works

```
Raw sources                      LLM compile step                  You query it
──────────────                   ────────────────                  ────────────
books/deep-learning.epub    →    wiki/summaries/books/...    →    /kb:research
videos/karpathy-gpt.md      →    wiki/concepts/transformer.md →    "Compare attention
papers/attention.pdf        →    wiki/_index.md               →     mechanisms across
articles/scaling-laws.md    →    wiki/_concepts.md            →     my sources"
```

**Two-layer architecture:**

- **`kb` CLI** (Python, no AI) — file operations, format conversion, search, stats. Works offline, no API key needed.
- **Claude Code skills** (AI-powered) — compilation, Q&A, health checks. Uses your existing Claude Code session.

The knowledge base format is **portable markdown** — any AI tool that can read files can operate on the same wiki. No vendor lock-in.

---

## Installation

**Prerequisites:**
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [Obsidian](https://obsidian.md/) (optional but recommended for browsing the wiki)

```bash
# Clone the repo
git clone git@github.com:mlgruby/vibe-kb.git
cd vibe-kb

# Install the kb CLI globally
uv tool install -e .

# Verify installation
kb --version
```

During development, use `uv run kb` instead of `kb`.

---

## Quick Start

### 1. Create a knowledge base

```bash
kb create ml-research \
  --vault-path $HOME/obsidian-vault \
  --topic "Machine learning research"
```

This creates the full directory structure inside your Obsidian vault:

```
obsidian-vault/
└── knowledge-bases/
    └── ml-research/
        ├── raw/           ← you put source materials here
        │   ├── books/
        │   ├── videos/
        │   ├── papers/
        │   └── articles/
        ├── wiki/          ← LLM writes here
        │   ├── concepts/
        │   ├── summaries/
        │   └── .templates/
        └── outputs/       ← Q&A results saved here
```

### 2. Add source materials

```bash
# Add an ePub book
kb add ml-research \
  --epub "$HOME/Downloads/deep-learning-goodfellow.epub" \
  --vault-path $HOME/obsidian-vault

# Add a YouTube video (extracts transcript automatically)
kb add ml-research \
  --youtube "https://www.youtube.com/watch?v=kCc8FmEb1nY" \
  --vault-path $HOME/obsidian-vault
```

### 3. Compile the wiki (Claude Code skill)

Open Claude Code in the vibe-kb repo and run:

```
/kb:compile
```

The LLM reads your raw sources, generates summaries with `[[wikilinks]]` to related concepts, and writes structured articles into `wiki/`. It then asks for approval before making structural changes (new concept articles, reorganisations).

### 4. Research your knowledge base

```
/kb:research
```

Ask any question. The skill searches the wiki, follows wikilinks, synthesises an answer citing your sources, and offers to save the output as markdown, Marp slides, or a Mermaid diagram.

Example questions:
- *"Summarise the main ideas about attention mechanisms across my sources"*
- *"What are the key differences between GPT-style and BERT-style pretraining?"*
- *"Create a slide deck covering transformer architecture innovations from 2017–2024"*

### 5. Search the wiki directly

```bash
# Case-insensitive full-text search
kb search ml-research "attention mechanism"

# Case-sensitive
kb search ml-research "FlashAttention" --case-sensitive
```

### 6. Check statistics

```bash
kb stats ml-research --vault-path $HOME/obsidian-vault
```

```
Knowledge Base: ml-research
Topic: Machine learning research
Created: 2026-04-15T10:00:00
Last compile: 2026-04-16T14:30:00

Sources: 12
Wiki articles: 47
Total words: 84,321

Location: /Users/you/obsidian-vault/knowledge-bases/ml-research
```

---

## Claude Code Skills

All LLM-powered operations are Claude Code skills. Run them from Claude Code inside the vibe-kb directory:

| Skill | Command | What it does |
|---|---|---|
| Create KB | `/kb:create` | Conversational KB initialisation — asks for name, topic, initial sources |
| Add source | `/kb:add-source` | Guided source addition — asks what you're adding and where |
| Compile | `/kb:compile` | Reads `raw/`, generates summaries and wikilinks, updates the wiki |
| Research | `/kb:research` | Multi-turn Q&A against your wiki with output in any format |
| Health check | `/kb:health-check` | Finds orphaned articles, dead links, stale summaries *(coming soon)* |

---

## Supported Source Types

| Type | Command | What gets extracted |
|---|---|---|
| ePub books | `--epub` | Full text, chapter structure, author/title metadata |
| YouTube videos | `--youtube` | Full transcript (manual or auto-generated), timestamps, description |
| Web articles | `--url` *(coming soon)* | Article text, images, metadata |
| arXiv papers | `--arxiv` *(coming soon)* | Abstract, full text, authors, citation metadata |
| Any file | `--file` *(coming soon)* | Auto-detects by extension (`.epub`, `.pdf`, `.md`, directories) |

---

## Obsidian Integration

vibe-kb is designed to live inside an Obsidian vault:

- `[[wikilinks]]` — the compiled wiki uses Obsidian-native wikilinks throughout, so the graph view shows concept relationships automatically
- **Graph view** — see how concepts connect across all your sources
- **Marp slides** — output from `/kb:research` can be Marp slide decks, renderable directly in Obsidian with the Marp plugin
- **Backlinks panel** — every concept article shows what sources reference it

The LLM only writes inside `knowledge-bases/` — your personal notes are never touched.

---

## Architecture

```
vibe-kb/
├── src/vibe_kb/
│   ├── cli.py              # kb command entry point
│   ├── config.py           # .kbconfig management
│   ├── search.py           # Full-text wiki search
│   ├── add/
│   │   ├── epub.py         # ePub → markdown extraction
│   │   └── youtube.py      # YouTube transcript extraction
│   └── utils/
│       └── files.py        # Filename generation, .meta.json creation
├── skills/                 # Claude Code skill prompts
│   ├── kb-create.md
│   ├── kb-add-source.md
│   ├── kb-compile.md
│   └── kb-research.md
└── tests/                  # 100 tests (unit + integration + property-based)
```

**Design principles:**
- The CLI is AI-free and always works offline
- The wiki format is plain markdown — readable without any tooling
- Skills are plain markdown prompt files — readable, editable, portable
- Any AI tool (Gemini CLI, Cursor, etc.) can operate on the same wiki

---

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Run property-based tests (Hypothesis)
uv run pytest tests/test_properties.py -v

# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Run the CLI in dev mode (without global install)
uv run kb --help
```

### CI

Every pull request runs:

- **Lint** — `ruff check` + `ruff format --check`
- **Tests** — pytest on Python 3.11 and 3.12
- **Property tests** — Hypothesis with 1000 examples in CI
- **Security audit** — `pip-audit` CVE scan on runtime dependencies

---

## Roadmap

**MVP (current):**
- [x] `kb create` — initialise knowledge base
- [x] `kb add --epub` — add ePub books
- [x] `kb add --youtube` — add YouTube transcripts
- [x] `kb search` — full-text wiki search
- [x] `kb stats` — knowledge base statistics
- [x] `kb:compile` skill — LLM-powered wiki compilation
- [x] `kb:research` skill — conversational Q&A

**Coming soon:**
- [ ] `kb add --url` — web article ingestion
- [ ] `kb add --arxiv` — arXiv paper ingestion
- [ ] `kb list` — list all knowledge bases
- [ ] `kb:health-check` skill — wiki maintenance and issue detection

**Future:**
- [ ] `kb add --file` — auto-detect file type
- [ ] `kb add --scan-dir` — batch import
- [ ] Gemini CLI and Cursor skill variants
- [ ] Cron-based scheduled compilation
- [ ] Cross-knowledge-base queries

---

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
