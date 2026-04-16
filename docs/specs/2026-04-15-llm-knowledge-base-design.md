# vibe-kb — LLM Knowledge Base System Design Spec

**Date:** 2026-04-15
**Repo:** `git@github.com:mlgruby/vibe-kb.git`
**Inspired by:** Andrej Karpathy's LLM Knowledge Bases concept
**Status:** Approved

## Overview

A system for building personal knowledge bases using LLMs. Raw source materials (articles, papers, ePubs, YouTube videos, repos) are collected into a `raw/` directory, then compiled by an LLM into a navigable markdown wiki with wikilinks and backlinks. The wiki is viewable in Obsidian, queryable through conversational AI, and incrementally enhanced through Q&A outputs filed back into the knowledge base.

The user rarely writes or edits the wiki manually — it is the LLM's domain.

## Architecture

### Two-Layer Design

| Layer | Responsibility | AI Dependency |
|-------|---------------|---------------|
| **`kb` CLI** | File operations, format conversion (ePub→md, YouTube→transcript), text search, validation, git | None — pure Python package |
| **Skills** | Compilation logic, Q&A, health checks, content generation | AI-specific (one set per tool) |

**Portability strategy:** The knowledge base format (markdown + wikilinks) is the interface. Any AI tool that can read files can operate on the same knowledge base. No adapter layer — each AI tool uses its native capabilities.

### Integration with Obsidian

- **Vault path:** `/Users/satyasheel/Insync/satyasheel@ymail.com/Dropbox/obsidian-satya/`
- **KB location:** `knowledge-bases/` subfolder inside the vault
- Knowledge bases are isolated from personal notes
- LLM tools only operate within `knowledge-bases/` boundary
- Obsidian plugins: Marp (slides), standard markdown rendering, graph view

## Knowledge Base Structure

Each knowledge base is independent with this structure:

```
knowledge-bases/<kb-name>/
├── raw/                          # Source materials (user-managed)
│   ├── articles/                 # Web articles (markdown)
│   ├── papers/                   # Academic papers (PDF)
│   ├── books/                    # ePub books
│   ├── videos/                   # YouTube transcripts
│   ├── repos/                    # Code repositories
│   └── datasets/                 # Data files
├── wiki/                         # LLM-compiled knowledge (LLM-managed)
│   ├── _index.md                 # Master index of all articles
│   ├── _concepts.md              # Concept hierarchy with backlink counts
│   ├── _sources.md               # All source materials with summaries
│   ├── concepts/                 # Core concept articles
│   ├── summaries/                # Source material summaries
│   │   ├── articles/
│   │   ├── papers/
│   │   ├── books/
│   │   └── videos/
│   ├── topics/                   # Thematic collections
│   └── .templates/               # Article templates for LLM
│       ├── concept-article.md
│       ├── article-summary.md
│       ├── paper-summary.md
│       ├── book-summary.md
│       └── video-summary.md
├── outputs/                      # Q&A results (LLM-generated)
│   └── YYYY-MM-DD-description.{md,slides.md,png}
└── .kbconfig                     # Metadata (last compile, stats)
```

## Source Material Types

| Type | Input Format | CLI Command | Processing |
|------|-------------|-------------|------------|
| Web articles | URL | `kb add --url <url>` | Fetch, convert to markdown, download images |
| Academic papers | PDF/URL | `kb add --arxiv <query>` | Extract text, metadata |
| Books | ePub | `kb add --epub <path>` | Extract chapters, images, create per-chapter + full summary |
| YouTube videos | URL | `kb add --youtube <url>` | Extract transcript, metadata, timestamps |
| Code repos | Directory | `kb add --file <path>` | Copy/symlink |
| Datasets | Files | `kb add --file <path>` | Copy, extract metadata |

**Auto-detection:** `kb add --file` detects type by file extension (`.epub` → books, `.pdf` → papers, `.md` → articles, directories → repos).
| Batch import | Directory | `kb add --scan-dir <path> --type epub` | Scan and import matching files |

**File naming convention:** `YYYY-MM-DD-title-slug.md`
**Metadata:** `.meta.json` alongside each source with URL, date, author, type.

## Wiki Compilation

### Incremental Compile Process

1. Scan `raw/` for new/modified content since last compile
2. For each new source:
   - Generate summary (250-500 words) using article template
   - Extract key concepts and entities
   - Create `[[wikilinks]]` to existing concepts
   - Add backlinks from existing articles to new content
   - Update index files (`_index.md`, `_concepts.md`, `_sources.md`)
3. Structural changes (requiring approval):
   - New concept article (when concept appears in 3+ sources)
   - Reorganization of categories
   - Merging/splitting existing articles
   - Show preview, wait for y/n/edit
4. Apply approved changes to `wiki/`
5. Git commit: `kb: compiled N new sources into <kb-name>`
6. Run health check automatically

### Wikilink Intelligence

The LLM actively manages Obsidian `[[wikilinks]]`:

- **On compile:** Creates links from new articles to existing concepts, and updates existing articles to reference new content
- **Backlink-guided updates:** When a new paper on "Flash Attention 2" arrives, the LLM follows backlinks from `[[Attention Mechanism]]` to find all related articles that should be updated
- **Update propagation preview:**
  ```
  Found 3 related articles that should reference this:
  → [[Attention Mechanism]] - add note about Flash Attention 2
  → [[Multi-Head Attention]] - update with new optimization technique  
  → [[Transformers]] - add to "Recent Advances" section
  Apply updates? [y/n/preview]
  ```

## Article Templates

### Concept Article Template

```markdown
---
type: concept
created: YYYY-MM-DD
updated: YYYY-MM-DD
related: [[concept1]], [[concept2]]
---

# Concept Name

## Overview
Brief 2-3 sentence definition

## Key Ideas
- Main points with [[wikilinks]] to related concepts

## Applications
Where this concept is used

## Sources
- [[source1]] - key insight
- [[source2]] - alternative view

## Open Questions
Areas for further research
```

### Source Summary Template

```markdown
---
type: summary
source_type: paper|book|video|article
source_url: URL
added: YYYY-MM-DD
authors: names
---

# Title

## Summary
250-500 word overview

## Key Concepts
- [[concept1]] - explanation
- [[concept2]] - explanation

## Notable Quotes/Insights
> Key passages

## Related Work
- [[other-source1]]
- [[other-source2]]

## Questions Raised
Things to explore further
```

## CLI Commands

```bash
# Knowledge base management
kb create <name>                              # Initialize new KB
kb list                                       # List all knowledge bases
kb stats <name>                               # Article count, word count, etc.

# Adding source materials
kb add <name> --url <url>                     # Web article
kb add <name> --arxiv <query> [--limit N]     # arXiv papers
kb add <name> --epub <path>                   # ePub book
kb add <name> --youtube <url>                 # YouTube video
kb add <name> --youtube-playlist <url>        # YouTube playlist
kb add <name> --file <path>                   # Auto-detect type
kb add <name> --scan-dir <path> --type <type> # Batch import

# Search (no AI required)
kb search <name> <query>                      # Text search over wiki

# Maintenance (no AI required)
kb stats <name>                               # Show statistics
```

The CLI is AI-free and installed via `uv tool install -e .` which registers the `kb` command globally (or use `uv run kb` during development). All LLM-powered operations (compile, Q&A, health-check) are handled by skills.

## Skills

### `kb:create` — Initialize Knowledge Base
- Conversational: asks for topic, initial sources
- Creates directory structure and templates
- Optionally scans a directory for existing files to import

### `kb:add-source` — Add Material
- Conversational: asks what you're adding (URL, file, YouTube link)
- Calls `kb add` CLI for conversion
- Offers to compile immediately after adding

### `kb:compile` — Compile Raw Sources into Wiki
- Reads new sources from `raw/`
- Loads wiki index, templates, existing articles
- Generates summaries, creates wikilinks
- Previews structural changes (new concept articles, reorganizations)
- Applies approved changes
- Commits to git
- Runs health check after completion

### `kb:research` — Deep Q&A Session
- Multi-turn conversation against the knowledge base
- Follows wikilinks and backlinks for context
- Reads index files to find relevant articles
- Generates outputs in requested format (markdown, Marp slides, matplotlib charts)
- Offers to file valuable outputs back into wiki

### `kb:health-check` — Wiki Maintenance
- Checks for: orphaned articles, dead links, stale summaries, missing metadata, inconsistent data, unindexed sources, template drift
- Reports issues by severity (critical, warning, suggestion)
- Offers to auto-fix simple issues
- Suggests new articles, merges, and further research questions
- Shows stats (article count, source count, concept count, backlink count)

## Output Formats

| Format | Use Case | Tool |
|--------|----------|------|
| Markdown (.md) | Research answers, summaries, comparisons | Direct write |
| Marp slides (.slides.md) | Presentations, findings overview | Marp plugin in Obsidian |
| Charts (.png) | Data comparisons, timelines | matplotlib |
| Mermaid diagrams (.mermaid.md) | Architecture, relationships | Obsidian mermaid support |

Outputs saved to `outputs/YYYY-MM-DD-description.{format}`.
Valuable outputs can be filed back into `wiki/` to enhance the knowledge base for future queries.

## Health Check Details

| Check | Description | Auto-fixable? |
|-------|-------------|---------------|
| Orphaned articles | Wiki articles with no backlinks | Suggests where to add links |
| Dead links | `[[wikilinks]]` to non-existent articles | Creates stub or removes |
| Stale summaries | Source updated but summary not recompiled | Triggers recompile |
| Missing metadata | Articles without frontmatter | Fills from content |
| Inconsistent data | Conflicting claims across articles | Flags with references |
| Unindexed sources | Files in `raw/` not compiled | Lists for compilation |
| Template drift | Articles not following template | Suggests reformatting |

## Technology Stack

- **Language:** Python 3.11+
- **Package manager:** uv (fast dependency management, virtual environments, lock files)
- **CLI framework:** Click or Typer
- **Package:** `vibe-kb` (installable via `uv tool install -e .`)
- **Skills:** Markdown prompt files (Claude Code skills format)
- **Python dependencies:**
  - `click` or `typer` — CLI framework
  - `ebooklib` — ePub parsing
  - `yt-dlp` — YouTube transcript extraction
  - `matplotlib` — Chart generation
  - `markdown` — Markdown processing
  - `beautifulsoup4` — HTML/web content parsing
  - `requests` — URL fetching
- **Dev dependencies:** pytest, ruff (linting/formatting)
- **Storage:** Obsidian vault (Dropbox-synced)
- **Version control:** Git for wiki change tracking

## Project Structure

```
vibe-kb/
├── pyproject.toml                # Package config, dependencies, entry points
├── uv.lock                       # Locked dependencies (reproducible installs)
├── src/
│   └── vibe_kb/
│       ├── __init__.py
│       ├── cli.py                # CLI entry point (kb command)
│       ├── add/                  # Source ingestion modules
│       │   ├── epub.py           # ePub conversion
│       │   ├── youtube.py        # YouTube transcript extraction
│       │   ├── url.py            # Web article fetching
│       │   └── arxiv.py          # arXiv paper fetching
│       ├── search.py             # Text search over wiki
│       ├── health.py             # Health check system
│       ├── config.py             # .kbconfig management
│       └── utils/
│           ├── markdown.py       # Markdown processing
│           ├── git.py            # Git operations
│           └── files.py          # File naming, metadata
├── skills/                       # Claude Code skills (markdown)
│   ├── kb-create.md
│   ├── kb-add-source.md
│   ├── kb-compile.md
│   ├── kb-research.md
│   └── kb-health-check.md
├── tests/
│   ├── test_add/
│   ├── test_search.py
│   └── test_health.py
└── docs/
```

## MVP Scope

**Focus:** One knowledge base (`ml-research`) end-to-end.

**Success criteria:**
1. Add 20+ sources (mix of ePubs, articles, YouTube videos)
2. Compile produces navigable wiki with wikilinks and backlinks
3. Ask 5 complex questions and get useful answers referencing multiple sources
4. Generate at least one slide deck and one visualization
5. File an output back into the wiki and see it referenced in future queries
6. Health check finds real issues and actionable suggestions

**Bootstrap plan:**
1. Initialize `knowledge-bases/ml-research/` in Obsidian vault
2. Import existing ePubs from `Case-Studies-And-Reviews/`
3. First compile: generate summaries and concept map
4. First research session: test Q&A against compiled wiki
5. Iterate: add more sources, refine templates, tune prompts

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Context limits at 400K words | LLM can't reason across full wiki | Strong index files (`_index.md`, `_concepts.md`) guide the LLM to relevant content |
| ePub conversion quality | Messy formatting in summaries | CLI cleanup layer normalizes content before LLM sees it |
| YouTube auto-caption quality | Inaccurate transcripts | Flag low-confidence transcripts for manual review |
| Git history bloat | Large repo over time | Commit only meaningful changes, not intermediate states |

## Future Extensions (Post-MVP)

- Additional knowledge bases (blockchain, web dev, etc.)
- Additional AI provider skills (Gemini CLI, Cursor)
- Cron-based automation (scheduled health checks, auto-compile)
- Web-based search engine over wiki
- Cross-knowledge-base queries
- Synthetic data generation + fine-tuning
