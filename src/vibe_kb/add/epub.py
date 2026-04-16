"""ePub source ingestion."""

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, Any
import re
from .images import extract_images_from_epub


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


def extract_epub_to_markdown(epub_path: Path, output_path: Path) -> Dict[str, Any]:
    """Extract ePub content to markdown.

    Args:
        epub_path: Path to .epub file
        output_path: Path to output .md file

    Returns:
        Dictionary with metadata (title, author, chapters, images_extracted)

    Raises:
        ValueError: If the ePub file is corrupt or contains no extractable content
    """
    # CRITICAL FIX #1: Error handling for corrupt/invalid ePub files
    try:
        book = epub.read_epub(str(epub_path))
    except Exception as e:
        raise ValueError(
            f"Failed to read ePub file '{epub_path.name}': {str(e)}. The file may be corrupt or invalid."
        )

    # CRITICAL FIX #2: Safe metadata access with fallback
    title = _safe_extract_metadata(book, "DC", "title")
    author = _safe_extract_metadata(book, "DC", "creator")

    # Extract images from ePub
    images_dir = output_path.parent / f"{output_path.stem}_images"
    image_result = extract_images_from_epub(epub_path, images_dir)
    images_extracted = image_result["downloaded"]

    # Build mapping of original image paths to local filenames
    image_map = {}
    if images_extracted > 0:
        for img in image_result["images"]:
            # Map both full path and just filename
            image_map[img["original_path"]] = img["filename"]
            # Also map just the filename in case references use relative paths
            original_filename = Path(img["original_path"]).name
            image_map[original_filename] = img["filename"]

    # Extract chapters
    chapters = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = item.get_content()
            # IMPORTANT FIX #7: Specify HTML parser (html.parser is built-in and handles XHTML well)
            soup = BeautifulSoup(content, "html.parser")

            # Convert images to markdown syntax if present
            if images_extracted > 0:
                for img_tag in soup.find_all("img"):
                    src = img_tag.get("src", "")
                    alt = img_tag.get("alt", "")

                    # Try to find matching image in our extracted images
                    local_filename = None
                    for original_path, filename in image_map.items():
                        if src in original_path or original_path in src or Path(src).name == Path(original_path).name:
                            local_filename = filename
                            break

                    if local_filename:
                        # Replace img tag with markdown syntax
                        images_dir_relative = f"{output_path.stem}_images"
                        markdown_img = f"![{alt}]({images_dir_relative}/{local_filename})"
                        img_tag.replace_with(markdown_img)

            # Extract text
            text = soup.get_text()
            # Clean up whitespace
            text = re.sub(r"\n\s*\n", "\n\n", text)
            text = text.strip()

            if text:  # Only add non-empty chapters
                chapters.append({"title": item.get_name(), "content": text})

    # CRITICAL FIX #3: Validate that chapters were extracted
    if not chapters:
        raise ValueError(
            f"No content could be extracted from '{epub_path.name}'. The ePub may be empty or have an unsupported format."
        )

    # Write markdown
    markdown = f"# {title}\n\n"
    markdown += f"**Author:** {author}\n\n"
    markdown += "---\n\n"

    for i, chapter in enumerate(chapters, 1):
        markdown += f"## Chapter {i}\n\n"
        markdown += f"{chapter['content']}\n\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    return {
        "title": title,
        "author": author,
        "chapter_count": len(chapters),
        "images_extracted": images_extracted,
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
        raise ValueError(
            f"Failed to read ePub file '{epub_path.name}': {str(e)}. The file may be corrupt or invalid."
        )

    # IMPORTANT FIX #8: Use shared helper function for metadata extraction
    title = _safe_extract_metadata(book, "DC", "title")
    author = _safe_extract_metadata(book, "DC", "creator")

    return {"title": title, "author": author, "source_type": "book"}
