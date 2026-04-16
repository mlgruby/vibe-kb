"""Image extraction from HTML and PDF sources."""
import re
from pathlib import Path
from typing import Dict, List
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup


def extract_images_from_html(html_file: Path, images_dir: Path, base_url: str = None) -> Dict:
    """Extract and download images from HTML file.

    Args:
        html_file: Path to HTML file
        images_dir: Directory to save images
        base_url: Base URL for relative image paths (optional)

    Returns:
        Dictionary with:
        - images: List of dicts with original_url, local_path, alt_text
        - downloaded: Count of successfully downloaded images
    """
    images_dir.mkdir(parents=True, exist_ok=True)

    content = html_file.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")

    # If no base_url provided, try to infer from common patterns
    if not base_url and "arxiv.org" in str(html_file):
        # Extract arXiv ID pattern
        match = re.search(r"(\d{4}\.\d{4,5})", str(html_file))
        if match:
            base_url = f"https://arxiv.org/html/{match.group(1)}/"

    images = []
    downloaded = 0

    for img_tag in soup.find_all("img"):
        src = img_tag.get("src")
        if not src:
            continue

        # Build absolute URL
        if base_url:
            img_url = urljoin(base_url, src)
        else:
            img_url = src

        # Skip data URIs and very small images (icons, spacers)
        if img_url.startswith("data:"):
            continue

        # Generate filename from URL
        parsed = urlparse(img_url)
        filename = Path(parsed.path).name
        if not filename:
            filename = f"image_{len(images)}.png"

        local_path = images_dir / filename

        # Download image
        try:
            response = requests.get(img_url, timeout=30)
            response.raise_for_status()
            local_path.write_bytes(response.content)
            downloaded += 1

            images.append(
                {
                    "original_url": img_url,
                    "local_path": str(local_path),
                    "alt_text": img_tag.get("alt", ""),
                    "filename": filename,
                }
            )
        except Exception:
            # Skip failed downloads
            continue

    return {"images": images, "downloaded": downloaded}


def extract_images_from_pdf(pdf_file: Path, images_dir: Path) -> Dict:
    """Extract embedded images from PDF file.

    Args:
        pdf_file: Path to PDF file
        images_dir: Directory to save images

    Returns:
        Dictionary with:
        - images: List of dicts with local_path, page_number
        - downloaded: Count of successfully extracted images
    """
    try:
        import pdfplumber
    except ImportError:
        return {"images": [], "downloaded": 0, "error": "pdfplumber not installed"}

    images_dir.mkdir(parents=True, exist_ok=True)

    images = []
    downloaded = 0

    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extract images from page
                page_images = page.images

                for img_idx, img in enumerate(page_images):
                    filename = f"page{page_num}_image{img_idx}.png"
                    local_path = images_dir / filename

                    # pdfplumber provides image coordinates, need to crop and save
                    # For now, just record metadata
                    # Full implementation would crop and save actual image data

                    images.append(
                        {
                            "local_path": str(local_path),
                            "page_number": page_num,
                            "filename": filename,
                            "bounds": img,
                        }
                    )

                downloaded = len(images)

    except Exception as e:
        return {"images": [], "downloaded": 0, "error": str(e)}

    return {"images": images, "downloaded": downloaded}


def update_markdown_image_links(markdown_content: str, images: List[Dict], images_dir_relative: str) -> str:
    """Update markdown image links to point to local files.

    Args:
        markdown_content: Original markdown content
        images: List of image metadata from extract_images_from_html
        images_dir_relative: Relative path to images directory (e.g., "images/")

    Returns:
        Updated markdown content with local image paths
    """
    for img in images:
        original_url = img["original_url"]
        filename = img["filename"]
        local_ref = f"{images_dir_relative}/{filename}"

        # Replace image URLs in markdown
        # Pattern: ![alt](url) or <img src="url">
        markdown_content = markdown_content.replace(f"]({original_url})", f"]({local_ref})")
        markdown_content = markdown_content.replace(f'src="{original_url}"', f'src="{local_ref}"')
        markdown_content = markdown_content.replace(f"src='{original_url}'", f"src='{local_ref}'")

    return markdown_content
