"""Tests for web article URL fetching and conversion."""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from vibe_kb.add.url import fetch_url_to_markdown
from vibe_kb.cli import cli


SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Test Article Title</title>
    <meta property="og:title" content="OG Article Title">
    <meta name="author" content="Jane Doe">
</head>
<body>
    <nav>Navigation stuff</nav>
    <header>Header stuff</header>
    <article>
        <h1>Main Article Heading</h1>
        <p>This is the first paragraph of the article with useful content.</p>
        <h2>Section 2</h2>
        <p>This is the second paragraph with more useful content.</p>
        <ul>
            <li>List item one</li>
            <li>List item two</li>
        </ul>
    </article>
    <aside>Sidebar content</aside>
    <footer>Footer stuff</footer>
</body>
</html>"""

SAMPLE_HTML_NO_OG = """<!DOCTYPE html>
<html>
<head>
    <title>Plain Title</title>
    <meta name="author" content="Bob Smith">
</head>
<body>
    <main>
        <h1>Article Heading</h1>
        <p>Some useful paragraph content here.</p>
    </main>
</body>
</html>"""

SAMPLE_HTML_ARTICLE_TAG = """<!DOCTYPE html>
<html>
<head>
    <title>Article Tag Test</title>
</head>
<body>
    <div>Some noise outside article</div>
    <article>
        <h1>Article Content</h1>
        <p>This content is inside the article tag.</p>
        <p>More content inside article.</p>
    </article>
    <div>More noise</div>
</body>
</html>"""

SAMPLE_HTML_EMPTY = """<!DOCTYPE html>
<html>
<head><title>Empty Page</title></head>
<body>
    <nav>Just nav links</nav>
    <footer>Just footer</footer>
</body>
</html>"""


def _make_mock_response(html: str, status_code: int = 200):
    """Create a mock requests.Response object."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.text = html
    mock_resp.raise_for_status = MagicMock()
    if status_code >= 400:
        from requests.exceptions import HTTPError

        mock_resp.raise_for_status.side_effect = HTTPError(
            f"{status_code} Error", response=mock_resp
        )
    return mock_resp


# ---------------------------------------------------------------------------
# Unit tests for fetch_url_to_markdown
# ---------------------------------------------------------------------------


def test_fetch_url_basic(tmp_path):
    """Mock successful HTML response, verify markdown file written with title and content."""
    output_path = tmp_path / "article.md"

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(SAMPLE_HTML)

        result = fetch_url_to_markdown("https://example.com/article", output_path)

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")

    # Check frontmatter
    assert "type: article" in content
    assert "source_url: https://example.com/article" in content
    assert "domain: example.com" in content

    # Check article body metadata
    assert "**Source:** https://example.com/article" in content
    assert "example.com" in content

    # Check content was extracted
    assert "first paragraph" in content or "useful content" in content

    # Check return dict
    assert result["url"] == "https://example.com/article"
    assert result["domain"] == "example.com"
    assert "title" in result
    assert "author" in result


def test_fetch_url_uses_og_title(tmp_path):
    """og:title meta tag takes precedence over <title>."""
    output_path = tmp_path / "article.md"

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(SAMPLE_HTML)

        result = fetch_url_to_markdown("https://example.com/article", output_path)

    assert result["title"] == "OG Article Title"
    content = output_path.read_text(encoding="utf-8")
    assert "OG Article Title" in content


def test_fetch_url_extracts_article_tag(tmp_path):
    """Content comes from <article> element, excluding noise divs."""
    output_path = tmp_path / "article.md"

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(SAMPLE_HTML_ARTICLE_TAG)

        fetch_url_to_markdown("https://example.com/page", output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "inside the article tag" in content


def test_fetch_url_raises_for_invalid_scheme(tmp_path):
    """ftp:// URL raises ValueError before making any request."""
    output_path = tmp_path / "article.md"

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        with pytest.raises(ValueError) as exc_info:
            fetch_url_to_markdown("ftp://example.com/file.txt", output_path)

        # Should not have made any network call
        mock_get.assert_not_called()

    assert "invalid" in str(exc_info.value).lower() or "scheme" in str(exc_info.value).lower()


def test_fetch_url_raises_for_http_error(tmp_path):
    """404 response raises ValueError."""
    output_path = tmp_path / "article.md"

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response("<html></html>", status_code=404)

        with pytest.raises(ValueError) as exc_info:
            fetch_url_to_markdown("https://example.com/notfound", output_path)

    assert "404" in str(exc_info.value) or "http" in str(exc_info.value).lower()


def test_fetch_url_raises_for_empty_content(tmp_path):
    """HTML with no extractable text raises ValueError."""
    output_path = tmp_path / "article.md"

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(SAMPLE_HTML_EMPTY)

        with pytest.raises(ValueError) as exc_info:
            fetch_url_to_markdown("https://example.com/empty", output_path)

    assert "no article content" in str(exc_info.value).lower()


def test_fetch_url_extracts_author(tmp_path):
    """Author extracted from meta name=author tag."""
    output_path = tmp_path / "article.md"

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(SAMPLE_HTML)

        result = fetch_url_to_markdown("https://example.com/article", output_path)

    assert result["author"] == "Jane Doe"
    content = output_path.read_text(encoding="utf-8")
    assert "Jane Doe" in content


def test_fetch_url_fallback_title_from_title_tag(tmp_path):
    """When no og:title, uses <title> tag."""
    output_path = tmp_path / "article.md"

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(SAMPLE_HTML_NO_OG)

        result = fetch_url_to_markdown("https://example.com/page", output_path)

    assert result["title"] == "Plain Title"


def test_fetch_url_unknown_author_fallback(tmp_path):
    """HTML with no author meta falls back to 'Unknown'."""
    output_path = tmp_path / "article.md"

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(SAMPLE_HTML_ARTICLE_TAG)

        result = fetch_url_to_markdown("https://example.com/page", output_path)

    assert result["author"] == "Unknown"
    content = output_path.read_text(encoding="utf-8")
    assert "**Author:** Unknown" in content


def test_fetch_url_uses_correct_request_params(tmp_path):
    """Verify User-Agent header and timeout are set."""
    output_path = tmp_path / "article.md"

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(SAMPLE_HTML)

        fetch_url_to_markdown("https://example.com/article", output_path)

    call_kwargs = mock_get.call_args
    # Should have been called with timeout
    assert call_kwargs is not None
    _, kwargs = call_kwargs
    assert "timeout" in kwargs
    assert kwargs["timeout"] == 30
    # Should have headers with User-Agent
    assert "headers" in kwargs
    assert "User-Agent" in kwargs["headers"]


def test_fetch_url_writes_utf8(tmp_path):
    """File is written with UTF-8 encoding."""
    html_with_unicode = """<!DOCTYPE html>
<html><head><title>Unicode Test</title></head>
<body>
<article>
    <h1>Unicode Heading</h1>
    <p>Content with special chars: café, naïve, résumé.</p>
</article>
</body></html>"""

    output_path = tmp_path / "article.md"

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(html_with_unicode)

        fetch_url_to_markdown("https://example.com/unicode", output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "café" in content or "naïve" in content or "résumé" in content


def test_fetch_url_removes_nav_header_footer(tmp_path):
    """Navigation, header, and footer elements are stripped from output."""
    output_path = tmp_path / "article.md"

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(SAMPLE_HTML)

        fetch_url_to_markdown("https://example.com/article", output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "Navigation stuff" not in content
    assert "Header stuff" not in content
    assert "Footer stuff" not in content
    assert "Sidebar content" not in content


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


def test_cli_add_url_integration(tmp_path):
    """Full CLI test mocking requests.get."""
    runner = CliRunner()

    # Create KB first
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(SAMPLE_HTML)

        result = runner.invoke(
            cli,
            [
                "add",
                "test-kb",
                "--url",
                "https://example.com/article",
                "--vault-path",
                str(tmp_path),
            ],
        )

    assert result.exit_code == 0, f"CLI failed with output:\n{result.output}"
    assert "Added article" in result.output
    assert "example.com" in result.output

    # Check files were created
    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    articles_dir = kb_dir / "raw" / "articles"
    assert articles_dir.exists()

    md_files = list(articles_dir.glob("*.md"))
    assert len(md_files) == 1

    meta_files = list(articles_dir.glob("*.meta.json"))
    assert len(meta_files) == 1


def test_cli_add_url_invalid_scheme(tmp_path):
    """CLI rejects non-http/https URLs."""
    runner = CliRunner()

    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    result = runner.invoke(
        cli,
        [
            "add",
            "test-kb",
            "--url",
            "ftp://example.com/article",
            "--vault-path",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    assert "invalid" in result.output.lower() or "http" in result.output.lower()


def test_cli_add_url_prevents_overwrite(tmp_path):
    """Adding same URL twice fails with 'already exists'."""
    runner = CliRunner()

    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(SAMPLE_HTML)

        # First add
        result = runner.invoke(
            cli,
            [
                "add",
                "test-kb",
                "--url",
                "https://example.com/article",
                "--vault-path",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0, f"First add failed:\n{result.output}"

        # Second add with the same URL (same title -> same filename)
        result = runner.invoke(
            cli,
            [
                "add",
                "test-kb",
                "--url",
                "https://example.com/article",
                "--vault-path",
                str(tmp_path),
            ],
        )

    assert result.exit_code != 0
    assert "already exists" in result.output


def test_cli_add_url_rolls_back_on_metadata_failure(tmp_path):
    """If create_metadata raises, no orphaned .md file is left behind."""
    runner = CliRunner()

    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        mock_get.return_value = _make_mock_response(SAMPLE_HTML)

        with patch("vibe_kb.cli.create_metadata") as mock_meta:
            mock_meta.side_effect = OSError("Disk full")

            result = runner.invoke(
                cli,
                [
                    "add",
                    "test-kb",
                    "--url",
                    "https://example.com/article",
                    "--vault-path",
                    str(tmp_path),
                ],
            )

    assert result.exit_code != 0

    # No orphaned .md file should remain
    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    articles_dir = kb_dir / "raw" / "articles"
    if articles_dir.exists():
        md_files = list(articles_dir.glob("*.md"))
        assert len(md_files) == 0, f"Orphaned .md files found: {md_files}"


def test_cli_add_url_no_source_updated_message(tmp_path):
    """'No source specified' error message now mentions --url."""
    runner = CliRunner()

    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    result = runner.invoke(cli, ["add", "test-kb", "--vault-path", str(tmp_path)])

    assert result.exit_code != 0
    assert "--url" in result.output


def test_fetch_url_resolves_page_relative_images_correctly(tmp_path):
    """Page-relative images are resolved against article URL, not domain root."""
    html_with_relative_img = """<!DOCTYPE html>
<html>
<head>
    <title>Article With Relative Image</title>
</head>
<body>
    <article>
        <h1>Content</h1>
        <img src="figure.png" alt="Relative image">
    </article>
</body>
</html>"""

    output_path = tmp_path / "article.md"
    fetched_figure = False

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        # Mock the HTML fetch
        mock_html_resp = _make_mock_response(html_with_relative_img)
        # Simulate the article being at /blog/post.html
        mock_html_resp.url = "https://example.com/blog/post.html"

        def mock_response_handler(url, **kwargs):
            nonlocal fetched_figure
            if url == "https://example.com/blog/post.html":
                return mock_html_resp
            elif url == "https://example.com/blog/figure.png":
                # Correct: resolved relative to article URL
                fetched_figure = True
                mock_img = MagicMock()
                mock_img.content = b"correct figure"
                mock_img.raise_for_status = MagicMock()
                return mock_img
            elif url == "https://example.com/figure.png":
                # Wrong: resolved relative to domain root
                mock_img = MagicMock()
                mock_img.content = b"wrong location"
                mock_img.raise_for_status = MagicMock()
                return mock_img
            return _make_mock_response("<html></html>")

        mock_get.side_effect = mock_response_handler

        fetch_url_to_markdown("https://example.com/blog/post.html", output_path)

    # Verify image was fetched from correct location (relative to article, not domain)
    assert fetched_figure, "Image should have been fetched from /blog/figure.png, not /figure.png"


def test_cli_add_url_with_images_moves_images_to_kb(tmp_path):
    """Article images are moved from temp location to KB alongside markdown."""
    # HTML with embedded images
    html_with_images = """<!DOCTYPE html>
<html>
<head>
    <title>Article With Images</title>
    <meta name="author" content="Test Author">
</head>
<body>
    <article>
        <h1>Visual Guide</h1>
        <p>Here is a diagram:</p>
        <img src="diagram.png" alt="System diagram">
        <p>And another figure:</p>
        <img src="chart.png" alt="Performance chart">
    </article>
</body>
</html>"""

    runner = CliRunner()
    result = runner.invoke(cli, ["create", "test-kb", "--vault-path", str(tmp_path)])
    assert result.exit_code == 0

    with patch("vibe_kb.add.url.requests.get") as mock_get:
        # Mock the HTML fetch
        mock_html_resp = _make_mock_response(html_with_images)
        mock_html_resp.url = "https://example.com/visual-guide"

        # Mock image downloads
        def mock_response_handler(url, **kwargs):
            if url == "https://example.com/visual-guide":
                return mock_html_resp
            elif "diagram.png" in url:
                mock_img = MagicMock()
                mock_img.content = b"fake diagram data"
                mock_img.raise_for_status = MagicMock()
                return mock_img
            elif "chart.png" in url:
                mock_img = MagicMock()
                mock_img.content = b"fake chart data"
                mock_img.raise_for_status = MagicMock()
                return mock_img
            return _make_mock_response("<html></html>")

        mock_get.side_effect = mock_response_handler

        result = runner.invoke(
            cli,
            [
                "add",
                "test-kb",
                "--url",
                "https://example.com/visual-guide",
                "--vault-path",
                str(tmp_path),
            ],
        )

    assert result.exit_code == 0, f"CLI failed:\n{result.output}"

    # Check that markdown was created
    kb_dir = tmp_path / "knowledge-bases" / "test-kb"
    articles_dir = kb_dir / "raw" / "articles"
    md_files = list(articles_dir.glob("*.md"))
    assert len(md_files) == 1, f"Expected 1 markdown file, found {len(md_files)}"

    md_file = md_files[0]

    # Check that images directory exists NEXT TO the markdown file in KB
    images_dir = articles_dir / f"{md_file.stem}_images"
    assert images_dir.exists(), f"Images directory not found at {images_dir}"

    # Check that both images were moved to the KB
    diagram = images_dir / "diagram.png"
    chart = images_dir / "chart.png"
    assert diagram.exists(), f"diagram.png not found in {images_dir}"
    assert chart.exists(), f"chart.png not found in {images_dir}"

    # Verify image content was saved correctly
    assert diagram.read_bytes() == b"fake diagram data"
    assert chart.read_bytes() == b"fake chart data"

    # Check that markdown has correct relative paths (not /tmp paths)
    content = md_file.read_text()
    assert f"{md_file.stem}_images/diagram.png" in content
    assert f"{md_file.stem}_images/chart.png" in content
    # Ensure NO temp paths leaked into markdown
    assert "/tmp" not in content.lower()
