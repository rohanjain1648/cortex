import asyncio
import json
import logging
import os
import tempfile
import uuid
import zipfile
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .chunker import chunk_content
from .embedder import _load_model, embed_chunks_async
from .parsers.base import BaseParser
from .parsers.instagram import InstagramParser
from .parsers.linkedin import LinkedInParser
from .parsers.twitter import TwitterParser
from .rag import RAGPipeline
from .vectorstore import VectorStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

PARSERS: list[type[BaseParser]] = [LinkedInParser, TwitterParser, InstagramParser]
ingestion_jobs: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Warming up embedding model (may download ~90MB on first run)...")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _load_model)
    logger.info("Ready.")
    yield


app = FastAPI(title="Cortex API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

vector_store = VectorStore()
rag = RAGPipeline(vector_store)


class ChatRequest(BaseModel):
    query: str
    history: list[dict] = []


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/stats")
def get_stats():
    return vector_store.get_stats()


@app.delete("/api/reset")
def reset_kb():
    vector_store.reset()
    return {"message": "Knowledge base reset"}


@app.post("/api/ingest")
async def ingest(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_hint: Optional[str] = Form(None),
):
    content = await file.read()
    job_id = str(uuid.uuid4())[:8]
    ingestion_jobs[job_id] = {"status": "pending", "progress": 0, "message": "Queued"}
    background_tasks.add_task(_run_ingestion, job_id, content, file.filename or "upload.zip")
    return {"job_id": job_id, "status": "pending"}


@app.get("/api/ingest/{job_id}")
def get_job(job_id: str):
    job = ingestion_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    async def generate():
        async for event in rag.stream_answer(request.query):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


async def _run_ingestion(job_id: str, content: bytes, filename: str) -> None:
    job = ingestion_jobs[job_id]
    try:
        job.update({"status": "parsing", "progress": 5, "message": "Opening archive..."})

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, filename)
            with open(zip_path, "wb") as f:
                f.write(content)

            if not zipfile.is_zipfile(zip_path):
                job.update({"status": "error", "message": "Not a valid ZIP archive."})
                return

            with zipfile.ZipFile(zip_path) as zf:
                names = zf.namelist()
                parser = next((cls() for cls in PARSERS if cls.can_parse(names)), None)

                if not parser:
                    job.update({
                        "status": "error",
                        "message": "Could not detect platform. Expected a LinkedIn, Twitter/X, or Instagram export ZIP.",
                    })
                    return

                job.update({
                    "status": "parsing", "progress": 15,
                    "message": f"Parsing {parser.source_name} export...",
                    "source": parser.source_name,
                })

                parsed = parser.parse(zf)

        if not parsed:
            job.update({"status": "error", "message": "No usable content found in the export."})
            return

        job.update({"progress": 30, "message": f"Parsed {len(parsed)} items. Chunking..."})

        all_chunks = [chunk for item in parsed for chunk in chunk_content(item)]

        job.update({"progress": 40, "message": f"{len(all_chunks)} chunks created. Embedding..."})

        def on_progress(pct: int):
            job.update({"progress": 40 + int(pct * 0.5), "message": f"Embedding... {pct}%"})

        embedded = await embed_chunks_async(all_chunks, on_progress=on_progress)

        job.update({"progress": 92, "message": "Upserting to vector store..."})
        new_count = vector_store.upsert(embedded)
        total = len(all_chunks)

        job.update({
            "status": "done",
            "progress": 100,
            "message": f"Done. {new_count} new chunks added ({total - new_count} duplicates skipped).",
            "stats": vector_store.get_stats(),
            "source": parser.source_name,
        })

    except Exception as e:
        logger.exception(f"Ingestion job {job_id} failed")
        job.update({"status": "error", "message": str(e)})
