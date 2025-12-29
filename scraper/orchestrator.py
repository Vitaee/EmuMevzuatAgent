"""Crawl orchestrator for scraping all regulations."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx

from app.config import get_settings
from scraper.client import create_client, fetch
from scraper.parsers.regulation import ParsedDocument, parse_doc_page
from scraper.parsers.toc import TocItem, parse_toc

settings = get_settings()


@dataclass
class ScrapedDocument:
    """Complete scraped document with TOC metadata and page content."""
    
    # From TOC
    code: str
    toc_title: str
    url: str
    parent_code: Optional[str]
    depth: int
    sort_key: int
    
    # From page
    page_title: str
    events: list
    text: str
    raw_html: str
    
    # Metadata
    scraped_at: datetime


async def crawl_toc(client: httpx.AsyncClient) -> list[TocItem]:
    """
    Fetch and parse the Table of Contents.
    
    Args:
        client: HTTP client to use
        
    Returns:
        List of parsed TOC items
    """
    toc_url = settings.scraper_base_url + "Content-en.htm"
    print(f"[TOC] Fetching {toc_url}")
    
    toc_html = await fetch(client, toc_url)
    items = parse_toc(toc_html)
    
    print(f"[TOC] Found {len(items)} items")
    return items


async def crawl_document(
    client: httpx.AsyncClient,
    item: TocItem,
    semaphore: asyncio.Semaphore,
) -> Optional[ScrapedDocument]:
    """
    Fetch and parse a single regulation document.
    
    Args:
        client: HTTP client to use
        item: TOC item to fetch
        semaphore: Concurrency control semaphore
        
    Returns:
        ScrapedDocument or None if the item is not a valid document
    """
    # Skip non-HTM files
    if not item.href.lower().endswith(".htm"):
        return None
    
    url = settings.scraper_base_url + item.href
    
    async with semaphore:
        try:
            print(f"[DOC] Fetching {item.code}: {item.title[:50]}...")
            html = await fetch(client, url)
        except Exception as e:
            print(f"[ERROR] Failed to fetch {url}: {e}")
            return None
    
    parsed = parse_doc_page(html)
    
    return ScrapedDocument(
        code=item.code,
        toc_title=item.title,
        url=url,
        parent_code=item.parent_code,
        depth=item.depth,
        sort_key=item.sort_key,
        page_title=parsed.title,
        events=parsed.events,
        text=parsed.text,
        raw_html=parsed.raw_html,
        scraped_at=datetime.utcnow(),
    )


async def crawl_all() -> tuple[list[TocItem], list[ScrapedDocument]]:
    """
    Crawl all regulation documents.
    
    Returns:
        Tuple of (TOC items, scraped documents)
    """
    semaphore = asyncio.Semaphore(settings.scraper_concurrency)
    
    async with create_client() as client:
        # First, get the TOC
        toc_items = await crawl_toc(client)
        
        # Then fetch all documents concurrently (with rate limiting)
        tasks = [
            crawl_document(client, item, semaphore)
            for item in toc_items
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out errors and None values
        documents: list[ScrapedDocument] = []
        for result in results:
            if isinstance(result, ScrapedDocument):
                documents.append(result)
            elif isinstance(result, Exception):
                print(f"[ERROR] Task failed: {result}")
        
        print(f"\n[DONE] Scraped {len(documents)} documents from {len(toc_items)} TOC items")
        return toc_items, documents
