"""ePub source ingestion."""
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, Any
import re


def _safe_extract_metadata(book: epub.EpubBook, namespace: str, field: str) -> str:
    """Safely extract metadata from ePub with fallback to 'Unknown'.

    Args:
        book: EpubBook instance
        namespace: Metadata namespace (e.g., 'DC')
        field: Metadata field name (e.g., 'title', 'creator')

    Returns:
        Extracted metadata or 'Unknown' if not found
    """
    try:
        metadata = book.get_metadata(namespace, field)
        if metadata and len(metadata) > 0 and len(metadata[0]) > 0:
            return metadata[0][0]
    except (IndexError, KeyError, TypeError):
        pass
    return "Unknown"


def extract_epub_to_markdown(
    epub_path: Path,
    output_path: Path
) -> Dict[str, Any]:
    """Extract ePub content to markdown.

    Args:
        epub_path: Path to .epub file
        output_path: Path to output .md file

    Returns:
        Dictionary with metadata (title, author, chapters)

    Raises:
        ValueError: If the ePub file is corrupt or contains no extractable content
    """
    # CRITICAL FIX #1: Error handling for corrupt/invalid ePub files
    try:
        book = epub.read_epub(str(epub_path))
    except Exception as e:
        raise ValueError(f"Failed to read ePub file '{epub_path.name}': {str(e)}. The file may be corrupt or invalid.")

    # CRITICAL FIX #2: Safe metadata access with fallback
    title = _safe_extract_metadata(book, 'DC', 'title')
    author = _safe_extract_metadata(book, 'DC', 'creator')

    # Extract chapters
    chapters = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = item.get_content()
            # IMPORTANT FIX #7: Specify HTML parser (html.parser is built-in and handles XHTML well)
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

    # CRITICAL FIX #3: Validate that chapters were extracted
    if not chapters:
        raise ValueError(f"No content could be extracted from '{epub_path.name}'. The ePub may be empty or have an unsupported format.")

    # Write markdown
    markdown = f"# {title}\n\n"
    markdown += f"**Author:** {author}\n\n"
    markdown += "---\n\n"

    for i, chapter in enumerate(chapters, 1):
        markdown += f"## Chapter {i}\n\n"
        markdown += f"{chapter['content']}\n\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding='utf-8')

    return {
        'title': title,
        'author': author,
        'chapter_count': len(chapters)
    }


def get_epub_metadata(epub_path: Path) -> Dict[str, Any]:
    """Get metadata from ePub without full extraction.

    Args:
        epub_path: Path to .epub file

    Returns:
        Dictionary with metadata

    Raises:
        ValueError: If the ePub file is corrupt or invalid
    """
    # CRITICAL FIX #1: Error handling for corrupt/invalid ePub files
    try:
        book = epub.read_epub(str(epub_path))
    except Exception as e:
        raise ValueError(f"Failed to read ePub file '{epub_path.name}': {str(e)}. The file may be corrupt or invalid.")

    # IMPORTANT FIX #8: Use shared helper function for metadata extraction
    title = _safe_extract_metadata(book, 'DC', 'title')
    author = _safe_extract_metadata(book, 'DC', 'creator')

    return {
        'title': title,
        'author': author,
        'source_type': 'book'
    }
