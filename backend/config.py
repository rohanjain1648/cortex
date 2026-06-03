from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    embedding_model: str = "all-MiniLM-L6-v2"
    embed_batch_size: int = 32

    chroma_persist_dir: str = "./chroma_db"
    collection_name: str = "knowledge_base"

    max_chunk_chars: int = 1200
    chunk_overlap_chars: int = 150
    min_chunk_chars: int = 80

    top_k: int = 6

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
