"""ePub source ingestion."""

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, Any
import re
from datetime import date
import posixpath
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

            # Get the current document's path for resolving relative image references
            document_path = item.get_name()  # e.g., "OEBPS/Text/chapter1.xhtml"
            document_dir = posixpath.dirname(document_path)  # e.g., "OEBPS/Text"

            # Convert images to markdown syntax if present
            if images_extracted > 0:
                for img_tag in soup.find_all("img"):
                    src = img_tag.get("src", "")
                    alt = img_tag.get("alt", "")

                    local_filename = None

                    # Resolve relative image path to absolute ePub path
                    if src:
                        # Resolve src relative to the current document's directory
                        resolved_path = posixpath.normpath(
                            posixpath.join(document_dir, src)
                        )

                        # Look up the resolved path in image_map
                        if resolved_path in image_map:
                            local_filename = image_map[resolved_path]
                        # Fall back to basename matching
                        elif Path(src).name in image_map:
                            local_filename = image_map[Path(src).name]

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


def extract_epub_to_chapters(epub_path: Path, output_dir: Path) -> Dict[str, Any]:
    """Extract ePub into separate chapter files with index.

    Args:
        epub_path: Path to .epub file
        output_dir: Directory to create for book (will contain index.md and chapter files)

    Returns:
        Dictionary with metadata (title, author, chapter_count, images_extracted)

    Raises:
        ValueError: If the ePub file is corrupt or contains no extractable content
    """
    try:
        book = epub.read_epub(str(epub_path))
    except Exception as e:
        raise ValueError(
            f"Failed to read ePub file '{epub_path.name}': {str(e)}. The file may be corrupt or invalid."
        )

    title = _safe_extract_metadata(book, "DC", "title")
    author = _safe_extract_metadata(book, "DC", "creator")

    # Extract images from ePub
    images_dir = output_dir / f"{output_dir.stem}_images"
    image_result = extract_images_from_epub(epub_path, images_dir)
    images_extracted = image_result["downloaded"]

    # Build mapping of original image paths to local filenames
    image_map = {}
    if images_extracted > 0:
        for img in image_result["images"]:
            image_map[img["original_path"]] = img["filename"]
            original_filename = Path(img["original_path"]).name
            image_map[original_filename] = img["filename"]

    # Extract chapters
    chapters = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            content = item.get_content()
            soup = BeautifulSoup(content, "html.parser")

            # Get the current document's path for resolving relative image references
            document_path = item.get_name()  # e.g., "OEBPS/Text/chapter1.xhtml"
            document_dir = posixpath.dirname(document_path)  # e.g., "OEBPS/Text"

            # Convert images to markdown syntax if present
            if images_extracted > 0:
                for img_tag in soup.find_all("img"):
                    src = img_tag.get("src", "")
                    alt = img_tag.get("alt", "")

                    local_filename = None

                    # Resolve relative image path to absolute ePub path
                    if src:
                        # Resolve src relative to the current document's directory
                        resolved_path = posixpath.normpath(
                            posixpath.join(document_dir, src)
                        )

                        # Look up the resolved path in image_map
                        if resolved_path in image_map:
                            local_filename = image_map[resolved_path]
                        # Fall back to basename matching with warning comment
                        elif Path(src).name in image_map:
                            # This is less reliable but handles edge cases
                            local_filename = image_map[Path(src).name]

                    if local_filename:
                        images_dir_relative = f"{output_dir.stem}_images"
                        markdown_img = f"![{alt}]({images_dir_relative}/{local_filename})"
                        img_tag.replace_with(markdown_img)

            # Extract text
            text = soup.get_text()
            text = re.sub(r"\n\s*\n", "\n\n", text)
            text = text.strip()

            if text:
                # Extract chapter title from item title or first heading
                chapter_title = item.get_name()
                h1 = soup.find("h1")
                if h1:
                    chapter_title = h1.get_text(strip=True)

                chapters.append({"title": chapter_title, "content": text})

    if not chapters:
        raise ValueError(
            f"No content could be extracted from '{epub_path.name}'. The ePub may be empty or have an unsupported format."
        )

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate chapter filenames with slugs
    def slugify(text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^a-z0-9]+", "-", text)
        text = re.sub(r"-+", "-", text)
        return text.strip("-")

    # Write individual chapter files
    chapter_files = []
    for i, chapter in enumerate(chapters, 1):
        slug = slugify(chapter["title"])
        filename = f"chapter-{i:02d}-{slug}.md"
        chapter_path = output_dir / filename

        chapter_markdown = f"# {chapter['title']}\n\n{chapter['content']}\n"
        chapter_path.write_text(chapter_markdown, encoding="utf-8")

        chapter_files.append({"number": i, "title": chapter["title"], "filename": filename})

    # Write index.md with frontmatter
    index_path = output_dir / "index.md"
    today = date.today().isoformat()

    index_markdown = "---\n"
    index_markdown += "type: book\n"
    index_markdown += f"title: {title}\n"
    index_markdown += f"author: {author}\n"
    index_markdown += f"chapters: {len(chapters)}\n"
    index_markdown += f"images: {images_extracted}\n"
    index_markdown += f"added: {today}\n"
    index_markdown += "---\n\n"

    index_markdown += f"# {title}\n\n"
    index_markdown += f"**Author:** {author}\n\n"
    index_markdown += "## Table of Contents\n\n"

    for cf in chapter_files:
        chapter_slug = cf["filename"].replace(".md", "")
        index_markdown += (
            f"{cf['number']}. [[{chapter_slug}|Chapter {cf['number']}: {cf['title']}]]\n"
        )

    index_path.write_text(index_markdown, encoding="utf-8")

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
