"""Tests for file utilities."""
import json
from datetime import date
import pytest
from vibe_kb.utils.files import generate_filename, create_metadata


def test_generate_filename_from_title():
    result = generate_filename("Attention Is All You Need")
    expected = f"{date.today().isoformat()}-attention-is-all-you-need.md"
    assert result == expected


def test_generate_filename_removes_special_chars():
    result = generate_filename("GPT-4: The Next Generation!")
    expected = f"{date.today().isoformat()}-gpt-4-the-next-generation.md"
    assert result == expected


def test_generate_filename_rejects_empty_title():
    with pytest.raises(ValueError, match="Title cannot be empty"):
        generate_filename("")

    with pytest.raises(ValueError, match="Title cannot be empty"):
        generate_filename("   ")


def test_create_metadata(tmp_path):
    target = tmp_path / "test.meta.json"
    create_metadata(
        target,
        source_url="https://example.com/article",
        source_type="article",
        title="Test Article",
        author="John Doe"
    )

    assert target.exists()
    data = json.loads(target.read_text())
    assert data["source_url"] == "https://example.com/article"
    assert data["source_type"] == "article"
    assert data["title"] == "Test Article"
    assert data["author"] == "John Doe"
    assert "added_date" in data


def test_generate_filename_raises_for_punctuation_only_title():
    """Title that sanitizes to empty slug (e.g. only punctuation) must raise."""
    with pytest.raises(ValueError, match="alphanumeric"):
        generate_filename("!!!")


def test_generate_filename_raises_for_emoji_only_title():
    """Emoji-only title produces empty slug and must raise."""
    with pytest.raises(ValueError, match="alphanumeric"):
        generate_filename("🎉🚀✨")
