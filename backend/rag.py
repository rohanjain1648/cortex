import asyncio
import logging
from typing import AsyncIterator

from google import genai
from google.genai import types

from .config import settings
from .embedder import embed_texts
from .vectorstore import VectorStore

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an AI assistant analyzing a person's social media content and writing.
Answer questions based solely on the provided context from their posts, articles, and profile.
Be specific and cite the source content naturally in your response.
If the context doesn't contain enough information to answer clearly, say so.\
"""


class RAGPipeline:
    def __init__(self, store: VectorStore):
        self.store = store
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def stream_answer(self, query: str) -> AsyncIterator[dict]:
        loop = asyncio.get_running_loop()

        embedding = await loop.run_in_executor(None, lambda: embed_texts([query])[0])
        results = self.store.query(embedding, top_k=settings.top_k)

        if not results:
            yield {"type": "text", "content": "The knowledge base is empty. Please ingest some social media exports first via the 'Ingest Data' tab."}
            yield {"type": "sources", "sources": []}
            yield {"type": "done"}
            return

        context_parts = []
        for i, r in enumerate(results, 1):
            ts = f", {r.timestamp[:10]}" if r.timestamp else ""
            label = f"[{i}] {r.source.capitalize()} {r.content_type}{ts}"
            context_parts.append(f"{label}:\n{r.text}")

        context = "\n\n---\n\n".join(context_parts)
        user_message = (
            f"Context from social media exports:\n\n{context}\n\n"
            f"---\n\nQuestion: {query}\n\n"
            "Answer based on the context above, referencing specific content when relevant."
        )

        async for chunk in await self._client.aio.models.generate_content_stream(
            model=settings.gemini_model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                max_output_tokens=1024,
            ),
        ):
            if chunk.text:
                yield {"type": "text", "content": chunk.text}

        yield {"type": "sources", "sources": [r.to_dict() for r in results]}
        yield {"type": "done"}
