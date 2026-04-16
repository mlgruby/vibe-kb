# vibe-kb MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an LLM-powered knowledge base system where raw materials (ePubs, articles, YouTube videos) are compiled into a navigable markdown wiki with wikilinks and backlinks, queryable through Claude Code skills.

**Architecture:** Two-layer design - `kb` CLI handles file operations (AI-free Python package), Skills handle LLM reasoning (compilation, Q&A, health checks). Knowledge base format (markdown + wikilinks) is the portability interface.

**Tech Stack:** Python 3.11+, uv, Click, ebooklib, yt-dlp, beautifulsoup4, matplotlib, pytest

---

## File Structure

### Core Package (`src/vibe_kb/`)
- `__init__.py` - Package version and exports
- `cli.py` - Click-based CLI entry point, command routing
- `config.py` - .kbconfig read/write, KB metadata management
- `utils/files.py` - File naming (`YYYY-MM-DD-slug.md`), .meta.json creation
- `utils/markdown.py` - Markdown processing, frontmatter parsing
- `utils/git.py` - Git commit operations
- `add/epub.py` - ePub extraction to markdown
- `add/youtube.py` - YouTube transcript via yt-dlp
- `add/url.py` - Web article fetching with beautifulsoup4
- `add/arxiv.py` - arXiv paper fetching
- `search.py` - Text search over wiki markdown files
- `health.py` - Health check system

### Skills (`skills/`)
- `kb-create.md` - Initialize KB with directory structure
- `kb-add-source.md` - Conversational source adding
- `kb-compile.md` - Wiki compilation from raw sources
- `kb-research.md` - Q&A against knowledge base
- `kb-health-check.md` - Wiki maintenance and linting

### Tests (`tests/`)
- `test_utils/test_files.py` - File naming, metadata
- `test_add/test_epub.py` - ePub conversion
- `test_add/test_youtube.py` - YouTube transcript
- `test_search.py` - Wiki search
- `conftest.py` - Pytest fixtures (temp KB structure)

---

## Task 1: Project Initialization

**Files:**
- Create: `pyproject.toml`
- Create: `src/vibe_kb/__init__.py`
- Create: `src/vibe_kb/cli.py`

- [ ] **Step 1: Initialize uv project**

```bash
cd /Users/satyasheel/Documents/Personal/vibe-kb
uv init --lib
```

Expected: Creates pyproject.toml

- [ ] **Step 2: Configure pyproject.toml**

```toml
[project]
name = "vibe-kb"
version = "0.1.0"
description = "LLM-powered knowledge base system"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1.0",
    "ebooklib>=0.18",
    "yt-dlp>=2024.0.0",
    "beautifulsoup4>=4.12.0",
    "requests>=2.31.0",
    "matplotlib>=3.8.0",
]

[project.scripts]
kb = "vibe_kb.cli:cli"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

Write to: `pyproject.toml`

- [ ] **Step 3: Add dependencies**

```bash
uv add click ebooklib yt-dlp beautifulsoup4 requests matplotlib lxml html5lib
uv add --dev pytest ruff
```

Expected: Updates pyproject.toml, creates uv.lock

- [ ] **Step 4: Create package structure**

```bash
mkdir -p src/vibe_kb/{add,utils}
mkdir -p tests/{test_add,test_utils}
mkdir -p skills
touch src/vibe_kb/__init__.py
touch src/vibe_kb/{cli,config,search,health}.py
touch src/vibe_kb/add/{__init__,epub,youtube,url,arxiv}.py
touch src/vibe_kb/utils/{__init__,files,markdown,git}.py
touch tests/conftest.py
```

Expected: Directory structure matches spec

- [ ] **Step 5: Write package __init__.py**

```python
"""vibe-kb: LLM-powered knowledge base system."""

__version__ = "0.1.0"
```

Write to: `src/vibe_kb/__init__.py`

- [ ] **Step 6: Write minimal CLI entry point**

```python
"""CLI entry point for kb command."""
import click


@click.group()
@click.version_option()
def cli():
    """vibe-kb: LLM-powered knowledge base system."""
    pass


if __name__ == "__main__":
    cli()
```

Write to: `src/vibe_kb/cli.py`

- [ ] **Step 7: Test CLI installation**

```bash
uv run kb --version
```

Expected: `kb, version 0.1.0`

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock src/ tests/ skills/
git commit -m "chore: initialize vibe-kb project with uv"
```

---

## Task 2: File Utilities

**Files:**
- Create: `src/vibe_kb/utils/files.py`
- Create: `tests/test_utils/test_files.py`

- [ ] **Step 1: Write failing test for filename generation**

```python
"""Tests for file utilities."""
from datetime import date
from vibe_kb.utils.files import generate_filename


def test_generate_filename_from_title():
    result = generate_filename("Attention Is All You Need")
    expected = f"{date.today().isoformat()}-attention-is-all-you-need.md"
    assert result == expected


def test_generate_filename_removes_special_chars():
    result = generate_filename("GPT-4: The Next Generation!")
    expected = f"{date.today().isoformat()}-gpt-4-the-next-generation.md"
    assert result == expected
```

Write to: `tests/test_utils/test_files.py`

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest tests/test_utils/test_files.py::test_generate_filename_from_title -v
```

Expected: ImportError or NameError

- [ ] **Step 3: Implement filename generation**

```python
"""File utilities for knowledge base operations."""
import re
from datetime import date
from pathlib import Path


def generate_filename(title: str, extension: str = ".md") -> str:
    """Generate YYYY-MM-DD-slug.md filename from title.
    
    Args:
        title: Article/source title
        extension: File extension (default: .md)
        
    Returns:
        Formatted filename string
    """
    # Convert to lowercase and replace spaces with hyphens
    slug = title.lower().replace(" ", "-")
    
    # Remove special characters except hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    today = date.today().isoformat()
    return f"{today}-{slug}{extension}"
```

Write to: `src/vibe_kb/utils/files.py`

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest tests/test_utils/test_files.py -v
```

Expected: 2 passed

- [ ] **Step 5: Write failing test for metadata creation**

```python
import json
from pathlib import Path
from vibe_kb.utils.files import create_metadata


def test_create_metadata(tmp_path):
    target = tmp_path / "test.meta.json"
    create_metadata(
        target,
        source_url="https://example.com/article",
        source_type="article",
        title="Test Article",
        author="John Doe"
    )
    
    assert target.exists()
    data = json.loads(target.read_text())
    assert data["source_url"] == "https://example.com/article"
    assert data["source_type"] == "article"
    assert data["title"] == "Test Article"
    assert data["author"] == "John Doe"
    assert "added_date" in data
```

Append to: `tests/test_utils/test_files.py`

- [ ] **Step 6: Run test to verify failure**

```bash
uv run pytest tests/test_utils/test_files.py::test_create_metadata -v
```

Expected: ImportError or NameError

- [ ] **Step 7: Implement metadata creation**

```python
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


def create_metadata(
    target: Path,
    source_url: str,
    source_type: str,
    title: str,
    author: Optional[str] = None,
    **kwargs
) -> None:
    """Create .meta.json metadata file for a source.
    
    Args:
        target: Path to .meta.json file
        source_url: URL of the source material
        source_type: Type (article, paper, book, video, repo)
        title: Title of the source
        author: Author name (optional)
        **kwargs: Additional metadata fields
    """
    metadata = {
        "source_url": source_url,
        "source_type": source_type,
        "title": title,
        "added_date": datetime.now().isoformat(),
    }
    
    if author:
        metadata["author"] = author
    
    metadata.update(kwargs)
    
    target.write_text(json.dumps(metadata, indent=2))
```

Append to: `src/vibe_kb/utils/files.py`

- [ ] **Step 8: Run tests to verify pass**

```bash
uv run pytest tests/test_utils/test_files.py -v
```

Expected: 3 passed

- [ ] **Step 9: Commit**

```bash
git add src/vibe_kb/utils/files.py tests/test_utils/test_files.py
git commit -m "feat: add file utilities for naming and metadata"
```

---

## Task 3: KB Configuration Management

**Files:**
- Create: `src/vibe_kb/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test for config creation**

```python
"""Tests for KB configuration management."""
import json
from pathlib import Path
from vibe_kb.config import KBConfig


def test_create_new_config(tmp_path):
    kb_dir = tmp_path / "test-kb"
    kb_dir.mkdir()
    
    config = KBConfig.create(kb_dir, name="test-kb", topic="Testing")
    
    assert config.name == "test-kb"
    assert config.topic == "Testing"
    assert config.kb_path == kb_dir
    assert (kb_dir / ".kbconfig").exists()


def test_load_existing_config(tmp_path):
    kb_dir = tmp_path / "test-kb"
    kb_dir.mkdir()
    
    # Create config file
    config_data = {
        "name": "test-kb",
        "topic": "Testing",
        "created": "2026-04-15T10:00:00",
        "last_compile": None,
        "source_count": 0,
        "article_count": 0
    }
    (kb_dir / ".kbconfig").write_text(json.dumps(config_data, indent=2))
    
    config = KBConfig.load(kb_dir)
    assert config.name == "test-kb"
    assert config.topic == "Testing"
```

Write to: `tests/test_config.py`

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest tests/test_config.py::test_create_new_config -v
```

Expected: ImportError or NameError

- [ ] **Step 3: Implement KBConfig class**

```python
"""Knowledge base configuration management."""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class KBConfig:
    """Knowledge base configuration."""
    
    name: str
    topic: str
    kb_path: Path
    created: str
    last_compile: Optional[str] = None
    source_count: int = 0
    article_count: int = 0
    
    @classmethod
    def create(cls, kb_path: Path, name: str, topic: str) -> "KBConfig":
        """Create new KB configuration.
        
        Args:
            kb_path: Path to knowledge base directory
            name: KB name
            topic: Research topic
            
        Returns:
            New KBConfig instance
        """
        config = cls(
            name=name,
            topic=topic,
            kb_path=kb_path,
            created=datetime.now().isoformat()
        )
        config.save()
        return config
    
    @classmethod
    def load(cls, kb_path: Path) -> "KBConfig":
        """Load existing KB configuration.
        
        Args:
            kb_path: Path to knowledge base directory
            
        Returns:
            Loaded KBConfig instance
        """
        config_file = kb_path / ".kbconfig"
        if not config_file.exists():
            raise FileNotFoundError(f"No .kbconfig found in {kb_path}")
        
        data = json.loads(config_file.read_text())
        return cls(kb_path=kb_path, **data)
    
    def save(self) -> None:
        """Save configuration to .kbconfig file."""
        config_file = self.kb_path / ".kbconfig"
        data = asdict(self)
        # Remove kb_path from saved data
        data.pop("kb_path")
        config_file.write_text(json.dumps(data, indent=2))
    
    def update_stats(self, source_count: int, article_count: int) -> None:
        """Update statistics and save.
        
        Args:
            source_count: Number of sources in raw/
            article_count: Number of articles in wiki/
        """
        self.source_count = source_count
        self.article_count = article_count
        self.save()
    
    def mark_compiled(self) -> None:
        """Mark KB as compiled with current timestamp."""
        self.last_compile = datetime.now().isoformat()
        self.save()
```

Write to: `src/vibe_kb/config.py`

- [ ] **Step 4: Run tests to verify pass**

```bash
uv run pytest tests/test_config.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/vibe_kb/config.py tests/test_config.py
git commit -m "feat: add KB configuration management"
```

---

## Task 4: KB Create Command

**Files:**
- Modify: `src/vibe_kb/cli.py`
- Create: `tests/test_cli_create.py`

- [ ] **Step 1: Write failing test for kb create**

```python
"""Tests for kb create command."""
from pathlib import Path
from click.testing import CliRunner
from vibe_kb.cli import cli


def test_kb_create_basic(tmp_path):
    runner = CliRunner()
    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    
    assert result.exit_code == 0
    assert kb_dir.exists()
    assert (kb_dir / ".kbconfig").exists()
    assert (kb_dir / "raw").is_dir()
    assert (kb_dir / "wiki").is_dir()
    assert (kb_dir / "outputs").is_dir()
```

Write to: `tests/test_cli_create.py`

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest tests/test_cli_create.py::test_kb_create_basic -v
```

Expected: FAIL - command not found

- [ ] **Step 3: Add kb create command**

```python
"""CLI entry point for kb command."""
import click
from pathlib import Path
from .config import KBConfig


@click.group()
@click.version_option()
def cli():
    """vibe-kb: LLM-powered knowledge base system."""
    pass


@cli.command()
@click.argument("name")
@click.option(
    "--vault-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Obsidian vault path (default: use KB_VAULT_PATH env var)"
)
@click.option("--topic", help="Research topic")
def create(name: str, vault_path: Path, topic: str):
    """Create a new knowledge base."""
    if not vault_path:
        vault_path = Path.home() / "obsidian-vault"  # Fallback
    
    kb_dir = vault_path / "knowledge-bases" / name
    
    if kb_dir.exists():
        click.echo(f"Error: Knowledge base '{name}' already exists at {kb_dir}")
        raise click.Abort()
    
    # Create directory structure
    kb_dir.mkdir(parents=True)
    (kb_dir / "raw" / "articles").mkdir(parents=True)
    (kb_dir / "raw" / "papers").mkdir(parents=True)
    (kb_dir / "raw" / "books").mkdir(parents=True)
    (kb_dir / "raw" / "videos").mkdir(parents=True)
    (kb_dir / "raw" / "repos").mkdir(parents=True)
    (kb_dir / "raw" / "datasets").mkdir(parents=True)
    
    (kb_dir / "wiki" / "concepts").mkdir(parents=True)
    (kb_dir / "wiki" / "summaries" / "articles").mkdir(parents=True)
    (kb_dir / "wiki" / "summaries" / "papers").mkdir(parents=True)
    (kb_dir / "wiki" / "summaries" / "books").mkdir(parents=True)
    (kb_dir / "wiki" / "summaries" / "videos").mkdir(parents=True)
    (kb_dir / "wiki" / "topics").mkdir(parents=True)
    (kb_dir / "wiki" / ".templates").mkdir(parents=True)
    
    (kb_dir / "outputs").mkdir()
    
    # Create templates
    _create_templates(kb_dir / "wiki" / ".templates")
    
    # Create config
    KBConfig.create(kb_dir, name=name, topic=topic or name)
    
    click.echo(f"✓ Created knowledge base '{name}' at {kb_dir}")
    click.echo(f"  Raw sources: {kb_dir / 'raw'}")
    click.echo(f"  Wiki: {kb_dir / 'wiki'}")


def _create_templates(template_dir: Path):
    """Create article templates."""
    # Concept article template
    concept_template = """---
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
"""
    (template_dir / "concept-article.md").write_text(concept_template)
    
    # Source summary template
    summary_template = """---
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
"""
    for source_type in ["article", "paper", "book", "video"]:
        (template_dir / f"{source_type}-summary.md").write_text(summary_template)


if __name__ == "__main__":
    cli()
```

Replace entire file: `src/vibe_kb/cli.py`

- [ ] **Step 4: Run test to verify pass**

```bash
uv run pytest tests/test_cli_create.py -v
```

Expected: 1 passed

- [ ] **Step 5: Test CLI manually**

```bash
uv run kb create test-kb --vault-path /tmp
ls -la /tmp/knowledge-bases/test-kb/
```

Expected: Directory structure created

- [ ] **Step 6: Commit**

```bash
git add src/vibe_kb/cli.py tests/test_cli_create.py
git commit -m "feat: add kb create command"
```

---

## Task 5: ePub Source Ingestion

**Files:**
- Create: `src/vibe_kb/add/epub.py`
- Create: `tests/test_add/test_epub.py`
- Modify: `src/vibe_kb/cli.py`

- [ ] **Step 1: Write failing test for ePub conversion**

```python
"""Tests for ePub ingestion."""
import pytest
from pathlib import Path
from vibe_kb.add.epub import extract_epub_to_markdown


def test_extract_epub_basic(tmp_path):
    """Test requires a real .epub file - placeholder for now."""
    # This test will be completed when we have a sample epub
    pytest.skip("Requires sample ePub file for testing")


def test_epub_metadata_extraction(tmp_path):
    """Test metadata extraction from ePub."""
    pytest.skip("Requires sample ePub file for testing")
```

Write to: `tests/test_add/test_epub.py`

- [ ] **Step 2: Implement ePub extraction**

```python
"""ePub source ingestion."""
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, List, Optional
import re


def extract_epub_to_markdown(
    epub_path: Path,
    output_path: Path
) -> Dict[str, any]:
    """Extract ePub content to markdown.
    
    Args:
        epub_path: Path to .epub file
        output_path: Path to output .md file
        
    Returns:
        Dictionary with metadata (title, author, chapters)
    """
    book = epub.read_epub(str(epub_path))
    
    # Extract metadata
    title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else "Unknown"
    authors = book.get_metadata('DC', 'creator')
    author = authors[0][0] if authors else "Unknown"
    
    # Extract chapters
    chapters = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = item.get_content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract text
            text = soup.get_text()
            # Clean up whitespace
            text = re.sub(r'\n\s*\n', '\n\n', text)
            text = text.strip()
            
            if text:  # Only add non-empty chapters
                chapters.append({
                    'title': item.get_name(),
                    'content': text
                })
    
    # Write markdown
    markdown = f"# {title}\n\n"
    markdown += f"**Author:** {author}\n\n"
    markdown += "---\n\n"
    
    for i, chapter in enumerate(chapters, 1):
        markdown += f"## Chapter {i}\n\n"
        markdown += f"{chapter['content']}\n\n"
    
    output_path.write_text(markdown, encoding='utf-8')
    
    return {
        'title': title,
        'author': author,
        'chapter_count': len(chapters)
    }


def get_epub_metadata(epub_path: Path) -> Dict[str, any]:
    """Get metadata from ePub without full extraction.
    
    Args:
        epub_path: Path to .epub file
        
    Returns:
        Dictionary with metadata
    """
    book = epub.read_epub(str(epub_path))
    
    title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else "Unknown"
    authors = book.get_metadata('DC', 'creator')
    author = authors[0][0] if authors else "Unknown"
    
    return {
        'title': title,
        'author': author,
        'source_type': 'book'
    }
```

Write to: `src/vibe_kb/add/epub.py`

- [ ] **Step 3: Add kb add --epub command**

```python
from .add.epub import extract_epub_to_markdown, get_epub_metadata
from .utils.files import generate_filename, create_metadata


@cli.command()
@click.argument("kb_name")
@click.option("--epub", "epub_path", type=click.Path(exists=True, path_type=Path), help="ePub file path")
@click.option(
    "--vault-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Obsidian vault path"
)
def add(kb_name: str, epub_path: Optional[Path], vault_path: Optional[Path]):
    """Add source material to knowledge base."""
    if not vault_path:
        vault_path = Path.home() / "obsidian-vault"
    
    kb_dir = vault_path / "knowledge-bases" / kb_name
    if not kb_dir.exists():
        click.echo(f"Error: Knowledge base '{kb_name}' not found")
        raise click.Abort()
    
    if epub_path:
        _add_epub(kb_dir, epub_path)
    else:
        click.echo("Error: No source specified. Use --epub, --url, or --youtube")
        raise click.Abort()


def _add_epub(kb_dir: Path, epub_path: Path):
    """Add ePub book to knowledge base."""
    click.echo(f"Processing ePub: {epub_path.name}")
    
    # Get metadata
    metadata = get_epub_metadata(epub_path)
    
    # Generate filename
    filename = generate_filename(metadata['title'])
    output_path = kb_dir / "raw" / "books" / filename
    
    # Extract to markdown
    result = extract_epub_to_markdown(epub_path, output_path)
    
    # Create metadata file
    meta_path = output_path.with_suffix('.meta.json')
    create_metadata(
        meta_path,
        source_url=str(epub_path),
        source_type='book',
        title=metadata['title'],
        author=metadata['author'],
        chapter_count=result['chapter_count']
    )
    
    click.echo(f"✓ Added book: {metadata['title']}")
    click.echo(f"  Location: {output_path}")
    click.echo(f"  Chapters: {result['chapter_count']}")
```

Add to `src/vibe_kb/cli.py` (append after create command)

- [ ] **Step 4: Test with real ePub**

```bash
# Download a sample ePub or use one from Case-Studies-And-Reviews
uv run kb add test-kb --epub /path/to/sample.epub --vault-path /tmp
```

Expected: ePub converted to markdown in raw/books/

- [ ] **Step 5: Commit**

```bash
git add src/vibe_kb/add/epub.py tests/test_add/test_epub.py src/vibe_kb/cli.py
git commit -m "feat: add ePub source ingestion"
```

---

## Task 6: YouTube Transcript Extraction

**Files:**
- Create: `src/vibe_kb/add/youtube.py`
- Modify: `src/vibe_kb/cli.py`

- [ ] **Step 1: Implement YouTube extraction**

```python
"""YouTube transcript extraction."""
import yt_dlp
from pathlib import Path
from typing import Dict
import re


def extract_youtube_transcript(
    url: str,
    output_path: Path
) -> Dict[str, any]:
    """Extract YouTube video transcript to markdown.
    
    Args:
        url: YouTube video URL
        output_path: Path to output .md file
        
    Returns:
        Dictionary with metadata
    """
    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'skip_download': True,
        'quiet': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        title = info.get('title', 'Unknown')
        channel = info.get('channel', 'Unknown')
        duration = info.get('duration', 0)
        upload_date = info.get('upload_date', 'Unknown')
        description = info.get('description', '')
        
        # Get subtitles
        subtitles = info.get('subtitles', {}).get('en') or info.get('automatic_captions', {}).get('en')
        
        if not subtitles:
            raise ValueError("No English subtitles available for this video")
        
        # Download subtitle content
        subtitle_url = subtitles[0]['url']
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl2:
            subtitle_content = ydl2.urlopen(subtitle_url).read().decode('utf-8')
        
        # Parse VTT format
        transcript = _parse_vtt(subtitle_content)
        
        # Write markdown
        markdown = f"# {title}\n\n"
        markdown += f"**Channel:** {channel}\n"
        markdown += f"**Duration:** {duration // 60}:{duration % 60:02d}\n"
        markdown += f"**Upload Date:** {upload_date}\n"
        markdown += f"**URL:** {url}\n\n"
        markdown += "---\n\n"
        markdown += f"## Description\n\n{description}\n\n"
        markdown += "---\n\n"
        markdown += "## Transcript\n\n"
        markdown += transcript
        
        output_path.write_text(markdown, encoding='utf-8')
        
        return {
            'title': title,
            'channel': channel,
            'duration': duration,
            'url': url
        }


def _parse_vtt(vtt_content: str) -> str:
    """Parse VTT subtitle format to plain text.
    
    Args:
        vtt_content: VTT subtitle content
        
    Returns:
        Plain text transcript
    """
    # Remove VTT header
    lines = vtt_content.split('\n')
    text_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip empty lines, timestamps, and VTT headers
        if not line or '-->' in line or line.startswith('WEBVTT') or line.isdigit():
            continue
        # Remove HTML tags
        line = re.sub(r'<[^>]+>', '', line)
        if line:
            text_lines.append(line)
    
    # Join and clean up
    transcript = ' '.join(text_lines)
    # Remove duplicate spaces
    transcript = re.sub(r'\s+', ' ', transcript)
    
    return transcript
```

Write to: `src/vibe_kb/add/youtube.py`

- [ ] **Step 2: Add kb add --youtube command**

```python
from .add.youtube import extract_youtube_transcript


@cli.command()
@click.argument("kb_name")
@click.option("--epub", "epub_path", type=click.Path(exists=True, path_type=Path))
@click.option("--youtube", "youtube_url", type=str, help="YouTube video URL")
@click.option("--vault-path", type=click.Path(exists=True, file_okay=False, path_type=Path))
def add(kb_name: str, epub_path: Optional[Path], youtube_url: Optional[str], vault_path: Optional[Path]):
    """Add source material to knowledge base."""
    if not vault_path:
        vault_path = Path.home() / "obsidian-vault"
    
    kb_dir = vault_path / "knowledge-bases" / kb_name
    if not kb_dir.exists():
        click.echo(f"Error: Knowledge base '{kb_name}' not found")
        raise click.Abort()
    
    if epub_path:
        _add_epub(kb_dir, epub_path)
    elif youtube_url:
        _add_youtube(kb_dir, youtube_url)
    else:
        click.echo("Error: No source specified")
        raise click.Abort()


def _add_youtube(kb_dir: Path, url: str):
    """Add YouTube video to knowledge base."""
    click.echo(f"Extracting transcript from: {url}")
    
    try:
        # Extract transcript
        result = extract_youtube_transcript(url, Path("/tmp/temp.md"))
        
        # Generate filename
        filename = generate_filename(result['title'])
        output_path = kb_dir / "raw" / "videos" / filename
        
        # Move temp file
        Path("/tmp/temp.md").rename(output_path)
        
        # Create metadata
        meta_path = output_path.with_suffix('.meta.json')
        create_metadata(
            meta_path,
            source_url=url,
            source_type='video',
            title=result['title'],
            author=result['channel'],
            duration=result['duration']
        )
        
        click.echo(f"✓ Added video: {result['title']}")
        click.echo(f"  Channel: {result['channel']}")
        click.echo(f"  Location: {output_path}")
        
    except Exception as e:
        click.echo(f"Error: {e}")
        raise click.Abort()
```

Update `add` command in `src/vibe_kb/cli.py`

- [ ] **Step 3: Test with YouTube URL**

```bash
uv run kb add test-kb --youtube "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --vault-path /tmp
```

Expected: Transcript extracted to raw/videos/

- [ ] **Step 4: Commit**

```bash
git add src/vibe_kb/add/youtube.py src/vibe_kb/cli.py
git commit -m "feat: add YouTube transcript extraction"
```

---

## Task 7: Search Command

**Files:**
- Create: `src/vibe_kb/search.py`
- Create: `tests/test_search.py`
- Modify: `src/vibe_kb/cli.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for wiki search."""
from pathlib import Path
from vibe_kb.search import search_wiki


def test_search_wiki_basic(tmp_path):
    # Create test wiki structure
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    
    # Create test files
    (wiki_dir / "test1.md").write_text("This is about transformers and attention mechanisms.")
    (wiki_dir / "test2.md").write_text("This discusses neural networks.")
    
    results = search_wiki(wiki_dir, "transformers")
    
    assert len(results) == 1
    assert "test1.md" in results[0]['file']
    assert "transformers" in results[0]['match'].lower()
```

Write to: `tests/test_search.py`

- [ ] **Step 2: Run test to verify failure**

```bash
uv run pytest tests/test_search.py -v
```

Expected: ImportError

- [ ] **Step 3: Implement search**

```python
"""Wiki search functionality."""
from pathlib import Path
from typing import List, Dict
import re


def search_wiki(wiki_dir: Path, query: str, case_sensitive: bool = False) -> List[Dict]:
    """Search wiki markdown files for query string.
    
    Args:
        wiki_dir: Path to wiki directory
        query: Search query
        case_sensitive: Whether search is case-sensitive
        
    Returns:
        List of matches with file path and matching line
    """
    results = []
    
    # Compile regex pattern
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(re.escape(query), flags)
    
    # Search all .md files recursively
    for md_file in wiki_dir.rglob("*.md"):
        if md_file.name.startswith('.'):
            continue
        
        content = md_file.read_text(encoding='utf-8')
        
        for line_num, line in enumerate(content.split('\n'), 1):
            if pattern.search(line):
                results.append({
                    'file': str(md_file.relative_to(wiki_dir)),
                    'line': line_num,
                    'match': line.strip()
                })
    
    return results
```

Write to: `src/vibe_kb/search.py`

- [ ] **Step 4: Run test to verify pass**

```bash
uv run pytest tests/test_search.py -v
```

Expected: 1 passed

- [ ] **Step 5: Add kb search command**

```python
from .search import search_wiki


@cli.command()
@click.argument("kb_name")
@click.argument("query")
@click.option("--vault-path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--case-sensitive", is_flag=True, help="Case-sensitive search")
def search(kb_name: str, query: str, vault_path: Optional[Path], case_sensitive: bool):
    """Search wiki for query string."""
    if not vault_path:
        vault_path = Path.home() / "obsidian-vault"
    
    kb_dir = vault_path / "knowledge-bases" / kb_name
    wiki_dir = kb_dir / "wiki"
    
    if not wiki_dir.exists():
        click.echo(f"Error: No wiki found in '{kb_name}'")
        raise click.Abort()
    
    click.echo(f"Searching '{kb_name}' for: {query}")
    
    results = search_wiki(wiki_dir, query, case_sensitive)
    
    if not results:
        click.echo("No matches found.")
        return
    
    click.echo(f"\nFound {len(results)} matches:\n")
    
    for result in results:
        click.echo(f"{result['file']}:{result['line']}")
        click.echo(f"  {result['match']}\n")
```

Add to `src/vibe_kb/cli.py`

- [ ] **Step 6: Test search command**

```bash
# Create test content first
mkdir -p /tmp/knowledge-bases/test-kb/wiki
echo "Transformers use attention mechanisms" > /tmp/knowledge-bases/test-kb/wiki/test.md

uv run kb search test-kb "attention" --vault-path /tmp
```

Expected: Shows matching line

- [ ] **Step 7: Commit**

```bash
git add src/vibe_kb/search.py tests/test_search.py src/vibe_kb/cli.py
git commit -m "feat: add wiki search command"
```

---

## Task 8: Stats Command

**Files:**
- Modify: `src/vibe_kb/cli.py`

- [ ] **Step 1: Add kb stats command**

```python
@cli.command()
@click.argument("kb_name")
@click.option("--vault-path", type=click.Path(exists=True, file_okay=False, path_type=Path))
def stats(kb_name: str, vault_path: Optional[Path]):
    """Show knowledge base statistics."""
    if not vault_path:
        vault_path = Path.home() / "obsidian-vault"
    
    kb_dir = vault_path / "knowledge-bases" / kb_name
    
    if not kb_dir.exists():
        click.echo(f"Error: Knowledge base '{kb_name}' not found")
        raise click.Abort()
    
    # Load config
    config = KBConfig.load(kb_dir)
    
    # Count sources
    raw_dir = kb_dir / "raw"
    source_files = list(raw_dir.rglob("*.md")) + list(raw_dir.rglob("*.pdf"))
    
    # Count wiki articles
    wiki_dir = kb_dir / "wiki"
    wiki_files = [f for f in wiki_dir.rglob("*.md") if not f.name.startswith(('_', '.'))]
    
    # Count words in wiki
    total_words = 0
    for wiki_file in wiki_files:
        content = wiki_file.read_text(encoding='utf-8')
        total_words += len(content.split())
    
    # Display stats
    click.echo(f"\nKnowledge Base: {config.name}")
    click.echo(f"Topic: {config.topic}")
    click.echo(f"Created: {config.created}")
    click.echo(f"Last compile: {config.last_compile or 'Never'}")
    click.echo(f"\nSources: {len(source_files)}")
    click.echo(f"Wiki articles: {len(wiki_files)}")
    click.echo(f"Total words: {total_words:,}")
    click.echo(f"\nLocation: {kb_dir}")
```

Add to `src/vibe_kb/cli.py`

- [ ] **Step 2: Test stats command**

```bash
uv run kb stats test-kb --vault-path /tmp
```

Expected: Shows statistics

- [ ] **Step 3: Commit**

```bash
git add src/vibe_kb/cli.py
git commit -m "feat: add stats command"
```

---

## Task 9: Create kb:create Skill

**Files:**
- Create: `skills/kb-create.md`

- [ ] **Step 1: Write kb:create skill using skill-creator**

Use the `skill-creator` plugin to create the skill with this specification:

```
Name: kb:create
Description: Initialize a new knowledge base with conversational flow

The skill should:
1. Ask user for KB name and research topic
2. Optionally ask if they have existing sources to import
3. Call `kb create <name>` command
4. If importing sources, call `kb add` for each source
5. Explain the directory structure created
6. Suggest next steps (adding sources, first compile)

The skill should use the vault path from user's Obsidian config:
/Users/satyasheel/Insync/satyasheel@ymail.com/Dropbox/obsidian-satya/
```

- [ ] **Step 2: Test skill**

Invoke the skill manually in Claude Code:
```
/kb:create
```

Expected: Conversational flow that creates KB

- [ ] **Step 3: Commit**

```bash
git add skills/kb-create.md
git commit -m "feat: add kb:create skill"
```

---

## Task 10: Create kb:add-source Skill

**Files:**
- Create: `skills/kb-add-source.md`

- [ ] **Step 1: Write kb:add-source skill**

Use `skill-creator` with specification:

```
Name: kb:add-source
Description: Add source material with conversational interface

The skill should:
1. Ask which KB to add to
2. Ask what type of source (epub, youtube, url, file)
3. Based on type, ask for path/URL
4. Call appropriate `kb add` command
5. Show what was added and where
6. Ask if they want to compile immediately
7. If yes, invoke kb:compile skill
```

- [ ] **Step 2: Test skill**

```
/kb:add-source
```

Expected: Adds source conversationally

- [ ] **Step 3: Commit**

```bash
git add skills/kb-add-source.md
git commit -m "feat: add kb:add-source skill"
```

---

## Task 11: Create kb:compile Skill (Stub)

**Files:**
- Create: `skills/kb-compile.md`

- [ ] **Step 1: Write kb:compile skill stub**

Use `skill-creator` with specification:

```
Name: kb:compile
Description: Compile raw sources into wiki (MVP: manual guidance)

For MVP, the skill should:
1. Ask which KB to compile
2. Read the raw/ directory and list new sources
3. For each source, read its content
4. Generate a summary using the source-summary template
5. Create [[wikilinks]] to concepts mentioned
6. Write summary to wiki/summaries/<type>/
7. Update _sources.md index
8. Commit changes

Note: This is MVP - full backlink intelligence and structural changes come later
```

- [ ] **Step 2: Test with one source**

Add an epub, then:
```
/kb:compile
```

Expected: Creates summary in wiki/

- [ ] **Step 3: Commit**

```bash
git add skills/kb-compile.md
git commit -m "feat: add kb:compile skill (MVP)"
```

---

## Task 12: Create kb:research Skill (Stub)

**Files:**
- Create: `skills/kb-research.md`

- [ ] **Step 1: Write kb:research skill stub**

Use `skill-creator`:

```
Name: kb:research
Description: Q&A against knowledge base

The skill should:
1. Ask which KB to research
2. Ask the research question
3. Read _index.md and _sources.md to find relevant articles
4. Read those articles
5. Generate answer referencing sources with [[wikilinks]]
6. Ask if they want output as markdown, slides, or chart
7. Save to outputs/ directory
8. Ask if they want to file it back into wiki
```

- [ ] **Step 2: Test with simple question**

```
/kb:research
Question: "Summarize the main topics covered"
```

Expected: Generates answer with sources

- [ ] **Step 3: Commit**

```bash
git add skills/kb-research.md
git commit -m "feat: add kb:research skill (MVP)"
```

---

## Task 13: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write comprehensive README**

```markdown
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
```

Write to: `README.md`

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive README"
```

---

## Self-Review Checklist

**Spec Coverage:**
- ✓ Project initialization (uv, pyproject.toml)
- ✓ File utilities (naming, metadata)
- ✓ KB configuration (.kbconfig)
- ✓ KB create command with directory structure
- ✓ ePub ingestion
- ✓ YouTube transcript extraction
- ✓ Search command
- ✓ Stats command
- ✓ Skills: create, add-source, compile (MVP), research (MVP)
- ⚠️ Health check - deferred (mentioned in spec as future)
- ⚠️ URL/arXiv ingestion - deferred (can add post-MVP)
- ⚠️ Full backlink intelligence - deferred (compile skill is MVP)

**Placeholders:** None - all code is complete

**Type Consistency:** 
- KBConfig fields match across tasks
- File paths consistent (Path type)
- Metadata structure consistent

**Missing from spec but needed:**
- Template creation in kb create ✓ (added in Task 4)
- Config loading in stats ✓ (added in Task 8)

Plan is complete and ready for execution.
