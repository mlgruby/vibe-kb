"""CLI entry point for kb command."""

import click
import re
import tempfile
from pathlib import Path
from typing import Optional
from .config import KBConfig
from .add.epub import extract_epub_to_markdown, extract_epub_to_chapters, get_epub_metadata
from .add.youtube import extract_youtube_transcript
from .add.url import fetch_url_to_markdown
from .add.arxiv import search_arxiv, arxiv_to_markdown
from .utils.files import generate_filename, create_metadata
from .search import search_wiki

_KB_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def _validate_kb_name(name: str) -> None:
    """Validate KB name to prevent path traversal outside the vault namespace.

    Args:
        name: Knowledge base name to validate

    Raises:
        click.Abort: If name is invalid
    """
    if not _KB_NAME_RE.match(name):
        click.echo(
            f"Error: Invalid knowledge base name '{name}'. "
            "Names must start with a letter or digit and contain only "
            "letters, digits, hyphens, and underscores."
        )
        raise click.Abort()


@click.group()
@click.version_option()
def cli():
    """vibe-kb: LLM-powered knowledge base system."""
    pass


@cli.command()
@click.argument("name")
@click.option(
    "--vault-path",
    type=click.Path(file_okay=False, path_type=Path),
    help="Obsidian vault path (default: ~/obsidian-vault)",
)
@click.option("--topic", help="Research topic")
def create(name: str, vault_path: Optional[Path], topic: str):
    """Create a new knowledge base."""
    _validate_kb_name(name)

    if not vault_path:
        vault_path = Path.home() / "obsidian-vault"

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
    click.echo(f"  Wiki articles: {kb_dir / 'wiki'}")
    click.echo(f"  Outputs: {kb_dir / 'outputs'}")


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
    (template_dir / "concept-article.md").write_text(concept_template, encoding="utf-8")

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
        (template_dir / f"{source_type}-summary.md").write_text(summary_template, encoding="utf-8")


@cli.command()
@click.argument("kb_name")
@click.option(
    "--epub", "epub_path", type=click.Path(exists=True, path_type=Path), help="ePub file path"
)
@click.option("--split-chapters", is_flag=True, help="Split ePub into separate chapter files")
@click.option("--youtube", "youtube_url", type=str, help="YouTube video URL")
@click.option("--url", "article_url", type=str, help="Web article URL")
@click.option("--arxiv", "arxiv_query", type=str, help="arXiv search query")
@click.option("--limit", default=10, type=int, help="Maximum number of arXiv papers (default: 10)")
@click.option(
    "--vault-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Obsidian vault path",
)
def add(
    kb_name: str,
    epub_path: Optional[Path],
    split_chapters: bool,
    youtube_url: Optional[str],
    article_url: Optional[str],
    arxiv_query: Optional[str],
    limit: int,
    vault_path: Optional[Path],
):
    """Add source material to knowledge base."""
    _validate_kb_name(kb_name)

    if not vault_path:
        vault_path = Path.home() / "obsidian-vault"

    kb_dir = vault_path / "knowledge-bases" / kb_name
    if not kb_dir.exists():
        click.echo(f"Error: Knowledge base '{kb_name}' not found")
        raise click.Abort()

    if epub_path:
        _add_epub(kb_dir, epub_path, split_chapters)
    elif youtube_url:
        _add_youtube(kb_dir, youtube_url)
    elif article_url:
        _add_url(kb_dir, article_url)
    elif arxiv_query:
        _add_arxiv(kb_dir, arxiv_query, limit)
    else:
        click.echo("Error: No source specified. Use --epub, --url, --youtube, or --arxiv")
        raise click.Abort()


def _add_epub(kb_dir: Path, epub_path: Path, split_chapters: bool = False):
    """Add ePub book to knowledge base.

    Transactional guarantee: if metadata creation fails after the markdown
    has been written (e.g. disk-full, permission error), the partially-written
    .md file is removed so a subsequent retry can succeed cleanly.
    Without this cleanup the existing-source guard would block the retry,
    leaving the KB in a broken state requiring manual file deletion.

    Note (TOCTOU): there is a theoretical time-of-check/time-of-use race
    between the exists() check and the write — a second concurrent process
    could create the same destination file in the milliseconds between them.
    For a personal single-user CLI this risk is negligible and not mitigated.

    Args:
        kb_dir: Knowledge base directory
        epub_path: Path to ePub file
        split_chapters: If True, split into directory with separate chapter files
    """
    if epub_path.suffix.lower() != ".epub":
        click.echo(f"Error: '{epub_path.name}' is not an .epub file")
        raise click.Abort()

    click.echo(f"Processing ePub: {epub_path.name}")

    try:
        metadata = get_epub_metadata(epub_path)
    except ValueError as e:
        click.echo(f"Error: {str(e)}")
        raise click.Abort()

    filename = generate_filename(metadata["title"])

    if split_chapters:
        # Create directory for book with chapters
        output_dir = kb_dir / "raw" / "books" / filename.replace(".md", "")

        if output_dir.exists():
            click.echo(f"Error: Source already exists at {output_dir}")
            click.echo("Remove the existing directory first if you want to replace it.")
            raise click.Abort()

        try:
            result = extract_epub_to_chapters(epub_path, output_dir)

            # Create metadata file in the book directory (use .meta.json convention)
            meta_path = output_dir / "index.meta.json"
            create_metadata(
                meta_path,
                source_url=str(epub_path),
                source_type="book",
                title=metadata["title"],
                author=metadata["author"],
                chapter_count=result["chapter_count"],
                images_extracted=result["images_extracted"],
            )
        except Exception as e:
            # Roll back the entire directory on failure
            if output_dir.exists():
                import shutil

                shutil.rmtree(output_dir)
            click.echo(f"Error: {str(e)}")
            raise click.Abort()

        click.echo(f"✓ Added book: {metadata['title']} ({result['chapter_count']} chapters)")
        click.echo(f"  Location: {output_dir}")
        click.echo(f"  Images: {result['images_extracted']}")

    else:
        # Original single-file behavior
        output_path = kb_dir / "raw" / "books" / filename

        if output_path.exists():
            click.echo(f"Error: Source already exists at {output_path}")
            click.echo("Remove the existing file first if you want to replace it.")
            raise click.Abort()

        output_created = False
        try:
            result = extract_epub_to_markdown(epub_path, output_path)
            output_created = True  # markdown written — track for cleanup on failure

            meta_path = output_path.with_suffix(".meta.json")
            create_metadata(
                meta_path,
                source_url=str(epub_path),
                source_type="book",
                title=metadata["title"],
                author=metadata["author"],
                chapter_count=result["chapter_count"],
                images_extracted=result.get("images_extracted", 0),
            )
        except Exception as e:
            # Roll back both the markdown file and any partial .meta.json
            # so a retry is not blocked by the "already exists" guard.
            if output_created and output_path.exists():
                output_path.unlink()
                meta_path = output_path.with_suffix(".meta.json")
                if meta_path.exists():
                    meta_path.unlink()
            click.echo(f"Error: {str(e)}")
            raise click.Abort()

        click.echo(f"✓ Added book: {metadata['title']}")
        click.echo(f"  Location: {output_path}")
        click.echo(f"  Chapters: {result['chapter_count']}")


def _add_youtube(kb_dir: Path, url: str):
    """Add YouTube video to knowledge base."""
    # Validate URL format: must be HTTPS and a known YouTube host
    from urllib.parse import urlparse

    parsed = urlparse(url)
    allowed_hosts = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        click.echo(
            "Error: Invalid YouTube URL. Must be https://youtube.com/... or https://youtu.be/..."
        )
        raise click.Abort()

    click.echo(f"Extracting transcript from: {url}")

    temp_path = None
    output_path = None
    output_created_by_us = False  # track whether we created output_path

    try:
        # Generate filename from URL metadata first to check for duplicates
        # before doing any network extraction
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tmp:
            temp_path = Path(tmp.name)

        # Extract transcript
        result = extract_youtube_transcript(url, temp_path)

        # Generate filename
        filename = generate_filename(result["title"])
        output_path = kb_dir / "raw" / "videos" / filename

        # Check for existing source to prevent silent overwrite
        if output_path.exists():
            click.echo(f"Error: Source already exists at {output_path}")
            click.echo("Remove the existing file first if you want to replace it.")
            raise click.Abort()

        # Move temp file to final location (we now own output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.rename(output_path)
        temp_path = None  # successfully moved, don't delete
        output_created_by_us = True  # we created it — safe to clean on failure

        # Create metadata
        meta_path = output_path.with_suffix(".meta.json")
        create_metadata(
            meta_path,
            source_url=url,
            source_type="video",
            title=result["title"],
            author=result["channel"],
            duration=result["duration"],
        )

        click.echo(f"✓ Added video: {result['title']}")
        click.echo(f"  Channel: {result['channel']}")
        click.echo(f"  Location: {output_path}")

    except click.Abort:
        # Duplicate-exists abort: only clean up temp, never touch output_path
        if temp_path and temp_path.exists():
            temp_path.unlink()
        raise
    except Exception as e:
        # Clean up temp file if still present
        if temp_path and temp_path.exists():
            temp_path.unlink()

        # Only clean up output_path if WE created it this invocation
        if output_created_by_us and output_path and output_path.exists():
            output_path.unlink()
            meta_path = output_path.with_suffix(".meta.json")
            if meta_path.exists():
                meta_path.unlink()

        click.echo(f"Error: {str(e)}")
        raise click.Abort()


def _add_url(kb_dir: Path, url: str):
    """Add a web article to knowledge base.

    Transactional guarantee: if metadata creation fails after the markdown
    has been written, the partially-written .md file is removed so a
    subsequent retry can succeed cleanly.
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        click.echo(
            f"Error: Invalid URL scheme '{parsed.scheme}'. Only http and https URLs are supported."
        )
        raise click.Abort()

    click.echo(f"Fetching article: {url}")

    output_created = False
    output_path = None
    temp_path = None  # track for cleanup on early failure

    try:
        # Perform the actual fetch (title-based filename determined after fetch)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tmp:
            temp_path = Path(tmp.name)

        result = fetch_url_to_markdown(url, temp_path)

        # Generate final filename from actual title
        filename = generate_filename(result["title"])
        output_path = kb_dir / "raw" / "articles" / filename

        if output_path.exists():
            temp_path.unlink(missing_ok=True)
            click.echo(f"Error: Source already exists at {output_path}")
            click.echo("Remove the existing file first if you want to replace it.")
            raise click.Abort()

        # Move temp file to final location
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save temp images directory path and stem before renaming markdown
        temp_stem = temp_path.stem
        temp_images_dir = temp_path.parent / f"{temp_stem}_images"

        temp_path.rename(output_path)
        temp_path = None  # successfully moved
        output_created = True

        # Move images directory if it was created during fetch
        if temp_images_dir.exists():
            final_images_dir = output_path.parent / f"{output_path.stem}_images"
            temp_images_dir.rename(final_images_dir)

            # Update image paths in markdown from temp stem to final stem
            content = output_path.read_text(encoding="utf-8")
            content = content.replace(f"{temp_stem}_images/", f"{output_path.stem}_images/")
            output_path.write_text(content, encoding="utf-8")

        # Create metadata
        meta_path = output_path.with_suffix(".meta.json")
        create_metadata(
            meta_path,
            source_url=url,
            source_type="article",
            title=result["title"],
            author=result["author"],
            domain=result["domain"],
        )

        click.echo(f"✓ Added article: {result['title']}")
        click.echo(f"  Source: {result['domain']}")
        click.echo(f"  Location: {output_path}")

    except click.Abort:
        # Duplicate-exists abort: clean up temp only, never touch output_path
        if temp_path and temp_path.exists():
            temp_path.unlink()
        raise
    except Exception as e:
        # Clean up temp file if fetch failed before the rename
        if temp_path and temp_path.exists():
            temp_path.unlink()
        # Roll back output if we created it but metadata failed
        if output_created and output_path and output_path.exists():
            output_path.unlink()
            meta_path = output_path.with_suffix(".meta.json")
            if meta_path.exists():
                meta_path.unlink()
        click.echo(f"Error: {str(e)}")
        raise click.Abort()


def _add_arxiv(kb_dir: Path, query: str, limit: int):
    """Add arXiv papers to knowledge base.

    Searches arXiv for papers matching query and converts them to markdown
    using MarkItDown (HTML preferred, PDF fallback).
    """
    click.echo(f"Searching arXiv for: {query}")

    try:
        results = search_arxiv(query, limit=limit)

        if not results:
            click.echo("No papers found matching query")
            return

        click.echo(f"Found {len(results)} paper(s)\n")

        for i, paper in enumerate(results, 1):
            click.echo(f"[{i}/{len(results)}] Processing: {paper['title'][:80]}...")

            # Generate filename
            filename = generate_filename(paper["title"])
            output_path = kb_dir / "raw" / "papers" / filename

            # Check if already exists
            if output_path.exists():
                click.echo("  ⊘ Skipped (already exists)")
                continue

            # Convert to markdown
            result = arxiv_to_markdown(paper["arxiv_id"], output_path)

            if result["success"]:
                # Create metadata
                meta_path = output_path.with_suffix(".meta.json")
                create_metadata(
                    meta_path,
                    source_url=f"https://arxiv.org/abs/{paper['arxiv_id']}",
                    source_type="paper",
                    title=paper["title"],
                    author=", ".join(paper["authors"]),
                    arxiv_id=paper["arxiv_id"],
                    format=result["format"],
                )

                click.echo(f"  ✓ Added ({result['format']} format)")
            else:
                click.echo(f"  ✗ Failed: {result.get('error', 'Unknown error')}")

        click.echo(f"\n✓ Processed {len(results)} papers")

    except Exception as e:
        click.echo(f"Error: {str(e)}")
        raise click.Abort()


@cli.command()
@click.argument("kb_name")
@click.argument("query")
@click.option("--vault-path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--case-sensitive", is_flag=True, help="Case-sensitive search")
def search(kb_name: str, query: str, vault_path: Optional[Path], case_sensitive: bool):
    """Search wiki for query string."""
    _validate_kb_name(kb_name)

    if not vault_path:
        vault_path = Path.home() / "obsidian-vault"

    kb_dir = vault_path / "knowledge-bases" / kb_name
    wiki_dir = kb_dir / "wiki"

    if not wiki_dir.exists():
        click.echo(f"Error: No wiki found in '{kb_name}'")
        raise click.Abort()

    click.echo(f"Searching '{kb_name}' for: {query}")

    try:
        results = search_wiki(wiki_dir, query, case_sensitive)
    except ValueError as e:
        click.echo(f"Error: {str(e)}")
        raise click.Abort()

    if not results:
        click.echo("No matches found.")
        return

    click.echo(f"\nFound {len(results)} match{'es' if len(results) != 1 else ''}:\n")

    for result in results:
        click.echo(f"{result['file']}:{result['line']}")
        click.echo(f"  {result['match']}\n")


def _is_excluded_wiki_file(path: Path, base_dir: Path) -> bool:
    """Check if wiki file should be excluded from article count.

    Files are excluded if:
    - File is a symlink (security: prevents path traversal)
    - Filename starts with '_' or '.'
    - Any parent directory name starts with '_' or '.'

    Args:
        path: File path to check
        base_dir: Base wiki directory

    Returns:
        True if file should be excluded
    """
    # Security: skip symlinks to prevent path traversal vulnerability
    if path.is_symlink():
        return True

    # Skip files starting with _ or .
    if path.name.startswith(("_", ".")):
        return True

    # Check parent directories for _ or . prefix
    try:
        relative = path.relative_to(base_dir)
        for parent in relative.parents:
            if parent != Path(".") and parent.name.startswith(("_", ".")):
                return True
    except ValueError:
        # Path is outside base_dir
        return True

    return False


@cli.command()
@click.argument("kb_name")
@click.option("--vault-path", type=click.Path(exists=True, file_okay=False, path_type=Path))
def stats(kb_name: str, vault_path: Optional[Path]):
    """Show knowledge base statistics.

    Displays KB metadata, source counts, wiki article counts, and total word count.

    Args:
        kb_name: Name of the knowledge base
        vault_path: Optional vault path (defaults to ~/obsidian-vault)
    """
    _validate_kb_name(kb_name)

    if not vault_path:
        vault_path = Path.home() / "obsidian-vault"

    kb_dir = vault_path / "knowledge-bases" / kb_name

    if not kb_dir.exists():
        click.echo(f"Error: Knowledge base '{kb_name}' not found")
        raise click.Abort()

    # Load config
    try:
        config = KBConfig.load(kb_dir)
    except FileNotFoundError as e:
        click.echo(f"Error: {str(e)}")
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error: Failed to load config: {str(e)}")
        raise click.Abort()

    # Count sources (skip symlinks for security)
    raw_dir = kb_dir / "raw"
    source_files = []
    if raw_dir.exists():
        for pattern in ["*.md", "*.pdf"]:
            for f in raw_dir.rglob(pattern):
                if not f.is_symlink():
                    source_files.append(f)

    # Count wiki articles and words (exclude templates, hidden files, symlinks, binary files)
    wiki_dir = kb_dir / "wiki"
    wiki_files = []
    total_words = 0
    if wiki_dir.exists():
        for md_file in wiki_dir.rglob("*.md"):
            if not _is_excluded_wiki_file(md_file, wiki_dir):
                # Try to read the file to verify it's a valid text file and count words
                try:
                    content = md_file.read_text(encoding="utf-8")
                    wiki_files.append(md_file)
                    total_words += len(content.split())
                except (UnicodeDecodeError, PermissionError, OSError):
                    # Skip files that can't be read (binary files, permission issues)
                    continue

    # Display stats
    click.echo(f"\nKnowledge Base: {config.name}")
    click.echo(f"Topic: {config.topic}")
    click.echo(f"Created: {config.created}")
    click.echo(f"Last compile: {config.last_compile or 'Never'}")
    click.echo(f"\nSources: {len(source_files)}")
    click.echo(f"Wiki articles: {len(wiki_files)}")
    click.echo(f"Total words: {total_words:,}")
    click.echo(f"\nLocation: {kb_dir}")


if __name__ == "__main__":
    cli()
