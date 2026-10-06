from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DocChat"
    environment: str = "development"
    auth_mode: str = "single-user"
    secret_key: str = "dev-secret-change-me"
    jwt_secret: str = "dev-jwt-change-me"
    database_url: str = "sqlite:///./data/app.db"
    upload_dir: str = "./storage/uploads"
    vector_store_dir: str = "./data/chroma"
    max_file_size_mb: int = 20
    allowed_extensions: str = ".pdf,.docx,.txt,.md,.csv,.xlsx,.pptx,.html,.json"
    default_provider: str = "ollama"
    chat_model: str = "llama3.1"
    embedding_model: str = "nomic-embed-text"
    ollama_base_url: str = "http://localhost:11434"
    groq_api_key: str = ""
    retrieval_top_k: int = 5
    chunk_size: int = 1000
    chunk_overlap: int = 150
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_extensions.split(",") if item.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()

ROOT_DIR = Path(__file__).resolve().parents[2]
APP_DIR = ROOT_DIR / "backend"
DATA_DIR = ROOT_DIR / "data"
UPLOAD_ROOT = ROOT_DIR / settings.upload_dir.replace("./", "")
VECTOR_ROOT = ROOT_DIR / settings.vector_store_dir.replace("./", "")

for path in (DATA_DIR, UPLOAD_ROOT, VECTOR_ROOT):
    path.mkdir(parents=True, exist_ok=True)

os.makedirs(str(UPLOAD_ROOT), exist_ok=True)
os.makedirs(str(VECTOR_ROOT), exist_ok=True)
