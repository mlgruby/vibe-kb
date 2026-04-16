"""Tests for kb stats command."""
from pathlib import Path
from click.testing import CliRunner
from vibe_kb.cli import cli
import json


def test_stats_basic(tmp_path):
    """Test basic stats display."""
    runner = CliRunner()

    # Create KB first
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path), "--topic", "AI Research"])
    assert result.exit_code == 0

    # Run stats
    result = runner.invoke(cli, ["stats", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code == 0
    assert "Knowledge Base: test-kb" in result.output
    assert "Topic: AI Research" in result.output
    assert "Created:" in result.output
    assert "Last compile: Never" in result.output
    assert "Sources: 0" in result.output
    # Spec bug: template files in .templates/ are counted because spec only checks f.name
    # not parent directory. Creates 5 template files.
    assert "Wiki articles: 5" in result.output
    assert "Location:" in result.output


def test_stats_with_sources(tmp_path):
    """Test stats with source files."""
    runner = CliRunner()

    # Create KB
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    kb_dir = tmp_path / "knowledge-bases" / "test-kb"

    # Add some source files
    (kb_dir / "raw" / "books" / "book1.md").write_text("Book content", encoding='utf-8')
    (kb_dir / "raw" / "papers" / "paper1.pdf").write_bytes(b"PDF content")
    (kb_dir / "raw" / "articles" / "article1.md").write_text("Article", encoding='utf-8')

    # Run stats
    result = runner.invoke(cli, ["stats", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code == 0
    assert "Sources: 3" in result.output


def test_stats_with_wiki_articles(tmp_path):
    """Test stats with wiki articles."""
    runner = CliRunner()

    # Create KB
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    wiki_dir = kb_dir / "wiki"

    # Add wiki articles
    (wiki_dir / "concepts" / "concept1.md").write_text("This is a concept article.", encoding='utf-8')
    (wiki_dir / "topics" / "topic1.md").write_text("This is a topic article.", encoding='utf-8')

    # Run stats
    result = runner.invoke(cli, ["stats", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code == 0
    # 5 template files + 2 user articles = 7 total
    assert "Wiki articles: 7" in result.output


def test_stats_skip_hidden_files(tmp_path):
    """Test that hidden files (starting with .) are skipped per spec."""
    runner = CliRunner()

    # Create KB
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    wiki_dir = kb_dir / "wiki"

    # Add visible and hidden files
    (wiki_dir / "visible.md").write_text("Visible content", encoding='utf-8')
    (wiki_dir / ".hidden.md").write_text("Hidden content", encoding='utf-8')

    # Run stats
    result = runner.invoke(cli, ["stats", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code == 0
    # Spec: wiki_files = [f for f in wiki_dir.rglob("*.md") if not f.name.startswith(('_', '.'))]
    # 5 template files + 1 visible file = 6 (.hidden.md is skipped)
    assert "Wiki articles: 6" in result.output


def test_stats_skip_template_files(tmp_path):
    """Test that template files (starting with _) are skipped."""
    runner = CliRunner()

    # Create KB
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    wiki_dir = kb_dir / "wiki"

    # Add regular and template files
    (wiki_dir / "article.md").write_text("Article content", encoding='utf-8')
    (wiki_dir / "_template.md").write_text("Template content", encoding='utf-8')

    # Run stats
    result = runner.invoke(cli, ["stats", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code == 0
    # 5 template files in .templates/ + 1 article = 6 (_template.md is skipped)
    assert "Wiki articles: 6" in result.output


def test_stats_nonexistent_kb(tmp_path):
    """Test error when KB doesn't exist."""
    runner = CliRunner()

    result = runner.invoke(cli, ["stats", "nonexistent-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code != 0
    assert "error" in result.output.lower()
    assert "not found" in result.output.lower()


def test_stats_missing_config(tmp_path):
    """Test error when config is missing."""
    runner = CliRunner()

    # Create KB directory but remove config
    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    kb_dir.mkdir(parents=True)
    (kb_dir / "raw").mkdir()
    (kb_dir / "wiki").mkdir()

    result = runner.invoke(cli, ["stats", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code != 0
    assert "error" in result.output.lower()


def test_stats_with_compile_timestamp(tmp_path):
    """Test stats display with last compile timestamp."""
    runner = CliRunner()

    # Create KB
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    kb_dir = tmp_path / "knowledge-bases" / "test-kb"

    # Load config and mark as compiled
    config_file = kb_dir / ".kbconfig"
    config_data = json.loads(config_file.read_text())
    config_data["last_compile"] = "2024-01-15T10:30:00"
    config_file.write_text(json.dumps(config_data, indent=2))

    # Run stats
    result = runner.invoke(cli, ["stats", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code == 0
    assert "Last compile: 2024-01-15T10:30:00" in result.output


def test_stats_word_count_formatting(tmp_path):
    """Test that word count is formatted with thousands separator."""
    runner = CliRunner()

    # Create KB
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    wiki_dir = kb_dir / "wiki"

    # Create a file with many words
    words = " ".join([f"word{i}" for i in range(1500)])
    (wiki_dir / "large.md").write_text(words, encoding='utf-8')

    # Run stats
    result = runner.invoke(cli, ["stats", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code == 0
    # Should have comma separator for thousands (1500 + template words)
    assert "1," in result.output  # At least 1,xxx format


def test_stats_crashes_on_binary_files(tmp_path):
    """Test that binary files cause an error per spec (no error handling)."""
    runner = CliRunner()

    # Create KB
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    wiki_dir = kb_dir / "wiki"

    # Add valid file and binary file with .md extension
    (wiki_dir / "valid.md").write_text("Valid content", encoding='utf-8')
    (wiki_dir / "binary.md").write_bytes(b'\x80\x81\x82\x83')

    # Run stats - spec has no error handling, so this should crash
    result = runner.invoke(cli, ["stats", "test-kb", "--vault-path", str(tmp_path)])

    # Per spec: no error handling, so command will fail
    assert result.exit_code != 0


def test_stats_empty_wiki(tmp_path):
    """Test stats with empty wiki directory (only template files)."""
    runner = CliRunner()

    # Create KB
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    # Run stats on KB with only template files
    result = runner.invoke(cli, ["stats", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code == 0
    # 5 template files are counted per spec
    assert "Wiki articles: 5" in result.output


def test_stats_recursive_counting(tmp_path):
    """Test that files in subdirectories are counted."""
    runner = CliRunner()

    # Create KB
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    kb_dir = tmp_path / "knowledge-bases" / "test-kb"

    # Add sources in different subdirectories
    (kb_dir / "raw" / "books" / "book1.md").write_text("Book", encoding='utf-8')
    (kb_dir / "raw" / "books" / "subdir").mkdir(parents=True, exist_ok=True)
    (kb_dir / "raw" / "books" / "subdir" / "book2.md").write_text("Book2", encoding='utf-8')
    (kb_dir / "raw" / "papers" / "paper1.pdf").write_bytes(b"PDF")

    # Add wiki articles in subdirectories
    (kb_dir / "wiki" / "concepts" / "concept1.md").write_text("Concept", encoding='utf-8')
    (kb_dir / "wiki" / "topics" / "subtopic").mkdir(parents=True, exist_ok=True)
    (kb_dir / "wiki" / "topics" / "subtopic" / "topic1.md").write_text("Topic", encoding='utf-8')

    # Run stats
    result = runner.invoke(cli, ["stats", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code == 0
    assert "Sources: 3" in result.output
    # 5 template files + 2 user articles = 7
    assert "Wiki articles: 7" in result.output


def test_stats_includes_symlinks(tmp_path):
    """Test that symlinks are counted per spec (no symlink filtering)."""
    runner = CliRunner()

    # Create KB
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    wiki_dir = kb_dir / "wiki"

    # Create a regular file
    (wiki_dir / "normal.md").write_text("Normal file", encoding='utf-8')

    # Create a file outside wiki
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    (external_dir / "external.md").write_text("External content", encoding='utf-8')

    # Create symlink to external file
    symlink_path = wiki_dir / "link.md"
    symlink_path.symlink_to(external_dir / "external.md")

    # Run stats
    result = runner.invoke(cli, ["stats", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code == 0
    # Spec does not filter symlinks: 5 template files + 1 normal + 1 symlink = 7
    assert "Wiki articles: 7" in result.output


def test_stats_empty_files(tmp_path):
    """Test handling of empty files."""
    runner = CliRunner()

    # Create KB
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    wiki_dir = kb_dir / "wiki"

    # Create empty and non-empty files
    (wiki_dir / "empty.md").write_text("", encoding='utf-8')
    (wiki_dir / "content.md").write_text("Some content here", encoding='utf-8')

    # Run stats
    result = runner.invoke(cli, ["stats", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code == 0
    # 5 template files + 2 user files = 7
    assert "Wiki articles: 7" in result.output
