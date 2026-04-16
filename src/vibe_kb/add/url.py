"""Web article fetching and conversion to markdown."""

import re
from datetime import date
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from .images import extract_images_from_html, update_markdown_image_links


def fetch_url_to_markdown(url: str, output_path: Path) -> Dict[str, str]:
    """Fetch a web article and convert to markdown.

    Args:
        url: URL of the web article
        output_path: Path to write the markdown file

    Returns:
        Dict with title, author, url, domain

    Raises:
        ValueError: If URL is invalid, request fails, or no content extracted
    """
    # Validate URL scheme
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Invalid URL scheme '{parsed.scheme}'. Only http and https URLs are supported."
        )

    domain = parsed.hostname or parsed.netloc or url

    # Fetch the page
    headers = {
        "User-Agent": ("Mozilla/5.0 (compatible; vibe-kb/0.1; +https://github.com/vibe-kb/vibe-kb)")
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise ValueError(f"HTTP error fetching '{url}': {e}") from e
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to fetch '{url}': {e}") from e

    html = response.text

    # Parse HTML
    soup = BeautifulSoup(html, "html.parser")

    # Extract title: og:title > <title> > domain fallback
    title = _extract_title(soup, domain)

    # Extract author: meta name=author or article:author
    author = _extract_author(soup)

    # Extract main content
    content = _extract_content(soup)

    if not content.strip():
        raise ValueError(f"No article content could be extracted from {url}")

    # Extract images
    images_extracted = 0
    temp_html = output_path.parent / f"{output_path.stem}_temp.html"
    try:
        # Save HTML temporarily for image extraction
        temp_html.write_text(html, encoding="utf-8")

        # Extract images (use response.url to handle redirects and preserve path)
        images_dir = output_path.parent / f"{output_path.stem}_images"
        base_url = response.url
        image_result = extract_images_from_html(temp_html, images_dir, base_url)
        images_extracted = image_result["downloaded"]

        # Update content with local image references
        if images_extracted > 0:
            images_dir_relative = f"{output_path.stem}_images"
            content = update_markdown_image_links(
                content, image_result["images"], images_dir_relative
            )
    finally:
        # Clean up temp HTML
        if temp_html.exists():
            temp_html.unlink()

    # Write markdown file with frontmatter
    today = date.today().isoformat()
    markdown = f"---\ntype: article\nsource_url: {url}\nadded: {today}\ndomain: {domain}\n---\n\n"
    markdown += f"# {title}\n\n"
    markdown += f"**Source:** {url}\n"
    markdown += f"**Author:** {author or 'Unknown'}\n"
    markdown += f"**Domain:** {domain}\n\n"
    markdown += "---\n\n"
    markdown += content

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    return {
        "title": title,
        "author": author or "Unknown",
        "url": url,
        "domain": domain,
        "images_extracted": images_extracted,
    }


def _extract_title(soup: BeautifulSoup, fallback: str) -> str:
    """Extract page title from HTML.

    Priority: og:title > <title> > fallback domain.

    Args:
        soup: Parsed BeautifulSoup object
        fallback: Fallback string (typically the domain)

    Returns:
        Title string
    """
    # Try og:title first
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content", "").strip():
        return og_title["content"].strip()

    # Try <title> tag
    title_tag = soup.find("title")
    if title_tag and title_tag.get_text(strip=True):
        return title_tag.get_text(strip=True)

    return fallback


def _extract_author(soup: BeautifulSoup) -> Optional[str]:
    """Extract author from HTML meta tags.

    Args:
        soup: Parsed BeautifulSoup object

    Returns:
        Author string or None
    """
    # Try meta name="author"
    author_meta = soup.find("meta", attrs={"name": "author"})
    if author_meta and author_meta.get("content", "").strip():
        return author_meta["content"].strip()

    # Try meta property="article:author"
    article_author = soup.find("meta", property="article:author")
    if article_author and article_author.get("content", "").strip():
        return article_author["content"].strip()

    return None


def _extract_content(soup: BeautifulSoup) -> str:
    """Extract main article content from HTML.

    Removes boilerplate elements (nav, header, footer, aside, script, style)
    and tries <article>, <main>, role="main" div, then largest <div>.

    Args:
        soup: Parsed BeautifulSoup object

    Returns:
        Markdown-formatted content string
    """
    # Remove boilerplate elements from a working copy
    working = BeautifulSoup(str(soup), "html.parser")
    for tag in working.find_all(["nav", "header", "footer", "aside", "script", "style"]):
        tag.decompose()

    # Try <article> first
    content_elem = working.find("article")

    # Try <main>
    if not content_elem:
        content_elem = working.find("main")

    # Try role="main"
    if not content_elem:
        content_elem = working.find(attrs={"role": "main"})

    # Fall back to largest <div> by text length
    if not content_elem:
        divs = working.find_all("div")
        if divs:
            content_elem = max(divs, key=lambda d: len(d.get_text()))

    if not content_elem:
        content_elem = working.find("body")

    if not content_elem:
        return ""

    return _html_to_markdown(content_elem)


def _html_to_markdown(elem: BeautifulSoup) -> str:
    """Convert an HTML element to simplified markdown.

    Handles headings, paragraphs, lists, images, bold, italic, and code blocks.

    Args:
        elem: BeautifulSoup element to convert

    Returns:
        Markdown string
    """
    lines = []

    for tag in elem.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "pre", "blockquote", "img"],
        recursive=True,
    ):
        name = tag.name

        if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            # Skip headings nested inside list items
            if tag.parent and tag.parent.name in ("li", "td", "th"):
                continue
            text = tag.get_text(strip=True)
            if text:
                level = int(name[1])
                lines.append(f"{'#' * level} {text}\n")

        elif name == "p":
            # Skip paragraphs nested in list items (they'll be rendered by list handler)
            if tag.parent and tag.parent.name in ("li", "td", "th"):
                continue
            text = _inline_markdown(tag)
            if text.strip():
                lines.append(f"{text.strip()}\n")

        elif name in ("ul", "ol"):
            # Only process top-level lists (not nested — those handled recursively)
            if tag.parent and tag.parent.name in ("li",):
                continue
            list_lines = _convert_list(tag, ordered=(name == "ol"))
            if list_lines:
                lines.append(list_lines + "\n")

        elif name == "pre":
            # Skip pre nested inside other pre
            if tag.parent and tag.parent.name == "pre":
                continue
            code_text = tag.get_text()
            if code_text.strip():
                lines.append(f"```\n{code_text.strip()}\n```\n")

        elif name == "blockquote":
            bq_text = tag.get_text(strip=True)
            if bq_text:
                lines.append(f"> {bq_text}\n")

        elif name == "img":
            # Skip images already processed inside paragraphs
            if tag.parent and tag.parent.name in ("p", "a"):
                continue
            # Standalone images (not in paragraphs)
            src = tag.get("src", "")
            alt = tag.get("alt", "")
            if src:
                lines.append(f"![{alt}]({src})\n")

    result = "\n".join(lines)
    # Collapse excessive blank lines
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def _convert_list(tag: BeautifulSoup, ordered: bool = False, depth: int = 0) -> str:
    """Convert a <ul> or <ol> element to markdown list.

    Args:
        tag: List element
        ordered: True for ordered list, False for unordered
        depth: Nesting depth for indentation

    Returns:
        Markdown list string
    """
    lines = []
    indent = "  " * depth
    for i, li in enumerate(tag.find_all("li", recursive=False), start=1):
        # Get direct text (not from nested lists)
        direct_text = ""
        for child in li.children:
            if hasattr(child, "name"):
                if child.name in ("ul", "ol"):
                    continue
                direct_text += child.get_text()
            else:
                direct_text += str(child)
        direct_text = direct_text.strip()

        prefix = f"{indent}{i}. " if ordered else f"{indent}- "

        if direct_text:
            lines.append(f"{prefix}{direct_text}")

        # Handle nested lists
        for child in li.find_all(["ul", "ol"], recursive=False):
            nested = _convert_list(child, ordered=(child.name == "ol"), depth=depth + 1)
            if nested:
                lines.append(nested)

    return "\n".join(lines)


def _inline_markdown(tag: BeautifulSoup) -> str:
    """Convert inline HTML elements to markdown within a paragraph.

    Handles <strong>, <b>, <em>, <i>, <code>, <a>, <img>.

    Args:
        tag: Paragraph or inline element

    Returns:
        Markdown string
    """
    result = ""
    for child in tag.children:
        if not hasattr(child, "name"):
            # NavigableString — plain text
            result += str(child)
        elif child.name in ("strong", "b"):
            inner = child.get_text()
            if inner:
                result += f"**{inner}**"
        elif child.name in ("em", "i"):
            inner = child.get_text()
            if inner:
                result += f"*{inner}*"
        elif child.name == "code":
            inner = child.get_text()
            if inner:
                result += f"`{inner}`"
        elif child.name == "a":
            text = child.get_text()
            href = child.get("href", "")
            if text and href:
                result += f"[{text}]({href})"
            elif text:
                result += text
        elif child.name == "img":
            # Convert img tags to markdown image syntax
            src = child.get("src", "")
            alt = child.get("alt", "")
            if src:
                result += f"![{alt}]({src})"
        else:
            # Recurse for any other inline elements (skip bare NavigableStrings)
            if hasattr(child, "children"):
                result += _inline_markdown(child)
            else:
                result += str(child)
    return result
