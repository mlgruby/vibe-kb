"""Wiki search functionality."""
from pathlib import Path
from typing import List, Dict
import re


def search_wiki(wiki_dir: Path, query: str, case_sensitive: bool = False) -> List[Dict]:
    """Search wiki markdown files for query string.

    Args:
        wiki_dir: Path to wiki directory
        query: Search query
        case_sensitive: Whether search is case-sensitive

    Returns:
        List of matches with file path, line number, and matching line

    Raises:
        ValueError: If query is empty or directory doesn't exist
    """
    # Validate inputs
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    if not wiki_dir.exists():
        raise ValueError(f"Wiki directory not found: {wiki_dir}")

    if not wiki_dir.is_dir():
        raise ValueError(f"Path is not a directory: {wiki_dir}")

    results = []

    # Compile regex pattern
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        # Escape special regex characters for literal search
        pattern = re.compile(re.escape(query), flags)
    except re.error as e:
        raise ValueError(f"Invalid search pattern: {e}")

    # Search all .md files recursively
    for md_file in wiki_dir.rglob("*.md"):
        # Skip hidden files and symlinks for security
        if md_file.name.startswith('.') or md_file.is_symlink():
            continue

        try:
            content = md_file.read_text(encoding='utf-8')
        except (UnicodeDecodeError, PermissionError, OSError) as e:
            # Skip files with read errors (binary files, permission issues, etc.)
            continue

        # Search each line
        for line_num, line in enumerate(content.splitlines(), 1):
            if pattern.search(line):
                results.append({
                    'file': str(md_file.relative_to(wiki_dir)),
                    'line': line_num,
                    'match': line.strip()
                })

    return results
