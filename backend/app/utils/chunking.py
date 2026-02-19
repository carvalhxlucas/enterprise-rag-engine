from typing import List, Tuple


def split_text_into_chunks(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    if not text:
        return []
    normalized = " ".join(text.split())
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]
    chunks: List[str] = []
    start = 0
    while start < len(normalized):
        end = start + chunk_size
        chunk = normalized[start:end]
        chunks.append(chunk)
        if end >= len(normalized):
            break
        start = end - chunk_overlap
        if start < 0:
            start = 0
    return chunks


def chunk_pages(pages: List[Tuple[int, str]], chunk_size: int, chunk_overlap: int) -> List[Tuple[int, int, str]]:
    result: List[Tuple[int, int, str]] = []
    for page_number, text in pages:
        page_chunks = split_text_into_chunks(text, chunk_size, chunk_overlap)
        for index, chunk in enumerate(page_chunks):
            result.append((page_number, index, chunk))
    return result

