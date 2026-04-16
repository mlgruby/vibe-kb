"""Tests for health check system."""

from pathlib import Path
from vibe_kb.health import (
    HealthIssue,
    HealthReport,
    check_dead_links,
    check_orphaned_articles,
    check_unindexed_sources,
    check_missing_metadata,
    check_template_drift,
    run_health_check,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_wiki(base: Path) -> Path:
    """Create a minimal wiki directory structure under *base*."""
    wiki = base / "wiki"
    (wiki / "concepts").mkdir(parents=True)
    (wiki / "summaries").mkdir(parents=True)
    (wiki / ".templates").mkdir(parents=True)
    return wiki


def make_kb(base: Path) -> Path:
    """Create a minimal KB directory structure under *base*."""
    make_wiki(base)
    (base / "raw").mkdir(parents=True)
    return base


# ---------------------------------------------------------------------------
# check_dead_links
# ---------------------------------------------------------------------------


def test_check_dead_links_finds_broken_links(tmp_path):
    """A [[NonExistentPage]] link in a wiki article must be flagged as a warning."""
    wiki = make_wiki(tmp_path)
    (wiki / "article.md").write_text("See also [[NonExistentPage]] for details.", encoding="utf-8")

    issues = check_dead_links(wiki)

    assert len(issues) == 1
    issue = issues[0]
    assert issue.severity == "warning"
    assert issue.check == "dead_links"
    assert "NonExistentPage" in issue.details


def test_check_dead_links_ignores_valid_links(tmp_path):
    """A [[ExistingPage]] link that resolves to a real file must not be flagged."""
    wiki = make_wiki(tmp_path)
    (wiki / "ExistingPage.md").write_text("# Existing Page", encoding="utf-8")
    (wiki / "article.md").write_text(
        "Read [[ExistingPage]] for more information.", encoding="utf-8"
    )

    issues = check_dead_links(wiki)

    assert issues == []


def test_check_dead_links_ignores_index_files(tmp_path):
    """Links to special index files (_index, _sources, _concepts) must be skipped."""
    wiki = make_wiki(tmp_path)
    (wiki / "article.md").write_text(
        "See [[_index]] and [[_sources]] and [[_concepts]].", encoding="utf-8"
    )

    issues = check_dead_links(wiki)

    # None of those should be flagged as dead links
    assert issues == []


def test_check_dead_links_self_reference_ignored(tmp_path):
    """A file referencing itself must not produce a dead-link issue."""
    wiki = make_wiki(tmp_path)
    (wiki / "MyArticle.md").write_text("Self ref: [[MyArticle]].", encoding="utf-8")

    issues = check_dead_links(wiki)

    assert issues == []


def test_check_dead_links_skips_templates(tmp_path):
    """Files inside .templates/ must not be scanned for dead links."""
    wiki = make_wiki(tmp_path)
    (wiki / ".templates" / "tpl.md").write_text("Template ref [[BrokenLink]].", encoding="utf-8")

    issues = check_dead_links(wiki)

    assert issues == []


def test_check_dead_links_multiple_broken(tmp_path):
    """Multiple broken links in one file must each be reported."""
    wiki = make_wiki(tmp_path)
    (wiki / "article.md").write_text("See [[PageA]] and [[PageB]] and [[PageC]].", encoding="utf-8")

    issues = check_dead_links(wiki)

    broken = {i.details for i in issues}
    assert "PageA" in broken
    assert "PageB" in broken
    assert "PageC" in broken


# ---------------------------------------------------------------------------
# check_orphaned_articles
# ---------------------------------------------------------------------------


def test_check_orphaned_articles_finds_orphans(tmp_path):
    """An article with no incoming wikilinks must be flagged as a suggestion."""
    wiki = make_wiki(tmp_path)
    (wiki / "orphan.md").write_text("# Orphan\nNo one links here.", encoding="utf-8")

    issues = check_orphaned_articles(wiki)

    assert len(issues) == 1
    issue = issues[0]
    assert issue.severity == "suggestion"
    assert issue.check == "orphaned_articles"
    assert "orphan" in issue.file


def test_check_orphaned_articles_ignores_linked_articles(tmp_path):
    """An article that is referenced by another article must not be flagged."""
    wiki = make_wiki(tmp_path)
    (wiki / "linked.md").write_text("# Linked Page", encoding="utf-8")
    (wiki / "parent.md").write_text("See [[linked]] for details.", encoding="utf-8")

    issues = check_orphaned_articles(wiki)

    # 'parent' has no incoming links so it is orphaned; 'linked' is not
    orphan_files = [i.file for i in issues]
    assert not any("linked.md" in f for f in orphan_files)


def test_check_orphaned_articles_skips_index_files(tmp_path):
    """Index files (_index.md, _sources.md, _concepts.md) must not be considered orphans."""
    wiki = make_wiki(tmp_path)
    (wiki / "_index.md").write_text("# Index", encoding="utf-8")
    (wiki / "_sources.md").write_text("# Sources", encoding="utf-8")
    (wiki / "_concepts.md").write_text("# Concepts", encoding="utf-8")

    issues = check_orphaned_articles(wiki)

    orphan_files = [i.file for i in issues]
    assert not any("_index" in f for f in orphan_files)
    assert not any("_sources" in f for f in orphan_files)
    assert not any("_concepts" in f for f in orphan_files)


# ---------------------------------------------------------------------------
# check_unindexed_sources
# ---------------------------------------------------------------------------


def test_check_unindexed_sources_finds_missing(tmp_path):
    """A raw source with no corresponding wiki summary must be flagged as a warning."""
    kb = make_kb(tmp_path)
    raw_dir = kb / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "my-paper.md").write_text("Raw content.", encoding="utf-8")

    issues = check_unindexed_sources(kb)

    assert len(issues) == 1
    issue = issues[0]
    assert issue.severity == "warning"
    assert issue.check == "unindexed_sources"
    assert "my-paper" in issue.file or "my-paper" in issue.details


def test_check_unindexed_sources_ignores_compiled(tmp_path):
    """A raw source that has a matching wiki summary must not be flagged."""
    kb = make_kb(tmp_path)
    wiki = kb / "wiki"
    (wiki / "summaries").mkdir(parents=True, exist_ok=True)

    # Raw source
    (kb / "raw" / "my-paper.md").write_text("Raw content.", encoding="utf-8")

    # Matching summary (slug matches)
    (wiki / "summaries" / "my-paper-summary.md").write_text(
        "## Summary\nContent here.\n\n## Key Concepts\n- [[concept]]", encoding="utf-8"
    )

    issues = check_unindexed_sources(kb)

    assert issues == []


def test_check_unindexed_sources_strips_date_prefix(tmp_path):
    """Sources with YYYY-MM-DD- date prefix must match summaries by slug without prefix."""
    kb = make_kb(tmp_path)
    wiki = kb / "wiki"
    (wiki / "summaries").mkdir(parents=True, exist_ok=True)

    # Raw source with date prefix
    (kb / "raw" / "2024-01-15-neural-nets.md").write_text("Raw content.", encoding="utf-8")

    # Summary without date prefix
    (wiki / "summaries" / "neural-nets-summary.md").write_text(
        "## Summary\nContent.\n\n## Key Concepts\n- [[foo]]", encoding="utf-8"
    )

    issues = check_unindexed_sources(kb)

    assert issues == []


# ---------------------------------------------------------------------------
# check_missing_metadata
# ---------------------------------------------------------------------------


def test_check_missing_metadata_finds_articles_without_frontmatter(tmp_path):
    """An article without a YAML frontmatter block must be flagged as a suggestion."""
    wiki = make_wiki(tmp_path)
    (wiki / "no-frontmatter.md").write_text("# My Article\nSome content here.", encoding="utf-8")

    issues = check_missing_metadata(wiki)

    assert len(issues) == 1
    issue = issues[0]
    assert issue.severity == "suggestion"
    assert issue.check == "missing_metadata"
    assert "no-frontmatter" in issue.file


def test_check_missing_metadata_ignores_articles_with_frontmatter(tmp_path):
    """An article that starts with a --- YAML block must not be flagged."""
    wiki = make_wiki(tmp_path)
    (wiki / "with-frontmatter.md").write_text(
        "---\ntype: concept\ncreated: 2024-01-01\n---\n\n# My Article\nContent.",
        encoding="utf-8",
    )

    issues = check_missing_metadata(wiki)

    assert issues == []


def test_check_missing_metadata_skips_templates(tmp_path):
    """Files in .templates/ must not be checked for missing metadata."""
    wiki = make_wiki(tmp_path)
    (wiki / ".templates" / "tpl.md").write_text("# Template\nNo frontmatter.", encoding="utf-8")

    issues = check_missing_metadata(wiki)

    assert issues == []


# ---------------------------------------------------------------------------
# check_template_drift
# ---------------------------------------------------------------------------


def test_check_template_drift_finds_missing_sections_concept(tmp_path):
    """A concept article missing ## Overview must be flagged as a suggestion."""
    wiki = make_wiki(tmp_path)
    (wiki / "concepts" / "my-concept.md").write_text(
        "---\ntype: concept\n---\n\n# My Concept\n\n## Key Ideas\n- Stuff\n\n## Sources\n- foo",
        encoding="utf-8",
    )

    issues = check_template_drift(wiki)

    assert any("Overview" in i.details or "Overview" in i.message for i in issues)
    assert all(i.severity == "suggestion" for i in issues)
    assert all(i.check == "template_drift" for i in issues)


def test_check_template_drift_finds_missing_sections_summary(tmp_path):
    """A summary article missing ## Key Concepts must be flagged."""
    wiki = make_wiki(tmp_path)
    (wiki / "summaries" / "my-summary.md").write_text(
        "---\ntype: summary\n---\n\n# My Summary\n\n## Summary\nContent here.",
        encoding="utf-8",
    )

    issues = check_template_drift(wiki)

    assert any("Key Concepts" in i.details or "Key Concepts" in i.message for i in issues)


def test_check_template_drift_passes_complete_concept(tmp_path):
    """A concept article with all required sections must not be flagged."""
    wiki = make_wiki(tmp_path)
    (wiki / "concepts" / "complete.md").write_text(
        "---\ntype: concept\n---\n\n# Complete\n\n## Overview\nDef.\n\n## Key Ideas\n- x\n\n## Sources\n- y",
        encoding="utf-8",
    )

    issues = check_template_drift(wiki)

    assert issues == []


def test_check_template_drift_passes_complete_summary(tmp_path):
    """A summary article with all required sections must not be flagged."""
    wiki = make_wiki(tmp_path)
    (wiki / "summaries" / "complete.md").write_text(
        "---\ntype: summary\n---\n\n# Complete\n\n## Summary\nContent.\n\n## Key Concepts\n- [[x]]",
        encoding="utf-8",
    )

    issues = check_template_drift(wiki)

    assert issues == []


# ---------------------------------------------------------------------------
# run_health_check (integration)
# ---------------------------------------------------------------------------


def test_run_health_check_returns_report(tmp_path):
    """Full integration: run_health_check returns a HealthReport with correct stats."""
    kb = tmp_path / "my-kb"

    # Set up KB directory structure
    wiki = kb / "wiki"
    (wiki / "concepts").mkdir(parents=True)
    (wiki / "summaries").mkdir(parents=True)
    (wiki / ".templates").mkdir(parents=True)
    raw = kb / "raw"
    raw.mkdir(parents=True)

    # Good concept article (complete)
    (wiki / "concepts" / "good-concept.md").write_text(
        "---\ntype: concept\n---\n\n# Good Concept\n\n## Overview\nDef.\n\n## Key Ideas\n- x\n\n## Sources\n- y",
        encoding="utf-8",
    )

    # Bad article: dead link
    (wiki / "article-with-dead-link.md").write_text(
        "See [[DeadTarget]] for more.", encoding="utf-8"
    )

    # Unindexed raw source
    (raw / "uncompiled-paper.md").write_text("Raw source content.", encoding="utf-8")

    report = run_health_check(kb)

    assert isinstance(report, HealthReport)
    assert report.kb_name == "my-kb"
    assert isinstance(report.checked_at, str)

    # Stats must include expected keys
    assert "wiki_articles" in report.stats
    assert "source_files" in report.stats
    assert "concept_articles" in report.stats
    assert "wikilinks_found" in report.stats
    assert "dead_links_count" in report.stats
    assert "orphaned_count" in report.stats
    assert "unindexed_sources_count" in report.stats

    # Dead link must be detected
    dead_link_issues = [i for i in report.issues if i.check == "dead_links"]
    assert len(dead_link_issues) >= 1

    # Unindexed source must be detected
    unindexed_issues = [i for i in report.issues if i.check == "unindexed_sources"]
    assert len(unindexed_issues) >= 1

    # HealthReport convenience properties
    assert isinstance(report.critical, list)
    assert isinstance(report.warnings, list)
    assert isinstance(report.suggestions, list)


def test_health_report_severity_partitioning():
    """HealthReport.critical / .warnings / .suggestions must partition issues correctly."""
    report = HealthReport(kb_name="test", checked_at="2024-01-01T00:00:00")
    report.issues = [
        HealthIssue(severity="critical", check="x", message="m", file="f", details="d"),
        HealthIssue(severity="warning", check="x", message="m", file="f", details="d"),
        HealthIssue(severity="suggestion", check="x", message="m", file="f", details="d"),
        HealthIssue(severity="warning", check="x", message="m", file="f", details="d"),
    ]

    assert len(report.critical) == 1
    assert len(report.warnings) == 2
    assert len(report.suggestions) == 1
