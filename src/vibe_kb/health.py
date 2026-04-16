"""Health check system for knowledge base wiki maintenance."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class HealthIssue:
    """A single health check finding."""

    severity: str  # "critical", "warning", "suggestion"
    check: str  # check name, e.g. "dead_links"
    message: str  # human-readable description
    file: str  # relative path to affected file (empty string if N/A)
    details: str  # extra context (e.g. which links are dead)


@dataclass
class HealthReport:
    """Full health check report for a knowledge base."""

    kb_name: str
    checked_at: str
    issues: List[HealthIssue] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)

    @property
    def critical(self) -> List[HealthIssue]:
        """Return only critical-severity issues."""
        return [i for i in self.issues if i.severity == "critical"]

    @property
    def warnings(self) -> List[HealthIssue]:
        """Return only warning-severity issues."""
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def suggestions(self) -> List[HealthIssue]:
        """Return only suggestion-severity issues."""
        return [i for i in self.issues if i.severity == "suggestion"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:\|[^\]]*)?\]\]")
_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")
_INDEX_NAMES: Set[str] = {"_index", "_sources", "_concepts"}


def _is_excluded(path: Path, base_dir: Path) -> bool:
    """Return True if *path* should be skipped during wiki scanning.

    A path is excluded when:
    - It is a symlink (security: prevents path-traversal exploits).
    - Its filename starts with '.' or '_'.
    - Any parent directory relative to *base_dir* starts with '.' or '_'.
    """
    if path.is_symlink():
        return True
    if path.name.startswith((".", "_")):
        return True
    try:
        relative = path.relative_to(base_dir)
        for part in relative.parts[:-1]:  # directory components only
            if part.startswith((".", "_")):
                return True
    except ValueError:
        return True
    return False


def _read_text(path: Path) -> str:
    """Read *path* as UTF-8, returning empty string on any error."""
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError, OSError):
        return ""


def _wiki_articles(wiki_dir: Path) -> List[Path]:
    """Return all non-excluded .md files under *wiki_dir*."""
    results: List[Path] = []
    for md_file in wiki_dir.rglob("*.md"):
        if not _is_excluded(md_file, wiki_dir):
            results.append(md_file)
    return results


def _extract_wikilinks(text: str) -> List[str]:
    """Extract wikilink targets from *text* (the [[Target]] part)."""
    return _WIKILINK_RE.findall(text)


def _all_article_stems(wiki_dir: Path) -> Set[str]:
    """Return a set of lowercased stems of all .md files under *wiki_dir* (non-excluded)."""
    stems: Set[str] = set()
    for article in _wiki_articles(wiki_dir):
        stems.add(article.stem.lower())
    return stems


def _strip_date_prefix(name: str) -> str:
    """Remove a leading YYYY-MM-DD- date prefix from *name* if present."""
    return _DATE_PREFIX_RE.sub("", name)


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def check_dead_links(wiki_dir: Path) -> List[HealthIssue]:
    """Scan wiki articles for [[wikilinks]] that resolve to no existing file.

    Args:
        wiki_dir: Path to the wiki directory.

    Returns:
        List of HealthIssue with severity "warning" and check "dead_links".
    """
    issues: List[HealthIssue] = []
    known_stems = _all_article_stems(wiki_dir)

    for article in _wiki_articles(wiki_dir):
        text = _read_text(article)
        if not text:
            continue

        rel = str(article.relative_to(wiki_dir))
        for target in _extract_wikilinks(text):
            target_clean = target.strip()

            # Skip self-references
            if target_clean.lower() == article.stem.lower():
                continue

            # Skip special index files
            if target_clean.lower() in _INDEX_NAMES:
                continue

            if target_clean.lower() not in known_stems:
                issues.append(
                    HealthIssue(
                        severity="warning",
                        check="dead_links",
                        message=f"Dead wikilink [[{target_clean}]] in {rel}",
                        file=rel,
                        details=target_clean,
                    )
                )

    return issues


def check_orphaned_articles(wiki_dir: Path) -> List[HealthIssue]:
    """Find wiki articles with no incoming wikilinks from any other article.

    Args:
        wiki_dir: Path to the wiki directory.

    Returns:
        List of HealthIssue with severity "suggestion" and check "orphaned_articles".
    """
    issues: List[HealthIssue] = []
    articles = _wiki_articles(wiki_dir)

    # Collect all stems that are the target of at least one wikilink
    referenced_stems: Set[str] = set()
    for article in articles:
        text = _read_text(article)
        for target in _extract_wikilinks(text):
            referenced_stems.add(target.strip().lower())

    for article in articles:
        stem = article.stem

        # Skip index files
        if stem.lower() in _INDEX_NAMES:
            continue

        if stem.lower() not in referenced_stems:
            rel = str(article.relative_to(wiki_dir))
            issues.append(
                HealthIssue(
                    severity="suggestion",
                    check="orphaned_articles",
                    message=f"Article '{stem}' has no incoming wikilinks",
                    file=rel,
                    details=f"Consider linking to '{stem}' from related articles.",
                )
            )

    return issues


def check_unindexed_sources(kb_dir: Path) -> List[HealthIssue]:
    """Find source files in raw/ that have no corresponding wiki summary.

    Matching logic: strip the YYYY-MM-DD- date prefix and extension from the
    raw filename to produce a slug, then check whether any file under
    wiki/summaries/ contains that slug in its stem.

    Args:
        kb_dir: Path to the knowledge base root directory.

    Returns:
        List of HealthIssue with severity "warning" and check "unindexed_sources".
    """
    issues: List[HealthIssue] = []
    raw_dir = kb_dir / "raw"
    summaries_dir = kb_dir / "wiki" / "summaries"

    if not raw_dir.exists():
        return issues

    # Collect all summary stems (lowercased) for fast lookup
    summary_stems: Set[str] = set()
    if summaries_dir.exists():
        for summary in summaries_dir.rglob("*.md"):
            if not summary.is_symlink():
                summary_stems.add(summary.stem.lower())

    # Supported raw source extensions
    source_extensions = {".md", ".pdf", ".epub"}

    for source in raw_dir.rglob("*"):
        if source.is_symlink() or source.is_dir():
            continue
        if source.suffix.lower() not in source_extensions:
            continue
        if source.name.startswith((".", "_")):
            continue

        raw_name = source.stem  # e.g. "2024-01-15-neural-nets" or "my-paper"
        slug = _strip_date_prefix(raw_name).lower()  # e.g. "neural-nets" or "my-paper"

        # Check if any summary stem contains the slug
        matched = any(slug in stem for stem in summary_stems)

        if not matched:
            rel = str(source.relative_to(kb_dir))
            issues.append(
                HealthIssue(
                    severity="warning",
                    check="unindexed_sources",
                    message=f"Source '{source.name}' has no wiki summary",
                    file=rel,
                    details=slug,
                )
            )

    return issues


def check_missing_metadata(wiki_dir: Path) -> List[HealthIssue]:
    """Scan wiki articles for missing YAML frontmatter.

    An article is considered to have frontmatter when it starts with a '---'
    block (the file's very first non-empty bytes are '---').

    Args:
        wiki_dir: Path to the wiki directory.

    Returns:
        List of HealthIssue with severity "suggestion" and check "missing_metadata".
    """
    issues: List[HealthIssue] = []

    for article in _wiki_articles(wiki_dir):
        text = _read_text(article)
        if not text:
            continue

        if not text.startswith("---"):
            rel = str(article.relative_to(wiki_dir))
            issues.append(
                HealthIssue(
                    severity="suggestion",
                    check="missing_metadata",
                    message=f"Article '{article.stem}' is missing YAML frontmatter",
                    file=rel,
                    details="Add a --- frontmatter block with type, created, and related fields.",
                )
            )

    return issues


def check_template_drift(wiki_dir: Path) -> List[HealthIssue]:
    """Check that concept and summary articles contain required sections.

    Concept articles (wiki/concepts/*.md) must have:
        ## Overview, ## Key Ideas, ## Sources

    Summary articles (wiki/summaries/**/*.md) must have:
        ## Summary, ## Key Concepts

    Args:
        wiki_dir: Path to the wiki directory.

    Returns:
        List of HealthIssue with severity "suggestion" and check "template_drift".
    """
    issues: List[HealthIssue] = []

    concepts_dir = wiki_dir / "concepts"
    summaries_dir = wiki_dir / "summaries"

    concept_required = ["## Overview", "## Key Ideas", "## Sources"]
    summary_required = ["## Summary", "## Key Concepts"]

    def _check_sections(path: Path, required: List[str]) -> None:
        if path.is_symlink() or path.name.startswith((".", "_")):
            return
        text = _read_text(path)
        if not text:
            return
        missing = [sec for sec in required if sec not in text]
        if missing:
            rel = str(path.relative_to(wiki_dir))
            issues.append(
                HealthIssue(
                    severity="suggestion",
                    check="template_drift",
                    message=f"Article '{path.stem}' is missing required sections",
                    file=rel,
                    details=", ".join(missing),
                )
            )

    if concepts_dir.exists():
        for md_file in concepts_dir.glob("*.md"):
            _check_sections(md_file, concept_required)

    if summaries_dir.exists():
        for md_file in summaries_dir.rglob("*.md"):
            _check_sections(md_file, summary_required)

    return issues


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------


def run_health_check(kb_dir: Path) -> HealthReport:
    """Run all health checks against a knowledge base and return a HealthReport.

    Args:
        kb_dir: Path to the knowledge base root directory (contains wiki/ and raw/).

    Returns:
        HealthReport with all issues and summary statistics.
    """
    wiki_dir = kb_dir / "wiki"
    raw_dir = kb_dir / "raw"

    # Collect issues from all checks (wiki may not exist yet → graceful)
    all_issues: List[HealthIssue] = []

    if wiki_dir.exists():
        all_issues.extend(check_dead_links(wiki_dir))
        all_issues.extend(check_orphaned_articles(wiki_dir))
        all_issues.extend(check_missing_metadata(wiki_dir))
        all_issues.extend(check_template_drift(wiki_dir))

    all_issues.extend(check_unindexed_sources(kb_dir))

    # Compute stats
    wiki_articles = 0
    concept_articles = 0
    wikilinks_found = 0
    dead_links_count = 0
    orphaned_count = 0

    if wiki_dir.exists():
        articles = _wiki_articles(wiki_dir)
        wiki_articles = len(articles)

        concepts_dir = wiki_dir / "concepts"
        if concepts_dir.exists():
            concept_articles = sum(
                1
                for f in concepts_dir.glob("*.md")
                if not f.is_symlink() and not f.name.startswith((".", "_"))
            )

        for article in articles:
            text = _read_text(article)
            wikilinks_found += len(_extract_wikilinks(text))

    dead_links_count = sum(1 for i in all_issues if i.check == "dead_links")
    orphaned_count = sum(1 for i in all_issues if i.check == "orphaned_articles")

    source_files = 0
    unindexed_sources_count = 0
    source_extensions = {".md", ".pdf", ".epub"}
    if raw_dir.exists():
        source_files = sum(
            1
            for f in raw_dir.rglob("*")
            if not f.is_symlink()
            and not f.is_dir()
            and f.suffix.lower() in source_extensions
            and not f.name.startswith((".", "_"))
        )
    unindexed_sources_count = sum(1 for i in all_issues if i.check == "unindexed_sources")

    stats: Dict = {
        "wiki_articles": wiki_articles,
        "source_files": source_files,
        "concept_articles": concept_articles,
        "wikilinks_found": wikilinks_found,
        "dead_links_count": dead_links_count,
        "orphaned_count": orphaned_count,
        "unindexed_sources_count": unindexed_sources_count,
    }

    return HealthReport(
        kb_name=kb_dir.name,
        checked_at=datetime.now().isoformat(),
        issues=all_issues,
        stats=stats,
    )
