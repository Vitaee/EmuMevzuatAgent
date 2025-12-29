"""Parser for Table of Contents (Content-en.htm)."""

import re
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup

# Regex to match TOC entries like "5.1.2. Title text"
TOC_CODE_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\.\s*(.*\S)\s*$")


@dataclass
class TocItem:
    """Represents a single item in the Table of Contents."""
    
    code: str          # e.g., "5.1.2"
    title: str         # e.g., "Regulations for Student Scholarships"
    href: str          # relative URL to the page
    parent_code: Optional[str]  # parent code for hierarchy
    depth: int         # depth level (1, 2, 3, ...)
    sort_key: int      # position in the TOC


def soupify(html: str) -> BeautifulSoup:
    """Create BeautifulSoup parser using lxml for messy Word HTML."""
    return BeautifulSoup(html, "lxml")


def parent_of(code: str) -> Optional[str]:
    """
    Get the parent code of a given code.
    
    Examples:
        "5.1.2" -> "5.1"
        "5.1" -> "5"
        "5" -> None
    """
    parts = code.split(".")
    if len(parts) == 1:
        return None
    return ".".join(parts[:-1])


def parse_toc(toc_html: str) -> list[TocItem]:
    """
    Parse the Table of Contents HTML to extract document hierarchy.
    
    Args:
        toc_html: Raw HTML of Content-en.htm
        
    Returns:
        List of TocItem objects representing the document hierarchy
    """
    soup = soupify(toc_html)
    items: list[TocItem] = []
    sort = 0

    # Find all anchor tags with href
    for anchor in soup.select("a[href]"):
        text = anchor.get_text(" ", strip=True)
        match = TOC_CODE_RE.match(text)
        
        if not match:
            continue

        code = match.group(1)
        title = match.group(2)
        href = anchor["href"].strip()
        sort += 1

        items.append(
            TocItem(
                code=code,
                title=title,
                href=href,
                parent_code=parent_of(code),
                depth=len(code.split(".")),
                sort_key=sort,
            )
        )

    # De-duplicate by (code, href) because Word HTML can repeat anchors
    unique: dict[tuple[str, str], TocItem] = {}
    for item in items:
        unique[(item.code, item.href)] = item
    
    return list(unique.values())
