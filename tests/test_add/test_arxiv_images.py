"""Tests for arXiv image extraction with versioned URLs."""

from unittest.mock import Mock, patch
from vibe_kb.add.arxiv import arxiv_to_markdown


def test_arxiv_extracts_versioned_images(tmp_path):
    """Test that arXiv papers with versioned URLs (e.g., v7) extract images correctly."""
    arxiv_id = "1706.03762"
    output_path = tmp_path / "paper.md"
    images_dir = tmp_path / f"{output_path.stem}_images"

    # Mock HTML response with versioned image paths
    html_content = b"""
    <html>
        <body>
            <img src="1706.03762v7/Figures/ModalNet-21.png" alt="Figure 1">
            <img src="1706.03762v7/x1.png" alt="Figure 2">
        </body>
    </html>
    """

    with patch("vibe_kb.add.arxiv.requests.get") as mock_get:
        # First call: HTML page
        html_response = Mock()
        html_response.status_code = 200
        html_response.content = html_content
        html_response.url = "https://arxiv.org/html/1706.03762v7"  # Redirected to versioned URL

        # Subsequent calls: images
        image_response = Mock()
        image_response.content = b"fake image data"
        image_response.raise_for_status = Mock()

        mock_get.side_effect = [html_response, image_response, image_response]

        # Mock MarkItDown
        with patch("vibe_kb.add.arxiv.MarkItDown") as mock_md:
            mock_converter = Mock()
            mock_result = Mock()
            mock_result.text_content = "# Paper\n\n![Figure 1](1706.03762v7/Figures/ModalNet-21.png)\n![Figure 2](1706.03762v7/x1.png)"
            mock_converter.convert.return_value = mock_result
            mock_md.return_value = mock_converter

            result = arxiv_to_markdown(arxiv_id, output_path)

    # Verify images were extracted
    assert result["success"] is True
    assert result["format"] == "html"
    assert result["images_extracted"] == 2

    # Verify images directory created
    assert images_dir.exists()

    # Verify images downloaded
    assert (images_dir / "ModalNet-21.png").exists()
    assert (images_dir / "x1.png").exists()
