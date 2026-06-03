import logging
import os
from collections import Counter
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from .chunker import Chunk
from .config import settings

logger = logging.getLogger(__name__)


class SearchResult:
    def __init__(
        self,
        text: str,
        score: float,
        source: str,
        content_type: str,
        author: str,
        timestamp: Optional[str],
        chunk_id: str,
    ):
        self.text = text
        self.score = score
        self.source = source
        self.content_type = content_type
        self.author = author
        self.timestamp = timestamp
        self.chunk_id = chunk_id

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "score": round(self.score, 3),
            "source": self.source,
            "content_type": self.content_type,
            "author": self.author,
            "timestamp": self.timestamp,
            "chunk_id": self.chunk_id,
        }


class VectorStore:
    def __init__(self):
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"VectorStore ready. {self.collection.count()} chunks in collection.")

    def upsert(self, embedded_chunks: list[tuple[Chunk, list[float]]]) -> int:
        if not embedded_chunks:
            return 0

        before = self.collection.count()

        # Batch upserts — ChromaDB recommends ≤500 per call
        batch_size = 500
        for i in range(0, len(embedded_chunks), batch_size):
            batch = embedded_chunks[i : i + batch_size]
            self.collection.upsert(
                ids=[c.id for c, _ in batch],
                embeddings=[emb for _, emb in batch],
                documents=[c.text for c, _ in batch],
                metadatas=[
                    {
                        "source": c.source,
                        "content_type": c.content_type,
                        "author": c.author,
                        "timestamp": c.timestamp or "",
                        "chunk_index": c.chunk_index,
                        "total_chunks": c.total_chunks,
                        "original_id": c.original_id,
                    }
                    for c, _ in batch
                ],
            )

        return self.collection.count() - before

    def query(self, query_embedding: list[float], top_k: Optional[int] = None) -> list[SearchResult]:
        top_k = top_k or settings.top_k
        count = self.collection.count()
        if count == 0:
            return []

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )

        items = []
        for doc, meta, dist, cid in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
            results["ids"][0],
        ):
            items.append(SearchResult(
                text=doc,
                score=round(1.0 - dist, 3),
                source=meta.get("source", ""),
                content_type=meta.get("content_type", ""),
                author=meta.get("author", ""),
                timestamp=meta.get("timestamp") or None,
                chunk_id=cid,
            ))
        return items

    def get_stats(self) -> dict:
        count = self.collection.count()
        if count == 0:
            return {"total_chunks": 0, "sources": {}, "content_types": {}}

        result = self.collection.get(include=["metadatas"], limit=min(count, 50_000))
        metas = result["metadatas"]
        return {
            "total_chunks": count,
            "sources": dict(Counter(m["source"] for m in metas)),
            "content_types": dict(Counter(m["content_type"] for m in metas)),
        }

    def reset(self) -> None:
        self.client.delete_collection(settings.collection_name)
        self.collection = self.client.create_collection(
            name=settings.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Knowledge base reset.")
