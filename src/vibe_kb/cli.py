"""CLI entry point for kb command."""
import click
from pathlib import Path
from typing import Optional
from .config import KBConfig
from .add.epub import extract_epub_to_markdown, get_epub_metadata
from .utils.files import generate_filename, create_metadata


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


if __name__ == "__main__":
    cli()
