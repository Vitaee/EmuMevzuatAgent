"""HTTP client for scraping with robust encoding detection."""

import httpx
from charset_normalizer import from_bytes

from app.config import get_settings

settings = get_settings()

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MevzuatAI-Scraper/1.0; +contact@example.com)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.8,tr;q=0.6",
}

TIMEOUT = httpx.Timeout(
    connect=settings.scraper_timeout_connect,
    read=settings.scraper_timeout_read,
    write=10.0,
    pool=10.0,
)


def decode_html(content: bytes) -> str:
    """
    Decode bytes into text robustly.
    
    Uses charset_normalizer to detect encoding from bytes.
    Falls back to utf-8 with replacement if detection fails.
    """
    best = from_bytes(content).best()
    if best and best.encoding:
        return str(best)
    return content.decode("utf-8", errors="replace")


async def fetch(client: httpx.AsyncClient, url: str) -> str:
    """
    Fetch a URL and return decoded HTML content.
    
    Args:
        client: The httpx AsyncClient to use
        url: URL to fetch
        
    Returns:
        Decoded HTML content as string
        
    Raises:
        httpx.HTTPStatusError: If request fails
    """
    response = await client.get(
        url,
        headers=DEFAULT_HEADERS,
        timeout=TIMEOUT,
        follow_redirects=True,
    )
    response.raise_for_status()
    return decode_html(response.content)


def create_client() -> httpx.AsyncClient:
    """
    Create a configured httpx AsyncClient for scraping.
    
    Returns:
        Configured AsyncClient with connection pooling and retries
    """
    limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
    transport = httpx.AsyncHTTPTransport(retries=3)
    
    return httpx.AsyncClient(
        limits=limits,
        transport=transport,
        timeout=TIMEOUT,
    )
