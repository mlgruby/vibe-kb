"""arXiv paper fetching and download."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict
import requests
from markitdown import MarkItDown


def search_arxiv(query: str, limit: int = 10) -> List[Dict]:
    """Search arXiv for papers matching query.

    Args:
        query: Search query string
        limit: Maximum number of results to return

    Returns:
        List of paper metadata dictionaries with keys:
        - arxiv_id: arXiv paper ID
        - title: Paper title
        - authors: List of author names
        - abstract: Paper abstract
        - pdf_url: URL to PDF
    """
    # arXiv API endpoint
    base_url = "http://export.arxiv.org/api/query"

    # Build query parameters
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    response = requests.get(base_url, params=params)
    response.raise_for_status()

    # Parse XML response
    root = ET.fromstring(response.content)

    # Extract namespace
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    results = []
    for entry in root.findall("atom:entry", ns):
        # Extract arXiv ID from entry ID URL
        entry_id = entry.find("atom:id", ns).text
        arxiv_id = entry_id.split("/")[-1]

        # Extract metadata
        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        abstract = entry.find("atom:summary", ns).text.strip().replace("\n", " ")

        # Extract authors
        authors = []
        for author in entry.findall("atom:author", ns):
            name = author.find("atom:name", ns).text
            authors.append(name)

        # Build PDF URL
        pdf_url = f"http://arxiv.org/pdf/{arxiv_id}.pdf"

        results.append(
            {
                "arxiv_id": arxiv_id,
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "pdf_url": pdf_url,
            }
        )

    return results


def download_arxiv_pdf(arxiv_id: str, output_path: Path) -> bool:
    """Download arXiv paper PDF.

    Args:
        arxiv_id: arXiv paper ID (e.g., "1706.03762")
        output_path: Path to save PDF file

    Returns:
        True if download succeeded, False otherwise
    """
    pdf_url = f"http://arxiv.org/pdf/{arxiv_id}.pdf"

    try:
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)

        return True
    except Exception:
        return False


def arxiv_to_markdown(arxiv_id: str, output_path: Path) -> Dict:
    """Convert arXiv paper to markdown using MarkItDown.

    Tries HTML format first (better quality), falls back to PDF.

    Args:
        arxiv_id: arXiv paper ID (e.g., "1706.03762")
        output_path: Path to save markdown file

    Returns:
        Dictionary with:
        - success: bool - whether conversion succeeded
        - format: str - "html" or "pdf" (which format was used)
        - error: str - error message if failed (optional)
    """
    md = MarkItDown()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Try HTML first (preferred - better formatting)
    html_url = f"https://arxiv.org/html/{arxiv_id}"
    try:
        response = requests.get(html_url, timeout=30)
        if response.status_code == 200:
            # Save HTML temporarily
            temp_html = output_path.parent / f"{arxiv_id}.html"
            temp_html.write_bytes(response.content)

            # Convert to markdown
            result = md.convert(str(temp_html))
            output_path.write_text(result.text_content, encoding="utf-8")

            # Clean up temp file
            temp_html.unlink()

            return {"success": True, "format": "html"}
    except Exception:
        pass  # Fall back to PDF

    # Fall back to PDF
    pdf_url = f"http://arxiv.org/pdf/{arxiv_id}.pdf"
    try:
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()

        # Save PDF temporarily
        temp_pdf = output_path.parent / f"{arxiv_id}.pdf"
        temp_pdf.write_bytes(response.content)

        # Convert to markdown
        result = md.convert(str(temp_pdf))
        output_path.write_text(result.text_content, encoding="utf-8")

        # Clean up temp file
        temp_pdf.unlink()

        return {"success": True, "format": "pdf"}
    except Exception as e:
        return {"success": False, "format": None, "error": str(e)}
