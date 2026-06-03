import re
from dataclasses import dataclass, field
from typing import Optional

from .parsers.base import ParsedContent

MAX_CHUNK_CHARS = 1200
OVERLAP_CHARS = 150
MIN_CHUNK_CHARS = 80

_ATOMIC_TYPES = {"tweet", "story", "comment"}


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    content_type: str
    author: str
    timestamp: Optional[str]
    chunk_index: int
    total_chunks: int
    original_id: str
    metadata: dict = field(default_factory=dict)


def chunk_content(content: ParsedContent) -> list[Chunk]:
    text = content.text.strip()
    if not text:
        return []

    ts_str = content.timestamp.isoformat() if content.timestamp else None

    if content.content_type in _ATOMIC_TYPES or len(text) <= MAX_CHUNK_CHARS:
        return [_make_chunk(content, text, 0, 1, ts_str)]

    raw_chunks = _split_text(text)
    n = len(raw_chunks)
    return [_make_chunk(content, chunk, i, n, ts_str) for i, chunk in enumerate(raw_chunks)]


def _make_chunk(content: ParsedContent, text: str, idx: int, total: int, ts: Optional[str]) -> Chunk:
    return Chunk(
        id=f"{content.id}_{idx}",
        text=text,
        source=content.source,
        content_type=content.content_type,
        author=content.author,
        timestamp=ts,
        chunk_index=idx,
        total_chunks=total,
        original_id=content.id,
        metadata=content.metadata,
    )


def _split_text(text: str) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(para) > MAX_CHUNK_CHARS:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_paragraph(para))
        elif len(current) + len(para) + 2 <= MAX_CHUNK_CHARS:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            overlap = current[-OVERLAP_CHARS:] if OVERLAP_CHARS and current else ""
            current = (overlap + "\n\n" + para).strip() if overlap else para

    if current:
        chunks.append(current)

    return [c for c in chunks if len(c) >= MIN_CHUNK_CHARS]


def _split_paragraph(para: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", para)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= MAX_CHUNK_CHARS:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks
