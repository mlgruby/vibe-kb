"""Tests for arXiv paper fetching."""
from vibe_kb.add.arxiv import search_arxiv, download_arxiv_pdf, arxiv_to_markdown


def test_search_arxiv_returns_paper_metadata():
    """Test searching arXiv returns paper metadata."""
    # Search for a well-known paper
    results = search_arxiv("attention is all you need", limit=1)

    assert len(results) == 1
    paper = results[0]
    assert "arxiv_id" in paper
    assert "title" in paper
    assert "authors" in paper
    assert "abstract" in paper
    assert "pdf_url" in paper
    assert len(paper["authors"]) > 0


def test_search_arxiv_respects_limit():
    """Test that search respects the limit parameter."""
    results = search_arxiv("transformer", limit=3)

    assert len(results) <= 3


def test_download_arxiv_pdf_saves_file(tmp_path):
    """Test downloading arXiv PDF saves to specified path."""
    # Use a small, real paper for testing
    arxiv_id = "1706.03762"  # "Attention Is All You Need"
    output_path = tmp_path / "paper.pdf"

    success = download_arxiv_pdf(arxiv_id, output_path)

    assert success is True
    assert output_path.exists()
    assert output_path.stat().st_size > 0  # PDF has content


def test_arxiv_to_markdown_converts_paper(tmp_path):
    """Test converting arXiv paper to markdown using MarkItDown."""
    # Use a well-known paper
    arxiv_id = "1706.03762"  # "Attention Is All You Need"
    output_path = tmp_path / "paper.md"

    result = arxiv_to_markdown(arxiv_id, output_path)

    assert result["success"] is True
    assert result["format"] in ["html", "pdf"]  # Either format works
    assert output_path.exists()

    # Check markdown has content
    content = output_path.read_text(encoding="utf-8")
    assert len(content) > 1000  # Should have substantial content
    assert "attention" in content.lower()  # Paper title should appear
