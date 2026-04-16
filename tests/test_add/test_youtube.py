"""Tests for YouTube transcript extraction."""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from vibe_kb.add.youtube import extract_youtube_transcript, _parse_vtt
from vibe_kb.cli import cli


# Sample VTT content for testing
SAMPLE_VTT = """WEBVTT

00:00:00.000 --> 00:00:05.000
Hello everyone! Welcome to this video.

00:00:05.000 --> 00:00:10.000
Today we will be discussing knowledge bases.

00:00:10.000 --> 00:00:15.000
They are very useful for organizing information.
"""


def test_parse_vtt_basic():
    """Test basic VTT parsing."""
    transcript = _parse_vtt(SAMPLE_VTT)

    assert "Hello everyone" in transcript
    assert "knowledge bases" in transcript
    assert "organizing information" in transcript
    # Should not contain timestamps
    assert "-->" not in transcript
    assert "WEBVTT" not in transcript


def test_parse_vtt_with_html_tags():
    """Test VTT parsing with HTML tags."""
    vtt_with_tags = """WEBVTT

00:00:00.000 --> 00:00:05.000
<c>This has tags</c>

00:00:05.000 --> 00:00:10.000
<v Speaker>Multiple speakers</v>
"""

    transcript = _parse_vtt(vtt_with_tags)

    assert "This has tags" in transcript
    assert "Multiple speakers" in transcript
    # Should not contain HTML tags
    assert "<c>" not in transcript
    assert "<v>" not in transcript


def test_parse_vtt_empty():
    """Test VTT parsing with empty content."""
    vtt_empty = """WEBVTT

00:00:00.000 --> 00:00:05.000


00:00:05.000 --> 00:00:10.000

"""

    transcript = _parse_vtt(vtt_empty)

    # Should return empty or whitespace-only string
    assert transcript.strip() == ""


def test_extract_youtube_transcript_basic(tmp_path):
    """Test basic YouTube transcript extraction."""
    output_path = tmp_path / "video.md"

    # Mock yt_dlp
    with patch("vibe_kb.add.youtube.yt_dlp.YoutubeDL") as mock_ydl_class:
        # Create mock objects
        mock_ydl = MagicMock()
        mock_urlopen_obj = MagicMock()
        mock_urlopen_obj.read.return_value = SAMPLE_VTT.encode("utf-8")

        # Set up the info dict
        mock_info = {
            "title": "Test Video",
            "channel": "Test Channel",
            "duration": 125,  # 2:05
            "upload_date": "20240101",
            "description": "Test description",
            "subtitles": {"en": [{"url": "http://example.com/subs.vtt"}]},
        }

        mock_ydl.extract_info.return_value = mock_info
        mock_ydl.urlopen.return_value = mock_urlopen_obj
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        result = extract_youtube_transcript("https://www.youtube.com/watch?v=test123", output_path)

        # Check return value
        assert result["title"] == "Test Video"
        assert result["channel"] == "Test Channel"
        assert result["duration"] == 125
        assert result["url"] == "https://www.youtube.com/watch?v=test123"

        # Check output file
        assert output_path.exists()
        content = output_path.read_text()
        assert "# Test Video" in content
        assert "**Channel:** Test Channel" in content
        assert "**Duration:** 2:05" in content
        assert "**Upload Date:** 20240101" in content
        assert "Test description" in content
        assert "Hello everyone" in content


def test_extract_youtube_transcript_with_automatic_captions(tmp_path):
    """Test YouTube extraction with automatic captions fallback."""
    output_path = tmp_path / "video.md"

    with patch("vibe_kb.add.youtube.yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_urlopen_obj = MagicMock()
        mock_urlopen_obj.read.return_value = SAMPLE_VTT.encode("utf-8")

        # No manual subtitles, only automatic captions
        mock_info = {
            "title": "Auto Caption Video",
            "channel": "Test Channel",
            "duration": 60,
            "upload_date": "20240101",
            "description": "Test",
            "subtitles": {},  # No manual subtitles
            "automatic_captions": {"en": [{"url": "http://example.com/auto.vtt"}]},
        }

        mock_ydl.extract_info.return_value = mock_info
        mock_ydl.urlopen.return_value = mock_urlopen_obj
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        result = extract_youtube_transcript("https://www.youtube.com/watch?v=test456", output_path)

        assert result["title"] == "Auto Caption Video"
        assert output_path.exists()


def test_extract_youtube_transcript_no_subtitles(tmp_path):
    """Test handling of video with no subtitles."""
    output_path = tmp_path / "video.md"

    with patch("vibe_kb.add.youtube.yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()

        # No subtitles at all
        mock_info = {
            "title": "No Subs Video",
            "channel": "Test Channel",
            "duration": 60,
            "upload_date": "20240101",
            "description": "Test",
            "subtitles": {},
            "automatic_captions": {},
        }

        mock_ydl.extract_info.return_value = mock_info
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        with pytest.raises(ValueError) as exc_info:
            extract_youtube_transcript("https://www.youtube.com/watch?v=nosubs", output_path)

        assert "no english subtitles available" in str(exc_info.value).lower()


def test_extract_youtube_transcript_invalid_url(tmp_path):
    """Test handling of invalid YouTube URL."""
    output_path = tmp_path / "video.md"

    with patch("vibe_kb.add.youtube.yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = Exception("Invalid URL")
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        with pytest.raises(ValueError) as exc_info:
            extract_youtube_transcript("https://invalid-url.com", output_path)

        assert "failed to extract" in str(exc_info.value).lower()


def test_extract_youtube_transcript_network_error(tmp_path):
    """Test handling of network errors."""
    output_path = tmp_path / "video.md"

    with patch("vibe_kb.add.youtube.yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = Exception("Network error")
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        with pytest.raises(ValueError) as exc_info:
            extract_youtube_transcript("https://www.youtube.com/watch?v=test", output_path)

        error_msg = str(exc_info.value).lower()
        assert "failed" in error_msg or "error" in error_msg


def test_cli_add_youtube_integration(tmp_path):
    """Test CLI integration for adding YouTube video."""
    runner = CliRunner()

    # Create KB first
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    # Mock YouTube extraction
    with patch("vibe_kb.add.youtube.yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_urlopen_obj = MagicMock()
        mock_urlopen_obj.read.return_value = SAMPLE_VTT.encode("utf-8")

        mock_info = {
            "title": "CLI Test Video",
            "channel": "CLI Test Channel",
            "duration": 300,
            "upload_date": "20240101",
            "description": "CLI test description",
            "subtitles": {"en": [{"url": "http://example.com/subs.vtt"}]},
        }

        mock_ydl.extract_info.return_value = mock_info
        mock_ydl.urlopen.return_value = mock_urlopen_obj
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        # Add YouTube video to KB
        result = runner.invoke(
            cli,
            [
                "add",
                "test-kb",
                "--youtube",
                "https://www.youtube.com/watch?v=test123",
                "--vault-path",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0
        assert "Added video: CLI Test Video" in result.output
        assert "Channel: CLI Test Channel" in result.output

        # Check files were created
        kb_dir = tmp_path / "knowledge-bases" / "test-kb"
        videos_dir = kb_dir / "raw" / "videos"
        assert videos_dir.exists()

        # Check markdown file exists
        md_files = list(videos_dir.glob("*.md"))
        assert len(md_files) == 1

        # Check metadata file exists
        meta_files = list(videos_dir.glob("*.meta.json"))
        assert len(meta_files) == 1


def test_cli_add_youtube_no_subtitles(tmp_path):
    """Test CLI handling of video with no subtitles."""
    runner = CliRunner()

    # Create KB first
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    with patch("vibe_kb.add.youtube.yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()

        mock_info = {
            "title": "No Subs",
            "channel": "Test",
            "duration": 60,
            "upload_date": "20240101",
            "description": "Test",
            "subtitles": {},
            "automatic_captions": {},
        }

        mock_ydl.extract_info.return_value = mock_info
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        result = runner.invoke(
            cli,
            [
                "add",
                "test-kb",
                "--youtube",
                "https://www.youtube.com/watch?v=nosubs",
                "--vault-path",
                str(tmp_path),
            ],
        )

        assert result.exit_code != 0
        assert "error" in result.output.lower()


def test_extract_youtube_subtitle_download_failure(tmp_path):
    """Test handling subtitle download failure after info extraction succeeds."""
    output_path = tmp_path / "video.md"

    with patch("vibe_kb.add.youtube.yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()

        # Info extraction succeeds
        mock_info = {
            "title": "Test Video",
            "channel": "Test Channel",
            "duration": 300,
            "upload_date": "20240101",
            "description": "Test description",
            "subtitles": {"en": [{"url": "http://example.com/subtitle.vtt"}]},
            "automatic_captions": {},
        }

        mock_ydl.extract_info.return_value = mock_info
        # Simulate urlopen failure during subtitle download
        mock_ydl.urlopen.side_effect = Exception("Network error during subtitle download")
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        with pytest.raises(ValueError) as exc_info:
            extract_youtube_transcript("https://youtube.com/watch?v=test", output_path)

        assert "failed to extract" in str(exc_info.value).lower()


def test_cli_add_youtube_invalid_url(tmp_path):
    """Test CLI error handling for invalid YouTube URL."""
    runner = CliRunner()

    # Create KB first
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    # Try to add with invalid URL
    result = runner.invoke(
        cli, ["add", "test-kb", "--youtube", "not-a-url", "--vault-path", str(tmp_path)]
    )

    assert result.exit_code != 0
    assert "invalid" in result.output.lower()


def test_cli_add_no_source_specified(tmp_path):
    """Test CLI error when no source is specified."""
    runner = CliRunner()

    # Create KB first
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    # Try to add without specifying source
    result = runner.invoke(cli, ["add", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code != 0
    assert "no source specified" in result.output.lower()


def test_cli_add_youtube_rejects_non_youtube_https(tmp_path):
    """Test that https://example.com is rejected (URL logic bug fix)."""
    runner = CliRunner()

    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        [
            "add",
            "test-kb",
            "--youtube",
            "https://example.com/watch?v=dQw4w9WgXcQ",
            "--vault-path",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "invalid" in result.output.lower()


def test_cli_add_youtube_duplicate_preserves_existing(tmp_path):
    """Duplicate add must not delete the pre-existing source or metadata."""
    from unittest.mock import patch

    runner = CliRunner()
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    videos_dir = kb_dir / "raw" / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    # Freeze date so the pre-planted filename matches what generate_filename()
    # produces inside the CLI. Without this, a midnight boundary between the
    # two date.today() calls causes the duplicate check to miss and the test
    # to fail spuriously.
    from datetime import date

    frozen_date = date(2026, 1, 15)
    existing_filename = f"{frozen_date.isoformat()}-existing-video.md"
    existing_md = videos_dir / existing_filename
    existing_meta = videos_dir / existing_filename.replace(".md", ".meta.json")
    existing_md.write_text("ORIGINAL CONTENT", encoding="utf-8")
    existing_meta.write_text('{"title": "Existing Video"}', encoding="utf-8")

    mock_result = {
        "title": "Existing Video",
        "channel": "Test Channel",
        "duration": 300,
        "url": "https://youtube.com/watch?v=test",
    }

    with patch("vibe_kb.utils.files.date") as mock_date:
        mock_date.today.return_value = frozen_date
        with patch("vibe_kb.cli.extract_youtube_transcript", return_value=mock_result):
            result = runner.invoke(
                cli,
                [
                    "add",
                    "test-kb",
                    "--youtube",
                    "https://youtube.com/watch?v=test",
                    "--vault-path",
                    str(tmp_path),
                ],
            )

    assert result.exit_code != 0
    assert "already exists" in result.output

    # Original files must be intact
    assert existing_md.exists(), "Pre-existing markdown was deleted"
    assert existing_md.read_text(encoding="utf-8") == "ORIGINAL CONTENT"
    assert existing_meta.exists(), "Pre-existing metadata was deleted"


def test_parse_vtt_empty_returns_empty_string():
    """VTT with only headers/timestamps and no caption text parses to empty string."""
    vtt_header_only = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n\n00:00:03.000 --> 00:00:04.000\n"
    result = _parse_vtt(vtt_header_only)
    assert result.strip() == ""


def test_extract_youtube_raises_for_empty_transcript(tmp_path):
    """extract_youtube_transcript must raise ValueError when parsed transcript is empty."""
    from unittest.mock import patch, MagicMock

    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = {
        "title": "Music Video",
        "channel": "Artist",
        "duration": 200,
        "upload_date": "20240101",
        "description": "A music video",
        "subtitles": {"en": [{"url": "http://example.com/sub.vtt"}]},
        "automatic_captions": {},
    }
    # Subtitle file contains only timestamps — parses to empty transcript
    mock_ydl.urlopen.return_value.read.return_value = (
        b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n\n00:00:03.000 --> 00:00:04.000\n"
    )

    with patch("vibe_kb.add.youtube.yt_dlp.YoutubeDL") as mock_ytdl:
        mock_ytdl.return_value.__enter__.return_value = mock_ydl
        with pytest.raises(ValueError, match="no usable transcript"):
            extract_youtube_transcript("https://youtube.com/watch?v=music", tmp_path / "out.md")
