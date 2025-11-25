from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200, max_size: int = 5_000_000):

    if not text:
        return []

    if len(text) > max_size:
        logger.warning(f"Text size ({len(text)} chars) exceeds max_size ({max_size}). Truncating to {max_size} chars.")
        text = text[:max_size]

    text = text.replace("\r\n", "\n")

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    total = len(text)

    while start < total:
        end = min(start + chunk_size, total)
        chunks.append(text[start:end])
        
        if end >= total:
            break
        start = end - chunk_overlap
        if start <= 0:
            start = 1

    return chunks


def chunks_with_metadata(text: str, source: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Dict]:

    chunks = chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return [
        {
            "text": chunk,
            "source": source,
            "chunk_id": f"{source}__{i}"
        }
        for i, chunk in enumerate(chunks, start=1)
    ]
