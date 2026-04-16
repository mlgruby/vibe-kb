"""YouTube transcript extraction."""

import yt_dlp
from pathlib import Path
from typing import Dict, Any
import re


def extract_youtube_transcript(url: str, output_path: Path) -> Dict[str, Any]:
    """Extract YouTube video transcript to markdown.

    Args:
        url: YouTube video URL
        output_path: Path to output .md file

    Returns:
        Dictionary with metadata

    Raises:
        ValueError: If extraction fails or no subtitles are available
    """
    ydl_opts = {
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "skip_download": True,
        "quiet": True,
        "socket_timeout": 30,  # Prevent indefinite hangs
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            title = info.get("title", "Unknown")
            channel = info.get("channel", "Unknown")
            duration = info.get("duration", 0)
            upload_date = info.get("upload_date", "Unknown")
            description = info.get("description", "")

            # Get subtitles (prefer manual subtitles, fall back to automatic)
            subtitles = info.get("subtitles", {}).get("en") or info.get(
                "automatic_captions", {}
            ).get("en")

            if not subtitles:
                raise ValueError("No English subtitles available for this video")

            # Download subtitle content (reuse same YoutubeDL instance)
            subtitle_url = subtitles[0]["url"]
            subtitle_content = ydl.urlopen(subtitle_url).read().decode("utf-8")

            # Parse VTT format
            transcript = _parse_vtt(subtitle_content)

            # Write markdown
            markdown = f"# {title}\n\n"
            markdown += f"**Channel:** {channel}\n"
            markdown += f"**Duration:** {duration // 60}:{duration % 60:02d}\n"
            markdown += f"**Upload Date:** {upload_date}\n"
            markdown += f"**URL:** {url}\n\n"
            markdown += "---\n\n"
            markdown += f"## Description\n\n{description}\n\n"
            markdown += "---\n\n"
            markdown += "## Transcript\n\n"
            markdown += transcript

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown, encoding="utf-8")

            return {"title": title, "channel": channel, "duration": duration, "url": url}
    except ValueError:
        # Re-raise ValueError (from subtitle check) as-is
        raise
    except Exception as e:
        # Wrap other exceptions in ValueError with context
        raise ValueError(f"Failed to extract video information: {str(e)}")


def _parse_vtt(vtt_content: str) -> str:
    """Parse VTT subtitle format to plain text.

    Args:
        vtt_content: VTT subtitle content

    Returns:
        Plain text transcript
    """
    # Remove VTT header
    lines = vtt_content.split("\n")
    text_lines = []

    for line in lines:
        line = line.strip()
        # Skip empty lines, timestamps, and VTT headers
        if not line or "-->" in line or line.startswith("WEBVTT") or line.isdigit():
            continue
        # Remove HTML tags
        line = re.sub(r"<[^>]+>", "", line)
        if line:
            text_lines.append(line)

    # Join and clean up
    transcript = " ".join(text_lines)
    # Remove duplicate spaces
    transcript = re.sub(r"\s+", " ", transcript)

    return transcript
