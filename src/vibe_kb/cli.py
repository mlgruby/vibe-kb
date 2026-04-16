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


if __name__ == "__main__":
    cli()
