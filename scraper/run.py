"""CLI entry point for running the scraper.

Usage:
    python -m scraper.run

This script:
1. Scrapes all regulation documents from the EMU mevzuat website
2. Saves them to the database via the FastAPI API endpoints
"""

import asyncio
import sys
from datetime import datetime

import httpx

from app.config import get_settings
from scraper.orchestrator import ScrapedDocument, crawl_all
from scraper.parsers.regulation import DocEvent

settings = get_settings()

# API base URL (assuming FastAPI is running locally)
API_BASE = "http://localhost:8000/api/v1"


def event_to_dict(event: DocEvent) -> dict:
    """Convert DocEvent to API-compatible dict."""
    # Parse date from dd.mm.yyyy to yyyy-mm-dd
    parts = event.event_date.split(".")
    if len(parts) == 3:
        date_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
    else:
        date_str = event.event_date
    
    return {
        "event_date": date_str,
        "rg_no": event.rg_no,
        "ek": event.ek,
        "ae_no": event.ae_no,
    }


def doc_to_payload(doc: ScrapedDocument) -> dict:
    """Convert ScrapedDocument to API payload."""
    return {
        "code": doc.code,
        "title": doc.toc_title,
        "url": doc.url,
        "parent_code": doc.parent_code,
        "depth": doc.depth,
        "sort_key": doc.sort_key,
        "language": "en",
        "page_title": doc.page_title,
        "text_content": doc.text,
        "raw_html": doc.raw_html,
        "events": [event_to_dict(e) for e in doc.events],
        "chunks": [],  # Chunks would be added separately after embedding
    }


async def save_to_api(documents: list[ScrapedDocument]) -> tuple[int, int]:
    """
    Save scraped documents to the API.
    
    Returns:
        Tuple of (success_count, error_count)
    """
    success = 0
    errors = 0
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for doc in documents:
            payload = doc_to_payload(doc)
            
            try:
                # Try upsert endpoint
                response = await client.post(
                    f"{API_BASE}/reg-docs/upsert",
                    json=payload,
                )
                
                if response.status_code in (200, 201):
                    success += 1
                    print(f"[OK] Saved {doc.code}: {doc.toc_title[:40]}...")
                else:
                    errors += 1
                    print(f"[FAIL] {doc.code}: {response.status_code} - {response.text[:100]}")
                    
            except Exception as e:
                errors += 1
                print(f"[ERROR] {doc.code}: {e}")
    
    return success, errors


async def main():
    """Main entry point."""
    print("=" * 60)
    print("MEVZUAT AI SCRAPER")
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Target: {settings.scraper_base_url}")
    print("=" * 60)
    print()
    
    # Check if API is available
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE}/health")
            if response.status_code != 200:
                print(f"[WARNING] API health check failed: {response.status_code}")
                print("Make sure the FastAPI server is running: uvicorn app.main:app --reload")
                sys.exit(1)
            print("[OK] API is available\n")
    except httpx.ConnectError:
        print("[ERROR] Cannot connect to API at http://localhost:8000")
        print("Make sure the FastAPI server is running: uvicorn app.main:app --reload")
        sys.exit(1)
    
    # Crawl all documents
    print("Phase 1: Scraping documents...")
    print("-" * 40)
    toc_items, documents = await crawl_all()
    
    print()
    print("Phase 2: Saving to database...")
    print("-" * 40)
    success, errors = await save_to_api(documents)
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print(f"TOC items found: {len(toc_items)}")
    print(f"Documents scraped: {len(documents)}")
    print(f"Saved successfully: {success}")
    print(f"Errors: {errors}")
    print(f"Finished at: {datetime.now().isoformat()}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
