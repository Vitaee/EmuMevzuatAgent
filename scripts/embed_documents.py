"""CLI script to chunk and embed all documents.

Usage:
    python -m scripts.embed_documents
"""

import asyncio
import sys
from datetime import datetime


async def main():
    """Chunk and embed all documents."""
    print("=" * 60)
    print("MEVZUAT AI - DOCUMENT EMBEDDING")
    print(f"Started at: {datetime.now().isoformat()}")
    print("=" * 60)
    print()
    
    # Check OpenRouter configuration
    from app.config import get_settings
    settings = get_settings()
    
    if not settings.openrouter_api_key:
        print("[ERROR] OpenRouter API key not configured!")
        print("Please set OPENROUTER_API_KEY in your .env file")
        sys.exit(1)
    
    print(f"Using embedding model: {settings.embedding_model}")
    print(f"Embedding dimension: {settings.embedding_dim}")
    print()
    
    # Run embedding
    from app.agent.tools.embedder import embed_all_documents
    
    print("Processing documents...")
    print("-" * 40)
    
    results = await embed_all_documents()
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print(f"Documents processed: {results['processed']}")
    print(f"Chunks created: {results['chunks_created']}")
    print(f"Errors: {len(results['errors'])}")
    
    if results['errors']:
        print("\nErrors:")
        for err in results['errors']:
            print(f"  - Doc {err['doc_id']}: {err['error']}")
    
    print(f"\nFinished at: {datetime.now().isoformat()}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
