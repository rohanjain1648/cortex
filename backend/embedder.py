import asyncio
import logging
from functools import lru_cache
from typing import Callable, Optional

from .config import settings
from .chunker import Chunk

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_model():
    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        model = SentenceTransformer(settings.embedding_model)
        logger.info("Embedding model loaded")
        return model
    except ImportError as e:
        raise RuntimeError("sentence-transformers not installed. Run: pip install sentence-transformers") from e


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = _load_model()
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return embeddings.tolist()


async def embed_chunks_async(
    chunks: list[Chunk],
    batch_size: Optional[int] = None,
    on_progress: Optional[Callable[[int], None]] = None,
) -> list[tuple[Chunk, list[float]]]:
    batch_size = batch_size or settings.embed_batch_size
    loop = asyncio.get_running_loop()
    results: list[tuple[Chunk, list[float]]] = []
    total = len(chunks)

    for i in range(0, total, batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c.text for c in batch]
        embeddings = await loop.run_in_executor(None, embed_texts, texts)
        results.extend(zip(batch, embeddings))

        if on_progress:
            on_progress(min(100, int((i + len(batch)) / total * 100)))

    return results
