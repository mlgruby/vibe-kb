"""Tests for wiki search."""

import pytest
from click.testing import CliRunner
from vibe_kb.search import search_wiki
from vibe_kb.cli import cli


def test_search_wiki_basic(tmp_path):
    """Test basic case-insensitive search."""
    # Create test wiki structure
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    # Create test files
    (wiki_dir / "test1.md").write_text(
        "This is about transformers and attention mechanisms.", encoding="utf-8"
    )
    (wiki_dir / "test2.md").write_text("This discusses neural networks.", encoding="utf-8")

    results = search_wiki(wiki_dir, "transformers")

    assert len(results) == 1
    assert "test1.md" in results[0]["file"]
    assert "transformers" in results[0]["match"].lower()
    assert results[0]["line"] == 1


def test_search_wiki_case_sensitive(tmp_path):
    """Test case-sensitive search."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    (wiki_dir / "test.md").write_text(
        "Transformers are important.\ntransformers vary in size.", encoding="utf-8"
    )

    # Case-insensitive (default)
    results = search_wiki(wiki_dir, "transformers")
    assert len(results) == 2

    # Case-sensitive
    results = search_wiki(wiki_dir, "transformers", case_sensitive=True)
    assert len(results) == 1
    assert "transformers vary" in results[0]["match"]


def test_search_wiki_no_matches(tmp_path):
    """Test search with no matches."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    (wiki_dir / "test.md").write_text("Some content here.", encoding="utf-8")

    results = search_wiki(wiki_dir, "nonexistent")

    assert len(results) == 0


def test_search_wiki_multiple_matches_same_file(tmp_path):
    """Test multiple matches in same file."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    content = """# Attention Mechanisms

Attention is used in transformers.
The attention mechanism is powerful.
Self-attention is a key innovation."""

    (wiki_dir / "test.md").write_text(content, encoding="utf-8")

    results = search_wiki(wiki_dir, "attention")

    # Should find 4 matches: title, and 3 lines with "attention"
    assert len(results) == 4
    assert all("test.md" in r["file"] for r in results)
    # Check line numbers are different
    line_numbers = [r["line"] for r in results]
    assert len(set(line_numbers)) == 4


def test_search_wiki_recursive(tmp_path):
    """Test recursive search in subdirectories."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    (wiki_dir / "concepts").mkdir()
    (wiki_dir / "summaries").mkdir()

    (wiki_dir / "root.md").write_text("Neural networks in root.", encoding="utf-8")
    (wiki_dir / "concepts" / "concept1.md").write_text(
        "Neural networks in concepts.", encoding="utf-8"
    )
    (wiki_dir / "summaries" / "paper1.md").write_text(
        "Neural networks in summaries.", encoding="utf-8"
    )

    results = search_wiki(wiki_dir, "neural networks")

    assert len(results) == 3
    files = [r["file"] for r in results]
    assert any("root.md" in f for f in files)
    assert any("concepts" in f for f in files)
    assert any("summaries" in f for f in files)


def test_search_wiki_skip_hidden_files(tmp_path):
    """Test that hidden files are skipped."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    (wiki_dir / "visible.md").write_text("Search term here.", encoding="utf-8")
    (wiki_dir / ".hidden.md").write_text("Search term in hidden file.", encoding="utf-8")

    results = search_wiki(wiki_dir, "search term")

    assert len(results) == 1
    assert "visible.md" in results[0]["file"]
    assert ".hidden" not in results[0]["file"]


def test_search_wiki_empty_query(tmp_path):
    """Test handling of empty query."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    (wiki_dir / "test.md").write_text("Some content.", encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        search_wiki(wiki_dir, "")

    assert "empty" in str(exc_info.value).lower()


def test_search_wiki_nonexistent_directory(tmp_path):
    """Test handling of non-existent directory."""
    wiki_dir = tmp_path / "nonexistent"

    with pytest.raises(ValueError) as exc_info:
        search_wiki(wiki_dir, "query")

    assert (
        "not found" in str(exc_info.value).lower()
        or "does not exist" in str(exc_info.value).lower()
    )


def test_search_wiki_file_read_error(tmp_path):
    """Test graceful handling of file read errors."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    # Create a file with valid UTF-8 and one with invalid encoding
    (wiki_dir / "valid.md").write_text("Valid content with search term.", encoding="utf-8")
    # Create a file that might cause encoding issues
    (wiki_dir / "binary.md").write_bytes(b"\x80\x81\x82 search term")

    # Should skip files with read errors and return valid results
    results = search_wiki(wiki_dir, "search term")

    # At least the valid file should be found
    assert len(results) >= 1
    assert any("valid.md" in r["file"] for r in results)


def test_search_wiki_empty_file(tmp_path):
    """Test handling of empty files."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    (wiki_dir / "empty.md").write_text("", encoding="utf-8")
    (wiki_dir / "content.md").write_text("Search term here.", encoding="utf-8")

    results = search_wiki(wiki_dir, "search term")

    assert len(results) == 1
    assert "content.md" in results[0]["file"]


def test_search_wiki_special_characters(tmp_path):
    """Test search with special regex characters."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    (wiki_dir / "test.md").write_text("Cost is $100. Pattern is [a-z]+.", encoding="utf-8")

    # Test that special chars are escaped properly
    results = search_wiki(wiki_dir, "$100")
    assert len(results) == 1

    results = search_wiki(wiki_dir, "[a-z]+")
    assert len(results) == 1


def test_cli_search_basic(tmp_path):
    """Test CLI search command."""
    runner = CliRunner()

    # Create KB first
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    # Add some content to wiki
    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    wiki_dir = kb_dir / "wiki"
    (wiki_dir / "test.md").write_text("Transformers are neural networks.", encoding="utf-8")

    # Search
    result = runner.invoke(
        cli, ["search", "test-kb", "transformers", "--vault-path", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert "transformers" in result.output.lower()
    assert "test.md" in result.output


def test_cli_search_no_matches(tmp_path):
    """Test CLI search with no matches."""
    runner = CliRunner()

    # Create KB first
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    # Add some content to wiki
    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    wiki_dir = kb_dir / "wiki"
    (wiki_dir / "test.md").write_text("Some content here.", encoding="utf-8")

    # Search for non-existent term
    result = runner.invoke(cli, ["search", "test-kb", "nonexistent", "--vault-path", str(tmp_path)])

    assert result.exit_code == 0
    assert "no matches found" in result.output.lower()


def test_cli_search_case_sensitive(tmp_path):
    """Test CLI search with case-sensitive flag."""
    runner = CliRunner()

    # Create KB first
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    # Add content with different cases on separate lines
    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    wiki_dir = kb_dir / "wiki"
    (wiki_dir / "test.md").write_text(
        "Transformers are important.\ntransformers vary in size.", encoding="utf-8"
    )

    # Case-insensitive search (default) - should find both lines
    result = runner.invoke(
        cli, ["search", "test-kb", "transformers", "--vault-path", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert "2 matches" in result.output.lower() or "found 2" in result.output.lower()

    # Case-sensitive search - should find only lowercase line
    result = runner.invoke(
        cli,
        ["search", "test-kb", "transformers", "--vault-path", str(tmp_path), "--case-sensitive"],
    )

    assert result.exit_code == 0
    assert "1 match" in result.output.lower() or "found 1" in result.output.lower()


def test_cli_search_nonexistent_kb(tmp_path):
    """Test CLI search on non-existent KB."""
    runner = CliRunner()

    result = runner.invoke(
        cli, ["search", "nonexistent-kb", "query", "--vault-path", str(tmp_path)]
    )

    assert result.exit_code != 0
    assert "error" in result.output.lower()
    assert "no wiki found" in result.output.lower()


def test_search_wiki_skips_symlinks(tmp_path):
    """Test that symlinks are skipped for security."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    # Create a regular file
    (wiki_dir / "normal.md").write_text("This is a normal file.", encoding="utf-8")

    # Create a sensitive file outside wiki
    sensitive_dir = tmp_path / "sensitive"
    sensitive_dir.mkdir()
    (sensitive_dir / "secret.md").write_text("SECRET CONTENT", encoding="utf-8")

    # Create symlink to sensitive file
    symlink_path = wiki_dir / "link.md"
    symlink_path.symlink_to(sensitive_dir / "secret.md")

    # Search should not return content from symlink
    results = search_wiki(wiki_dir, "SECRET")

    assert len(results) == 0, "Symlinks should be skipped for security"


def test_search_wiki_handles_crlf(tmp_path):
    """Test that Windows CRLF line endings are handled correctly."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    # Create file with CRLF line endings
    (wiki_dir / "windows.md").write_text(
        "Line 1\r\nLine 2 with keyword\r\nLine 3", encoding="utf-8"
    )

    results = search_wiki(wiki_dir, "keyword")

    assert len(results) == 1
    assert results[0]["line"] == 2
    assert "\r" not in results[0]["match"], "Match should not contain carriage return"


def test_search_wiki_excludes_templates_directory(tmp_path):
    """Test that .templates/ directory is excluded from search results."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    # Create a real article
    (wiki_dir / "concepts").mkdir()
    (wiki_dir / "concepts" / "transformers.md").write_text(
        "Transformers use attention mechanisms.", encoding="utf-8"
    )

    # Create a template (should be excluded)
    templates_dir = wiki_dir / ".templates"
    templates_dir.mkdir()
    (templates_dir / "concept-article.md").write_text(
        "Transformers template placeholder.", encoding="utf-8"
    )

    results = search_wiki(wiki_dir, "transformers")

    assert len(results) == 1
    assert ".templates" not in results[0]["file"]
    assert results[0]["file"].startswith("concepts")


def test_search_wiki_excludes_underscore_directories(tmp_path):
    """Test that _archived/ and similar directories are excluded from search."""
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    (wiki_dir / "concepts").mkdir()
    (wiki_dir / "concepts" / "ml.md").write_text("Machine learning concepts.", encoding="utf-8")

    archived_dir = wiki_dir / "_archived"
    archived_dir.mkdir()
    (archived_dir / "old.md").write_text("Machine learning old article.", encoding="utf-8")

    results = search_wiki(wiki_dir, "machine learning")

    assert all("_archived" not in r["file"] for r in results)
