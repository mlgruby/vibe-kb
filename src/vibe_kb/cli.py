"""CLI entry point for kb command."""
import click
import tempfile
from pathlib import Path
from typing import Optional
from .config import KBConfig
from .add.epub import extract_epub_to_markdown, get_epub_metadata
from .add.youtube import extract_youtube_transcript
from .utils.files import generate_filename, create_metadata
from .search import search_wiki


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


@cli.command()
@click.argument("kb_name")
@click.option("--epub", "epub_path", type=click.Path(exists=True, path_type=Path), help="ePub file path")
@click.option("--youtube", "youtube_url", type=str, help="YouTube video URL")
@click.option(
    "--vault-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Obsidian vault path"
)
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
        click.echo("Error: No source specified. Use --epub, --url, or --youtube")
        raise click.Abort()


def _add_epub(kb_dir: Path, epub_path: Path):
    """Add ePub book to knowledge base."""
    # CRITICAL FIX #4: Validate file extension
    if epub_path.suffix.lower() != '.epub':
        click.echo(f"Error: '{epub_path.name}' is not an .epub file")
        raise click.Abort()

    click.echo(f"Processing ePub: {epub_path.name}")

    # Get metadata with error handling
    try:
        metadata = get_epub_metadata(epub_path)
    except ValueError as e:
        click.echo(f"Error: {str(e)}")
        raise click.Abort()

    # Generate filename
    filename = generate_filename(metadata['title'])
    output_path = kb_dir / "raw" / "books" / filename

    # Extract to markdown with error handling
    try:
        result = extract_epub_to_markdown(epub_path, output_path)
    except ValueError as e:
        click.echo(f"Error: {str(e)}")
        raise click.Abort()

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


def _add_youtube(kb_dir: Path, url: str):
    """Add YouTube video to knowledge base."""
    # Validate URL format
    if not (url.startswith(('http://', 'https://')) or
            'youtube.com' in url or 'youtu.be' in url):
        click.echo("Error: Invalid YouTube URL format")
        raise click.Abort()

    click.echo(f"Extracting transcript from: {url}")

    temp_path = None
    output_path = None

    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
            temp_path = Path(tmp.name)

        # Extract transcript
        result = extract_youtube_transcript(url, temp_path)

        # Generate filename
        filename = generate_filename(result['title'])
        output_path = kb_dir / "raw" / "videos" / filename

        # Move temp file to final location
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.rename(output_path)
        temp_path = None  # Successfully moved, don't clean up

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

    except ValueError as e:
        # Clean up temp file if it still exists
        if temp_path and temp_path.exists():
            temp_path.unlink()

        # Clean up output file if metadata creation failed
        if output_path and output_path.exists():
            output_path.unlink()
            meta_path = output_path.with_suffix('.meta.json')
            if meta_path.exists():
                meta_path.unlink()

        click.echo(f"Error: {str(e)}")
        raise click.Abort()
    except Exception as e:
        # Clean up temp file if it still exists
        if temp_path and temp_path.exists():
            temp_path.unlink()

        # Clean up output file if metadata creation failed
        if output_path and output_path.exists():
            output_path.unlink()
            meta_path = output_path.with_suffix('.meta.json')
            if meta_path.exists():
                meta_path.unlink()

        click.echo(f"Error: Unexpected error occurred: {str(e)}")
        raise click.Abort()


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
    try:
        config = KBConfig.load(kb_dir)
    except FileNotFoundError as e:
        click.echo(f"Error: {str(e)}")
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error: Failed to load config: {str(e)}")
        raise click.Abort()

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


if __name__ == "__main__":
    cli()
