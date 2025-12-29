"""Parser for regulation detail pages."""

import re
from dataclasses import dataclass, field
from typing import Optional

from bs4 import BeautifulSoup, Tag

# Regex patterns for metadata extraction
DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
RG_RE = re.compile(r"^R\.G\.\s*(\d+)\s*$", re.IGNORECASE)
EK_RE = re.compile(r"^EK\s*([IVXLCDM]+)\s*$", re.IGNORECASE)
AE_RE = re.compile(r"^A\.E\.\s*(\d+)\s*$", re.IGNORECASE)


@dataclass
class DocEvent:
    """Represents an enactment or amendment event."""
    
    event_date: str  # Raw date string "dd.mm.yyyy"
    rg_no: Optional[str] = None  # R.G. (Official Gazette) number
    ek: Optional[str] = None  # EK (Appendix) Roman numeral
    ae_no: Optional[str] = None  # A.E. (Decision) number


@dataclass
class ParsedDocument:
    """Result of parsing a regulation page."""
    
    title: str
    events: list[DocEvent] = field(default_factory=list)
    text: str = ""
    raw_html: str = ""


def soupify(html: str) -> BeautifulSoup:
    """Create BeautifulSoup parser using lxml for messy Word HTML."""
    return BeautifulSoup(html, "lxml")


def clean_text(s: str) -> str:
    """Normalize whitespace in text."""
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_events_from_left_cell(left_td: Tag) -> list[DocEvent]:
    """
    Parse event metadata from the left cell of the regulation table.
    
    The left cell contains multiple lines like:
    - 03.05.2019
    - R.G. 62
    - EK III
    - A.E. 349
    
    Events are grouped by date (a new date starts a new event).
    """
    lines = [t for t in left_td.stripped_strings]
    events: list[DocEvent] = []
    current: Optional[DocEvent] = None

    for line in lines:
        line = line.strip().rstrip(",")
        if not line:
            continue

        # New date starts a new event
        if DATE_RE.match(line):
            current = DocEvent(event_date=line)
            events.append(current)
            continue

        if current is None:
            continue

        # Match other metadata
        if (m := RG_RE.match(line)):
            current.rg_no = m.group(1)
        elif (m := EK_RE.match(line)):
            current.ek = m.group(1).upper()
        elif (m := AE_RE.match(line)):
            current.ae_no = m.group(1)

    return events


def parse_doc_page(doc_html: str) -> ParsedDocument:
    """
    Parse a regulation detail page.
    
    Extracts:
    - Title from <title> tag
    - Events from the left table cell
    - Clean text content from the body
    
    Args:
        doc_html: Raw HTML of the regulation page
        
    Returns:
        ParsedDocument with extracted data
    """
    soup = soupify(doc_html)

    # Extract title
    title = ""
    if soup.title:
        title = soup.title.get_text(" ", strip=True)
    title = clean_text(title)

    # Find events from the first table row
    events: list[DocEvent] = []
    first_row = soup.select_one("tr")
    if first_row:
        tds = first_row.find_all("td", recursive=False)
        if len(tds) >= 1:
            events = parse_events_from_left_cell(tds[0])

    # Remove scripts and styles
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # Extract clean text from body
    body = soup.body or soup
    text = clean_text(body.get_text(" ", strip=True))

    return ParsedDocument(
        title=title,
        events=events,
        text=text,
        raw_html=doc_html,
    )
