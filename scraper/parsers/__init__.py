"""Parsers package for scraping."""

from scraper.parsers.regulation import DocEvent, parse_doc_page
from scraper.parsers.toc import TocItem, parse_toc

__all__ = ["TocItem", "parse_toc", "DocEvent", "parse_doc_page"]
