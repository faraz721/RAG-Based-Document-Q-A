from typing import List, Dict, Any
from utils.config import CHUNK_SIZE, CHUNK_OVERLAP


def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks by character count, preferring sentence boundaries."""
    if not text or not text.strip():
        return []

    text = text.strip()
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        if end < text_len:
            # Prefer breaking at sentence or paragraph
            search_region = text[start:end]
            for sep in ["\n\n", "\n", ". ", "? ", "! ", "; ", ", "]:
                idx = search_region.rfind(sep)
                if idx > chunk_size * 0.4:
                    end = start + idx + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_len:
            break

        start = max(start + 1, end - overlap)

    return chunks


def create_chunks(
    pages: List[Dict[str, Any]], doc_id: str, filename: str
) -> List[Dict[str, Any]]:
    """Create chunk objects with metadata from extracted pages."""
    chunks = []
    chunk_index = 0

    for page_info in pages:
        page_num = page_info.get("page", 1)
        text = page_info.get("text", "")
        page_chunks = split_text(text)

        for chunk_text in page_chunks:
            chunks.append(
                {
                    "chunk_id": f"{doc_id}_{chunk_index}",
                    "doc_id": doc_id,
                    "filename": filename,
                    "page": page_num,
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                }
            )
            chunk_index += 1

    return chunks
