"""Tests for KB configuration management."""

import json
from vibe_kb.config import KBConfig


def test_create_new_config(tmp_path):
    kb_dir = tmp_path / "test-kb"
    kb_dir.mkdir()

    config = KBConfig.create(kb_dir, name="test-kb", topic="Testing")

    assert config.name == "test-kb"
    assert config.topic == "Testing"
    assert config.kb_path == kb_dir
    assert (kb_dir / ".kbconfig").exists()


def test_load_existing_config(tmp_path):
    kb_dir = tmp_path / "test-kb"
    kb_dir.mkdir()

    # Create config file
    config_data = {
        "name": "test-kb",
        "topic": "Testing",
        "created": "2026-04-15T10:00:00",
        "last_compile": None,
        "source_count": 0,
        "article_count": 0,
    }
    (kb_dir / ".kbconfig").write_text(json.dumps(config_data, indent=2))

    config = KBConfig.load(kb_dir)
    assert config.name == "test-kb"
    assert config.topic == "Testing"


def test_update_stats(tmp_path):
    kb_dir = tmp_path / "test-kb"
    kb_dir.mkdir()

    config = KBConfig.create(kb_dir, name="test-kb", topic="Testing")
    config.update_stats(source_count=5, article_count=3)

    assert config.source_count == 5
    assert config.article_count == 3

    # Verify it's saved to disk
    reloaded = KBConfig.load(kb_dir)
    assert reloaded.source_count == 5
    assert reloaded.article_count == 3


def test_mark_compiled(tmp_path):
    kb_dir = tmp_path / "test-kb"
    kb_dir.mkdir()

    config = KBConfig.create(kb_dir, name="test-kb", topic="Testing")
    assert config.last_compile is None

    config.mark_compiled()
    assert config.last_compile is not None

    # Verify it's saved to disk
    reloaded = KBConfig.load(kb_dir)
    assert reloaded.last_compile is not None


def test_config_file_format(tmp_path):
    """Test that .kbconfig doesn't include kb_path."""
    kb_dir = tmp_path / "test-kb"
    kb_dir.mkdir()

    KBConfig.create(kb_dir, name="test-kb", topic="Testing")

    config_file = kb_dir / ".kbconfig"
    saved_data = json.loads(config_file.read_text())

    assert "kb_path" not in saved_data
    assert "name" in saved_data
    assert "topic" in saved_data
    assert "created" in saved_data


def test_load_nonexistent_config(tmp_path):
    """Test loading config from directory without .kbconfig."""
    kb_dir = tmp_path / "test-kb"
    kb_dir.mkdir()

    try:
        KBConfig.load(kb_dir)
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError as e:
        assert ".kbconfig" in str(e)
