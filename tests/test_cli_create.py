"""Tests for kb create command."""
from pathlib import Path
from click.testing import CliRunner
from vibe_kb.cli import cli
import json


def test_kb_create_basic(tmp_path):
    runner = CliRunner()
    kb_dir = tmp_path / "knowledge-bases" / "test-kb"

    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code == 0
    assert kb_dir.exists()
    assert (kb_dir / ".kbconfig").exists()
    assert (kb_dir / "raw").is_dir()
    assert (kb_dir / "wiki").is_dir()
    assert (kb_dir / "outputs").is_dir()


def test_kb_create_full_structure(tmp_path):
    """Test that all subdirectories are created."""
    runner = CliRunner()
    kb_dir = tmp_path / "knowledge-bases" / "test-kb"

    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code == 0

    # Check raw subdirectories
    assert (kb_dir / "raw" / "articles").is_dir()
    assert (kb_dir / "raw" / "papers").is_dir()
    assert (kb_dir / "raw" / "books").is_dir()
    assert (kb_dir / "raw" / "videos").is_dir()
    assert (kb_dir / "raw" / "repos").is_dir()
    assert (kb_dir / "raw" / "datasets").is_dir()

    # Check wiki subdirectories
    assert (kb_dir / "wiki" / "concepts").is_dir()
    assert (kb_dir / "wiki" / "summaries" / "articles").is_dir()
    assert (kb_dir / "wiki" / "summaries" / "papers").is_dir()
    assert (kb_dir / "wiki" / "summaries" / "books").is_dir()
    assert (kb_dir / "wiki" / "summaries" / "videos").is_dir()
    assert (kb_dir / "wiki" / "topics").is_dir()
    assert (kb_dir / "wiki" / ".templates").is_dir()


def test_kb_create_templates(tmp_path):
    """Test that templates are created."""
    runner = CliRunner()
    kb_dir = tmp_path / "knowledge-bases" / "test-kb"

    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code == 0

    templates_dir = kb_dir / "wiki" / ".templates"
    assert (templates_dir / "concept-article.md").exists()
    assert (templates_dir / "article-summary.md").exists()
    assert (templates_dir / "paper-summary.md").exists()
    assert (templates_dir / "book-summary.md").exists()
    assert (templates_dir / "video-summary.md").exists()


def test_kb_create_config(tmp_path):
    """Test that config is created with correct data."""
    runner = CliRunner()
    kb_dir = tmp_path / "knowledge-bases" / "test-kb"

    result = runner.invoke(
        cli,
        ["create", "test-kb", "--vault-path", str(tmp_path), "--topic", "AI Research"]
    )

    assert result.exit_code == 0

    config_file = kb_dir / ".kbconfig"
    assert config_file.exists()

    config_data = json.loads(config_file.read_text())
    assert config_data["name"] == "test-kb"
    assert config_data["topic"] == "AI Research"
    assert "created" in config_data
    assert config_data["source_count"] == 0
    assert config_data["article_count"] == 0


def test_kb_create_already_exists(tmp_path):
    """Test error when KB already exists."""
    runner = CliRunner()

    # Create first KB
    result1 = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result1.exit_code == 0

    # Try to create again
    result2 = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result2.exit_code != 0
    assert "already exists" in result2.output
