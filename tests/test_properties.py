"""Property-based tests using Hypothesis.

These tests encode invariants that must hold for ALL inputs, not just
the specific examples we thought of. They are especially valuable for
security-sensitive functions (name validation, path construction) and
string-processing functions (slug generation, VTT parsing) where
edge cases are hard to enumerate by hand.
"""
import re
import tempfile
from datetime import date
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, assume, settings
from hypothesis import strategies as st

from vibe_kb.utils.files import generate_filename
from vibe_kb.add.youtube import _parse_vtt
from vibe_kb.cli import _validate_kb_name, _KB_NAME_RE
from vibe_kb.search import search_wiki


# ---------------------------------------------------------------------------
# generate_filename
# ---------------------------------------------------------------------------

# Strategy: printable text that contains at least one ASCII alnum char
# (so the slug won't be empty — we test the empty-slug path separately)
_titles_with_alnum = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S", "Zs")),
    min_size=1,
).filter(lambda t: re.search(r'[a-zA-Z0-9]', t))


@given(_titles_with_alnum)
@settings(max_examples=300)
def test_generate_filename_always_starts_with_today(title):
    """Output must always begin with today's ISO date."""
    result = generate_filename(title)
    assert result.startswith(date.today().isoformat()), (
        f"filename {result!r} does not start with today's date for title {title!r}"
    )


@given(_titles_with_alnum)
@settings(max_examples=300)
def test_generate_filename_never_contains_path_separator(title):
    """Output must never contain / or \\ regardless of title content."""
    result = generate_filename(title)
    assert "/" not in result, f"/ in filename {result!r} for title {title!r}"
    assert "\\" not in result, f"\\ in filename {result!r} for title {title!r}"


@given(_titles_with_alnum)
@settings(max_examples=300)
def test_generate_filename_always_ends_with_md(title):
    """Default extension must always be .md."""
    result = generate_filename(title)
    assert result.endswith(".md"), f"filename {result!r} does not end with .md"


@given(_titles_with_alnum)
@settings(max_examples=300)
def test_generate_filename_slug_only_safe_chars(title):
    """The slug portion must contain only [a-z0-9-]."""
    result = generate_filename(title)
    # Strip date prefix (YYYY-MM-DD-) and .md suffix to get slug
    slug = result[len(date.today().isoformat()) + 1 : -len(".md")]
    assert re.fullmatch(r'[a-z0-9-]+', slug), (
        f"slug {slug!r} contains unsafe characters for title {title!r}"
    )


@given(
    st.text(
        alphabet=st.characters(blacklist_categories=("L", "N"), blacklist_characters="-_ \t\n"),
        min_size=1,
    )
)
@settings(max_examples=100)
def test_generate_filename_raises_for_no_alnum(title):
    """Titles with no alphanumeric characters must raise ValueError."""
    assume(title.strip())  # exclude whitespace-only (raises different message)
    with pytest.raises(ValueError):
        generate_filename(title)


# ---------------------------------------------------------------------------
# _validate_kb_name
# ---------------------------------------------------------------------------

_valid_name_chars = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"),
    min_size=1,
).filter(lambda n: n[0].isalnum())


@given(_valid_name_chars)
@settings(max_examples=300)
def test_validate_kb_name_accepts_valid_names(name):
    """Any name matching the slug pattern must be accepted without raising."""
    # _validate_kb_name calls click.Abort on failure; we test it doesn't raise
    try:
        _validate_kb_name(name)  # should not raise
    except SystemExit:
        pytest.fail(f"_validate_kb_name raised Abort for valid name {name!r}")


@given(
    st.one_of(
        # names containing forward slash
        st.from_regex(r'[A-Za-z0-9][A-Za-z0-9_-]*/[A-Za-z0-9_-]+', fullmatch=True),
        # names containing backslash
        st.from_regex(r'[A-Za-z0-9][A-Za-z0-9_-]*\\[A-Za-z0-9_-]+', fullmatch=True),
        # names starting with dot (relative path escape)
        st.from_regex(r'\.[A-Za-z0-9_-]+', fullmatch=True),
        # names starting with ..
        st.just(".."),
        st.from_regex(r'\.\.[A-Za-z0-9_/-]*', fullmatch=True),
    )
)
@settings(max_examples=200)
def test_validate_kb_name_rejects_path_traversal(name):
    """Names containing path separators or traversal sequences must be rejected."""
    import click
    with pytest.raises((click.exceptions.Abort, SystemExit)):
        _validate_kb_name(name)


@given(st.from_regex(r'[^A-Za-z0-9].*', fullmatch=True).filter(bool))
@settings(max_examples=200)
def test_validate_kb_name_rejects_non_alnum_start(name):
    """Names not starting with a letter or digit must be rejected."""
    assume(not _KB_NAME_RE.match(name))
    import click
    with pytest.raises((click.exceptions.Abort, SystemExit)):
        _validate_kb_name(name)


# ---------------------------------------------------------------------------
# _parse_vtt
# ---------------------------------------------------------------------------

_vtt_text = st.text(alphabet=st.characters(blacklist_categories=("Cs",)))


@given(_vtt_text)
@settings(max_examples=300)
def test_parse_vtt_never_contains_html_tags(vtt_content):
    """Output must never contain HTML tags regardless of input."""
    result = _parse_vtt(vtt_content)
    assert not re.search(r'<[^>]+>', result), (
        f"HTML tag found in parse_vtt output: {result[:200]!r}"
    )


@given(_vtt_text)
@settings(max_examples=300)
def test_parse_vtt_never_contains_timestamps(vtt_content):
    """Output must never contain VTT timestamps (00:00:00.000 --> 00:00:00.000)."""
    result = _parse_vtt(vtt_content)
    assert "-->" not in result, f"Timestamp found in parse_vtt output: {result[:200]!r}"


@given(_vtt_text)
@settings(max_examples=300)
def test_parse_vtt_never_contains_webvtt_header(vtt_content):
    """Output must never contain the WEBVTT header line."""
    result = _parse_vtt(vtt_content)
    assert "WEBVTT" not in result, f"WEBVTT header found in output: {result[:200]!r}"


@given(_vtt_text)
@settings(max_examples=300)
def test_parse_vtt_output_is_string(vtt_content):
    """Output must always be a str (never None or exception)."""
    result = _parse_vtt(vtt_content)
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# search_wiki exclusion invariant
# ---------------------------------------------------------------------------

_safe_filename = st.from_regex(r'[a-z][a-z0-9_-]{0,20}\.md', fullmatch=True)
_hidden_dirname = st.from_regex(r'\.[a-z][a-z0-9_-]{0,10}', fullmatch=True)
_underscore_dirname = st.from_regex(r'_[a-z][a-z0-9_-]{0,10}', fullmatch=True)


@given(
    content=st.text(min_size=1, max_size=200,
                    alphabet=st.characters(whitelist_categories=("L", "N", "Zs"))),
    hidden_dir=_hidden_dirname,
    filename=_safe_filename,
)
@settings(max_examples=150, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_search_wiki_never_returns_hidden_directory_files(
    tmp_path, content, hidden_dir, filename
):
    """Files inside hidden directories (starting with '.') must never appear in results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir) / "wiki"
        wiki_dir.mkdir()

        hidden_path = wiki_dir / hidden_dir
        hidden_path.mkdir()
        (hidden_path / filename).write_text(content, encoding="utf-8")

        first_word = content.split()[0] if content.split() else content[:5]
        assume(first_word.strip())

        results = search_wiki(wiki_dir, first_word)
        for r in results:
            assert not r["file"].startswith("."), (
                f"Result from hidden dir leaked: {r['file']!r}"
            )
            assert "/." not in r["file"], (
                f"Result from hidden dir leaked: {r['file']!r}"
            )


@given(
    content=st.text(min_size=1, max_size=200,
                    alphabet=st.characters(whitelist_categories=("L", "N", "Zs"))),
    underscore_dir=_underscore_dirname,
    filename=_safe_filename,
)
@settings(max_examples=150, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_search_wiki_never_returns_underscore_directory_files(
    tmp_path, content, underscore_dir, filename
):
    """Files inside underscore directories (starting with '_') must never appear in results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir) / "wiki"
        wiki_dir.mkdir()

        underscore_path = wiki_dir / underscore_dir
        underscore_path.mkdir()
        (underscore_path / filename).write_text(content, encoding="utf-8")

        first_word = content.split()[0] if content.split() else content[:5]
        assume(first_word.strip())

        results = search_wiki(wiki_dir, first_word)
        for r in results:
            assert not any(
                part.startswith("_") for part in Path(r["file"]).parts
            ), f"Result from underscore dir leaked: {r['file']!r}"
