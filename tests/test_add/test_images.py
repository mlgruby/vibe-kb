"""Tests for image extraction from various sources."""

from unittest.mock import Mock, patch
from vibe_kb.add.images import extract_images_from_html, extract_images_from_pdf


def test_extract_images_from_html_creates_directory(tmp_path):
    """Test that image extraction creates images directory."""
    html_content = """
    <html>
        <body>
            <img src="https://arxiv.org/html/1706.03762v7/image1.png" alt="Figure 1">
            <p>Some text</p>
            <img src="https://arxiv.org/html/1706.03762v7/image2.png" alt="Figure 2">
        </body>
    </html>
    """

    html_file = tmp_path / "paper.html"
    html_file.write_text(html_content)

    images_dir = tmp_path / "images"

    # Mock HTTP requests
    with patch("vibe_kb.add.images.requests.get") as mock_get:
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = extract_images_from_html(html_file, images_dir)

    assert images_dir.exists()
    assert len(result["images"]) == 2
    assert result["downloaded"] == 2


def test_extract_images_from_pdf_saves_images(tmp_path):
    """Test that PDF image extraction works."""
    # This will need a real PDF with images to test properly
    # For now, just test the interface exists
    pdf_file = tmp_path / "paper.pdf"
    images_dir = tmp_path / "images"

    # Create empty PDF for interface test
    pdf_file.write_bytes(b"%PDF-1.4\n%")

    result = extract_images_from_pdf(pdf_file, images_dir)

    assert "images" in result
    assert "downloaded" in result
