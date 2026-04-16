"""Tests for ePub ingestion."""

import pytest
from pathlib import Path
from click.testing import CliRunner
from vibe_kb.add.epub import (
    extract_epub_to_markdown,
    get_epub_metadata,
    extract_epub_to_chapters,
)
from vibe_kb.cli import cli
from ebooklib import epub


def create_minimal_epub(path: Path, title="Test Book", author="Test Author", chapters=None):
    """Create a minimal valid ePub for testing."""
    book = epub.EpubBook()
    book.set_identifier("test123")
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)

    # Add chapters
    if chapters is None:
        chapters = [("Chapter 1", "This is chapter one content.")]

    epub_chapters = []
    for i, (chapter_title, content) in enumerate(chapters):
        chapter = epub.EpubHtml(title=chapter_title, file_name=f"chap_{i + 1}.xhtml", lang="en")
        chapter.content = f"<html><body><h1>{chapter_title}</h1><p>{content}</p></body></html>"
        book.add_item(chapter)
        epub_chapters.append(chapter)

    # Add navigation
    book.toc = tuple(epub_chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Define spine
    book.spine = ["nav"] + epub_chapters

    # Write to file
    epub.write_epub(str(path), book)


def test_extract_epub_basic(tmp_path):
    """Test basic ePub extraction."""
    epub_path = tmp_path / "test.epub"
    output_path = tmp_path / "output.md"

    create_minimal_epub(epub_path, title="My Test Book", author="John Doe")

    result = extract_epub_to_markdown(epub_path, output_path)

    assert output_path.exists()
    assert result["title"] == "My Test Book"
    assert result["author"] == "John Doe"
    # Note: chapter_count includes navigation items that have text content
    assert result["chapter_count"] >= 1

    content = output_path.read_text()
    assert "# My Test Book" in content
    assert "**Author:** John Doe" in content
    assert "Chapter 1" in content


def test_extract_epub_with_multiple_chapters(tmp_path):
    """Test ePub with multiple chapters."""
    epub_path = tmp_path / "test.epub"
    output_path = tmp_path / "output.md"

    chapters = [
        ("Chapter 1", "First chapter content."),
        ("Chapter 2", "Second chapter content."),
        ("Chapter 3", "Third chapter content."),
    ]
    create_minimal_epub(epub_path, chapters=chapters)

    result = extract_epub_to_markdown(epub_path, output_path)

    # Note: chapter_count includes navigation items that have text content
    assert result["chapter_count"] >= 3
    content = output_path.read_text()
    assert "## Chapter 1" in content
    assert "## Chapter 2" in content
    assert "## Chapter 3" in content


def test_extract_epub_corrupt_file(tmp_path):
    """Test handling of corrupt ePub file."""
    epub_path = tmp_path / "corrupt.epub"
    output_path = tmp_path / "output.md"

    # Create an invalid zip file
    epub_path.write_text("This is not a valid ePub file")

    with pytest.raises(ValueError) as exc_info:
        extract_epub_to_markdown(epub_path, output_path)

    error_msg = str(exc_info.value).lower()
    assert "corrupt" in error_msg or "invalid" in error_msg or "failed to read" in error_msg


def test_extract_epub_missing_metadata(tmp_path):
    """Test handling of ePub with missing/malformed metadata."""
    epub_path = tmp_path / "no_metadata.epub"
    output_path = tmp_path / "output.md"

    # Create an ePub without standard metadata
    book = epub.EpubBook()
    book.set_identifier("test456")
    # Don't set title or author - they should default to "Unknown"
    book.set_language("en")

    chapter = epub.EpubHtml(title="Chapter", file_name="chap.xhtml", lang="en")
    chapter.content = "<html><body><p>Content</p></body></html>"
    book.add_item(chapter)
    book.toc = (chapter,)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", chapter]

    epub.write_epub(str(epub_path), book)

    result = extract_epub_to_markdown(epub_path, output_path)

    assert result["title"] == "Unknown"
    assert result["author"] == "Unknown"


def test_extract_epub_empty_chapters(tmp_path):
    """Test handling of ePub with no extractable content."""
    from unittest.mock import patch, MagicMock

    epub_path = tmp_path / "empty.epub"
    output_path = tmp_path / "output.md"

    # Create a real epub file first (for file validation)
    create_minimal_epub(epub_path, title="Empty Book", author="Test Author")

    # Mock the book to return no items with text content
    with patch("vibe_kb.add.epub.epub.read_epub") as mock_read:
        mock_book = MagicMock()
        mock_book.get_metadata.return_value = [["Empty Book"]]

        # Return empty list of items
        mock_book.get_items.return_value = []

        mock_read.return_value = mock_book

        with pytest.raises(ValueError) as exc_info:
            extract_epub_to_markdown(epub_path, output_path)

        assert "no content" in str(exc_info.value).lower()


def test_get_epub_metadata(tmp_path):
    """Test metadata extraction without full extraction."""
    epub_path = tmp_path / "test.epub"
    create_minimal_epub(epub_path, title="Metadata Test", author="Jane Smith")

    metadata = get_epub_metadata(epub_path)

    assert metadata["title"] == "Metadata Test"
    assert metadata["author"] == "Jane Smith"
    assert metadata["source_type"] == "book"


def test_get_epub_metadata_missing(tmp_path):
    """Test metadata extraction with missing data."""
    epub_path = tmp_path / "no_metadata.epub"

    book = epub.EpubBook()
    book.set_identifier("test000")
    book.set_language("en")

    chapter = epub.EpubHtml(title="Chapter", file_name="chap.xhtml", lang="en")
    chapter.content = "<html><body><p>Content</p></body></html>"
    book.add_item(chapter)
    book.toc = (chapter,)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", chapter]

    epub.write_epub(str(epub_path), book)

    metadata = get_epub_metadata(epub_path)

    assert metadata["title"] == "Unknown"
    assert metadata["author"] == "Unknown"


def test_cli_add_epub_integration(tmp_path):
    """Test CLI integration for adding ePub."""
    runner = CliRunner()

    # Create KB first
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    # Create test ePub
    epub_path = tmp_path / "test_book.epub"
    create_minimal_epub(epub_path, title="CLI Test Book", author="Test Author")

    # Add ePub to KB
    result = runner.invoke(
        cli, ["add", "test-kb", "--epub", str(epub_path), "--vault-path", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert "Added book: CLI Test Book" in result.output

    # Check files were created
    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    books_dir = kb_dir / "raw" / "books"
    assert books_dir.exists()

    # Check markdown file exists
    md_files = list(books_dir.glob("*.md"))
    assert len(md_files) == 1

    # Check metadata file exists
    meta_files = list(books_dir.glob("*.meta.json"))
    assert len(meta_files) == 1


def test_cli_add_epub_invalid_extension(tmp_path):
    """Test CLI validation of file extension."""
    runner = CliRunner()

    # Create KB first
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    # Create a file with wrong extension
    wrong_file = tmp_path / "not_an_epub.txt"
    wrong_file.write_text("This is not an epub")

    # Try to add it
    result = runner.invoke(
        cli, ["add", "test-kb", "--epub", str(wrong_file), "--vault-path", str(tmp_path)]
    )

    assert result.exit_code != 0
    assert "not an .epub file" in result.output.lower()


def test_cli_add_epub_corrupt_file(tmp_path):
    """Test CLI handling of corrupt ePub file."""
    runner = CliRunner()

    # Create KB first
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    # Create corrupt ePub
    corrupt_epub = tmp_path / "corrupt.epub"
    corrupt_epub.write_text("Not a valid ePub file")

    # Try to add it
    result = runner.invoke(
        cli, ["add", "test-kb", "--epub", str(corrupt_epub), "--vault-path", str(tmp_path)]
    )

    assert result.exit_code != 0
    assert "error" in result.output.lower() or "invalid" in result.output.lower()


def test_cli_add_epub_prevents_overwrite(tmp_path):
    """Test that adding the same epub twice fails without --force."""
    runner = CliRunner()

    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    epub_path = tmp_path / "test_book.epub"
    create_minimal_epub(epub_path, title="Duplicate Book", author="Author")

    # First add — should succeed
    result = runner.invoke(
        cli, ["add", "test-kb", "--epub", str(epub_path), "--vault-path", str(tmp_path)]
    )
    assert result.exit_code == 0

    # Second add — should fail with overwrite error
    result = runner.invoke(
        cli, ["add", "test-kb", "--epub", str(epub_path), "--vault-path", str(tmp_path)]
    )
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_add_epub_rolls_back_markdown_on_metadata_failure(tmp_path):
    """If metadata creation fails after markdown is written, the .md is removed
    so a subsequent retry is not blocked by the 'already exists' guard."""
    from unittest.mock import patch

    runner = CliRunner()
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    epub_path = tmp_path / "book.epub"
    create_minimal_epub(epub_path, title="Rollback Test Book", author="Author")

    # Simulate create_metadata raising (e.g. disk-full / permission error)
    with patch("vibe_kb.cli.create_metadata", side_effect=OSError("disk full")):
        result = runner.invoke(
            cli, ["add", "test-kb", "--epub", str(epub_path), "--vault-path", str(tmp_path)]
        )

    assert result.exit_code != 0
    assert "disk full" in result.output

    # The markdown file must NOT remain — orphaned .md would block a retry
    books_dir = tmp_path / "knowledge-bases" / "test-kb" / "raw" / "books"
    orphaned_md = list(books_dir.glob("*.md"))
    assert len(orphaned_md) == 0, f"Orphaned markdown left behind: {orphaned_md}"

    # Retry must now succeed without hitting the 'already exists' guard
    result = runner.invoke(
        cli, ["add", "test-kb", "--epub", str(epub_path), "--vault-path", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert "Added book" in result.output


def test_extract_epub_to_chapters_creates_directory_structure(tmp_path):
    """Test that ePub extraction creates directory with index and chapter files."""
    epub_path = tmp_path / "test.epub"
    output_dir = tmp_path / "build-llm-from-scratch"

    chapters = [
        ("Introduction to LLMs", "This is the introduction content."),
        ("Working with Text Data", "This covers tokenization."),
        ("Coding Attention Mechanisms", "This explains attention."),
    ]
    create_minimal_epub(
        epub_path,
        title="Build a Large Language Model",
        author="Sebastian Raschka",
        chapters=chapters,
    )

    result = extract_epub_to_chapters(epub_path, output_dir)

    # Check result metadata
    assert result["title"] == "Build a Large Language Model"
    assert result["author"] == "Sebastian Raschka"
    assert result["chapter_count"] >= 3  # May include navigation items
    assert result["images_extracted"] == 0

    # Check directory structure
    assert output_dir.exists()
    assert (output_dir / "index.md").exists()
    assert (output_dir / "chapter-01-introduction-to-llms.md").exists()
    assert (output_dir / "chapter-02-working-with-text-data.md").exists()
    assert (output_dir / "chapter-03-coding-attention-mechanisms.md").exists()

    # Check index.md content
    index_content = (output_dir / "index.md").read_text()
    assert "# Build a Large Language Model" in index_content
    assert "**Author:** Sebastian Raschka" in index_content
    assert "[[chapter-01-introduction-to-llms|Chapter 1: Introduction to LLMs]]" in index_content
    assert (
        "[[chapter-02-working-with-text-data|Chapter 2: Working with Text Data]]" in index_content
    )

    # Check chapter file content
    chapter1_content = (output_dir / "chapter-01-introduction-to-llms.md").read_text()
    assert "# Introduction to LLMs" in chapter1_content
    assert "This is the introduction content." in chapter1_content


def test_extract_epub_to_chapters_creates_robust_index_with_frontmatter(tmp_path):
    """Test that index.md includes comprehensive frontmatter and metadata."""
    epub_path = tmp_path / "test.epub"
    output_dir = tmp_path / "deep-learning-book"

    chapters = [
        ("Neural Networks Basics", "Introduction to neural networks."),
        ("Backpropagation", "How backprop works."),
    ]
    create_minimal_epub(
        epub_path, title="Deep Learning", author="Ian Goodfellow", chapters=chapters
    )

    extract_epub_to_chapters(epub_path, output_dir)

    index_content = (output_dir / "index.md").read_text()

    # Check frontmatter exists
    assert index_content.startswith("---")
    assert "type: book" in index_content
    assert "title: Deep Learning" in index_content
    assert "author: Ian Goodfellow" in index_content
    assert "added:" in index_content

    # Check main content sections
    assert "# Deep Learning" in index_content
    assert "**Author:** Ian Goodfellow" in index_content
    assert "## Table of Contents" in index_content

    # Check wikilinks format
    assert (
        "[[chapter-01-neural-networks-basics|Chapter 1: Neural Networks Basics]]" in index_content
    )
    assert "[[chapter-02-backpropagation|Chapter 2: Backpropagation]]" in index_content


def test_extract_epub_to_chapters_with_images(tmp_path):
    """Test that image count is included in index frontmatter."""
    from unittest.mock import patch

    epub_path = tmp_path / "test.epub"
    output_dir = tmp_path / "book-with-images"

    chapters = [
        ("Introduction", "See the diagram below."),
    ]
    create_minimal_epub(epub_path, title="Visual Book", author="Author", chapters=chapters)

    # Mock image extraction to return 2 images
    mock_image_result = {
        "downloaded": 2,
        "images": [
            {"original_path": "images/fig1.png", "filename": "fig1.png"},
            {"original_path": "images/fig2.png", "filename": "fig2.png"},
        ],
    }

    with patch("vibe_kb.add.epub.extract_images_from_epub", return_value=mock_image_result):
        result = extract_epub_to_chapters(epub_path, output_dir)

    assert result["images_extracted"] == 2

    # Check index.md frontmatter includes image count
    index_content = (output_dir / "index.md").read_text()
    assert "images: 2" in index_content


def test_cli_add_epub_with_split_chapters(tmp_path):
    """Test CLI integration for adding ePub with chapter splitting."""
    runner = CliRunner()

    # Create KB first
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    # Create test ePub
    epub_path = tmp_path / "test_book.epub"
    chapters = [
        ("Introduction", "Chapter 1 content."),
        ("Advanced Topics", "Chapter 2 content."),
    ]
    create_minimal_epub(epub_path, title="Split Test Book", author="Test Author", chapters=chapters)

    # Add ePub with --split-chapters flag
    result = runner.invoke(
        cli,
        [
            "add",
            "test-kb",
            "--epub",
            str(epub_path),
            "--split-chapters",
            "--vault-path",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Added book: Split Test Book" in result.output

    # Check directory structure was created
    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    books_dir = kb_dir / "raw" / "books"

    # Find the book directory (it has a date prefix)
    book_dirs = [d for d in books_dir.iterdir() if d.is_dir() and "split-test-book" in d.name]
    assert len(book_dirs) == 1
    book_dir = book_dirs[0]

    assert (book_dir / "index.md").exists()
    assert (book_dir / "chapter-01-introduction.md").exists()
    assert (book_dir / "chapter-02-advanced-topics.md").exists()


def test_extract_epub_to_chapters_resolves_relative_image_paths(tmp_path):
    """Test that relative image paths like ../Images/fig.png are resolved correctly."""
    from unittest.mock import patch, Mock

    epub_path = tmp_path / "test.epub"
    output_dir = tmp_path / "book-with-relative-images"

    # Create ePub with typical structure: OEBPS/Text/chapter.xhtml referencing ../Images/fig.png
    book = epub.EpubBook()
    book.set_identifier("test123")
    book.set_title("Test Book")
    book.set_language("en")
    book.add_author("Test Author")

    # Add images in Images directory
    img1 = epub.EpubImage()
    img1.file_name = "OEBPS/Images/diagram.png"
    img1.content = b"diagram_content"
    book.add_item(img1)

    img2 = epub.EpubImage()
    img2.file_name = "OEBPS/Images/chart.png"
    img2.content = b"chart_content"
    book.add_item(img2)

    # Add chapter in Text directory with relative image reference
    chapter = epub.EpubHtml(title="Chapter 1", file_name="OEBPS/Text/chapter1.xhtml", lang="en")
    # Use relative path that goes up one level then into Images
    chapter.content = """<html><body>
        <h1>Chapter 1</h1>
        <p>See the diagram:</p>
        <img src="../Images/diagram.png" alt="Diagram"/>
        <p>And the chart:</p>
        <img src="../Images/chart.png" alt="Chart"/>
    </body></html>"""
    book.add_item(chapter)

    book.toc = (chapter,)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", chapter]

    epub.write_epub(str(epub_path), book)

    # Extract chapters
    result = extract_epub_to_chapters(epub_path, output_dir)

    assert result["images_extracted"] == 2

    # Read the generated chapter markdown
    chapter_files = list(output_dir.glob("chapter-*.md"))
    assert len(chapter_files) >= 1

    # Find the chapter file with actual content (not nav.xhtml)
    chapter_content = ""
    for cf in chapter_files:
        content = cf.read_text()
        if "Chapter 1" in content and len(content) > 100:
            chapter_content = content
            break

    assert chapter_content, "Could not find chapter with content"

    # Verify that relative paths were resolved and converted to local references
    assert "book-with-relative-images_images/diagram.png" in chapter_content
    assert "book-with-relative-images_images/chart.png" in chapter_content

    # Verify original relative paths are NOT in the content
    assert "../Images/diagram.png" not in chapter_content
    assert "../Images/chart.png" not in chapter_content
