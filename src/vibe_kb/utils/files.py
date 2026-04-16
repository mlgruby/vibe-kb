"""File utilities for knowledge base operations."""
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional


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
