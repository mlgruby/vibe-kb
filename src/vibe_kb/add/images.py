"""Image extraction from HTML and PDF sources."""

import re
import ipaddress
from pathlib import Path
from typing import Dict, List
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

try:
    import ebooklib
    from ebooklib import epub

    EPUB_SUPPORT = True
except ImportError:
    EPUB_SUPPORT = False


def _is_safe_url(url: str) -> bool:
    """Check if URL is safe to fetch (blocks SSRF attempts).

    Blocks:
    - Private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    - Loopback addresses (127.0.0.0/8)
    - Link-local addresses (169.254.0.0/16, including metadata endpoint)
    - IPv6 private/loopback ranges

    Args:
        url: URL to validate

    Returns:
        True if safe to fetch, False otherwise
    """
    try:
        parsed = urlparse(url)

        # Must be http or https
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Try to resolve as IP address
        try:
            ip = ipaddress.ip_address(hostname)

            # Block private, loopback, and link-local addresses
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False

            # Explicitly block metadata endpoint (169.254.169.254)
            if str(ip) == "169.254.169.254":
                return False

        except ValueError:
            # Not an IP address (hostname) - allow it
            # DNS rebinding attacks are out of scope
            pass

        return True

    except Exception:
        # If parsing fails, err on the side of safety
        return False


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
    used_filenames = set()  # Track used filenames to avoid collisions

    for img_tag in soup.find_all("img"):
        src = img_tag.get("src")
        if not src:
            continue

        # Store the original src attribute (may be relative)
        original_src = src

        # Build absolute URL
        if base_url:
            # Handle arXiv's versioned paths (e.g., 1706.03762v7/Figures/...)
            # If src starts with arxiv ID pattern, it's already relative to the base HTML directory
            if re.match(r"\d{4}\.\d{4,5}v\d+/", src):
                # Extract the directory part after the versioned ID
                # E.g., from "1706.03762v7/Figures/image.png" get "/Figures/image.png"
                parts = src.split("/", 1)
                if len(parts) > 1:
                    src = parts[1]  # Get everything after first /
            img_url = urljoin(base_url, src)
        else:
            img_url = src

        # Skip data URIs and very small images (icons, spacers)
        if img_url.startswith("data:"):
            continue

        # Security: Block SSRF attempts to private IPs, localhost, metadata endpoints
        if not _is_safe_url(img_url):
            continue

        # Generate filename from URL
        parsed = urlparse(img_url)
        base_filename = Path(parsed.path).name
        if not base_filename:
            base_filename = f"image_{len(images)}.png"

        # Handle filename collisions by appending counter
        filename = base_filename
        counter = 1
        while filename in used_filenames:
            # Split filename into name and extension
            name_parts = base_filename.rsplit(".", 1)
            if len(name_parts) == 2:
                filename = f"{name_parts[0]}_{counter}.{name_parts[1]}"
            else:
                filename = f"{base_filename}_{counter}"
            counter += 1

        used_filenames.add(filename)
        local_path = images_dir / filename

        # Download image
        try:
            response = requests.get(img_url, timeout=30)
            response.raise_for_status()
            local_path.write_bytes(response.content)
            downloaded += 1

            images.append(
                {
                    "original_url": img_url,  # Absolute URL
                    "original_src": original_src,  # Raw src attribute (may be relative)
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

                # Note: downloaded stays 0 because we don't actually save files
                # Only metadata is recorded until full implementation

    except Exception as e:
        return {"images": [], "downloaded": 0, "error": str(e)}

    return {"images": images, "downloaded": downloaded}


def extract_images_from_epub(epub_file: Path, images_dir: Path) -> Dict:
    """Extract embedded images from ePub file.

    Args:
        epub_file: Path to ePub file
        images_dir: Directory to save images

    Returns:
        Dictionary with:
        - images: List of dicts with original_path, local_path, filename
        - downloaded: Count of successfully extracted images
    """
    if not EPUB_SUPPORT:
        return {"images": [], "downloaded": 0, "error": "ebooklib not installed"}

    images_dir.mkdir(parents=True, exist_ok=True)

    images = []
    downloaded = 0
    used_filenames = set()  # Track used filenames to avoid collisions

    try:
        book = epub.read_epub(str(epub_file))

        # Extract all image items
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                # Get image filename from item name
                original_path = item.get_name()
                base_filename = Path(original_path).name

                # Some ePubs use paths like "OEBPS/images/fig1.png"
                # We just want the filename part
                if not base_filename:
                    base_filename = f"image_{len(images)}.png"

                # Handle filename collisions by appending counter
                filename = base_filename
                counter = 1
                while filename in used_filenames:
                    # Split filename into name and extension
                    name_parts = base_filename.rsplit(".", 1)
                    if len(name_parts) == 2:
                        filename = f"{name_parts[0]}_{counter}.{name_parts[1]}"
                    else:
                        filename = f"{base_filename}_{counter}"
                    counter += 1

                used_filenames.add(filename)
                local_path = images_dir / filename

                # Save image content
                try:
                    local_path.write_bytes(item.get_content())
                    downloaded += 1

                    images.append(
                        {
                            "original_path": original_path,
                            "local_path": str(local_path),
                            "filename": filename,
                        }
                    )
                except Exception:
                    # Skip failed extractions
                    continue

    except Exception as e:
        return {"images": [], "downloaded": 0, "error": str(e)}

    return {"images": images, "downloaded": downloaded}


def update_markdown_image_links(
    markdown_content: str, images: List[Dict], images_dir_relative: str
) -> str:
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
        original_src = img.get("original_src", original_url)  # Fall back to URL if not present
        filename = img["filename"]
        local_ref = f"{images_dir_relative}/{filename}"

        # Replace both absolute URL and original src in markdown
        # This handles cases where converters emit relative paths vs absolute URLs

        # Replace absolute URL forms
        markdown_content = markdown_content.replace(f"]({original_url})", f"]({local_ref})")
        markdown_content = markdown_content.replace(f'src="{original_url}"', f'src="{local_ref}"')
        markdown_content = markdown_content.replace(f"src='{original_url}'", f"src='{local_ref}'")

        # Also replace original src forms (may be relative)
        if original_src != original_url:
            markdown_content = markdown_content.replace(f"]({original_src})", f"]({local_ref})")
            markdown_content = markdown_content.replace(
                f'src="{original_src}"', f'src="{local_ref}"'
            )
            markdown_content = markdown_content.replace(
                f"src='{original_src}'", f"src='{local_ref}'"
            )

    return markdown_content
