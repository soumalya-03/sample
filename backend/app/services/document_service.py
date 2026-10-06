from __future__ import annotations

import json
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.db.models import Document, DocumentProcessingJob, User, Workspace
from backend.app.services.auth_service import hash_password
from backend.app.services.demo_accounts import DEMO_USERS
from backend.app.services.file_registry import compute_content_hash, extract_uploaded_text, is_supported_extension

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except Exception:  # pragma: no cover - fallback when optional vendor packages are missing
    class RecursiveCharacterTextSplitter:
        def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 0):
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap

        def split_text(self, text: str) -> list[str]:
            chunk_size = max(1, self.chunk_size)
            overlap = min(self.chunk_overlap, chunk_size - 1)
            chunks: list[str] = []
            index = 0
            while index < len(text):
                end = min(len(text), index + chunk_size)
                chunk = text[index:end]
                chunks.append(chunk)
                if end >= len(text):
                    break
                index = max(index + chunk_size - overlap, index + 1)
            return chunks


UPLOAD_ROOT = Path(settings.upload_dir.replace("./", "")).resolve()


def ensure_default_user(db: Session) -> User:
    stmt = select(User).where(User.email == "admin@local.dev")
    user = db.execute(stmt).scalar_one_or_none()
    if user is None:
        user = User(email="admin@local.dev", name="Local Admin", password_hash="hash:local-dev")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def ensure_demo_users(db: Session) -> None:
    demo_users = [
        ("sales@local.dev", "Jordan Lee", "local-sales"),
        *[
            (demo_user["email"], demo_user["name"], demo_user["password"])
            for demo_user in DEMO_USERS
        ],
    ]
    for email, name, password in demo_users:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            db.add(User(email=email, name=name, password_hash=hash_password(password)))
    db.commit()


def build_document_record(filename: str, file_size: int, owner_id: int | None = None, workspace_id: int | None = None) -> tuple[Document, str]:
    document_id = uuid.uuid4().hex
    storage_dir = UPLOAD_ROOT / document_id
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = storage_dir / filename
    return Document(
        document_id=document_id,
        filename=filename,
        file_type=Path(filename).suffix.lower(),
        file_size=file_size,
        storage_path=str(storage_path),
        status="uploaded",
        owner_id=owner_id,
        workspace_id=workspace_id,
    ), document_id


def save_document(db: Session, file_data, filename: str, owner_id: int | None = None, workspace_id: int | None = None) -> Document:
    if not is_supported_extension(Path(filename).suffix):
        raise ValueError(f"Unsupported file type for {filename}")

    document, document_id = build_document_record(filename, len(file_data), owner_id, workspace_id)
    storage_dir = Path(document.storage_path).parent
    storage_dir.mkdir(parents=True, exist_ok=True)
    with open(document.storage_path, "wb") as handle:
        handle.write(file_data)

    content_hash = compute_content_hash(document.storage_path)
    document.content_hash = content_hash
    document.status = "processing"
    db.add(document)
    db.commit()
    db.refresh(document)

    job = DocumentProcessingJob(document_id=document.document_id, status="processing", message="Extracting text and indexing")
    db.add(job)
    db.commit()

    extracted_text, metadata = extract_uploaded_text(document.storage_path, Path(filename).suffix.lower())
    if not extracted_text.strip():
        document.status = "failed"
        document.error_message = "No usable text could be extracted from the document."
        db.add(document)
        db.commit()
        return document

    document.metadata_json = json.dumps({"content_hash": content_hash, **metadata})
    document.status = "completed"
    db.add(document)
    db.commit()

    splitter = RecursiveCharacterTextSplitter(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    chunks = splitter.split_text(extracted_text)
    document.chunk_count = len(chunks)
    db.add(document)
    db.commit()
    db.refresh(document)

    return document


def get_documents(db: Session, user_id: int | None = None) -> list[Document]:
    query = db.query(Document)
    if user_id is not None:
        query = query.filter(Document.owner_id == user_id)
    return query.order_by(Document.created_at.desc()).all()


def get_document_by_id(db: Session, document_id: str) -> Document | None:
    return db.query(Document).filter(Document.document_id == document_id).first()


def delete_document(db: Session, document_id: str) -> None:
    document = get_document_by_id(db, document_id)
    if document is None:
        return
    storage_file = Path(document.storage_path)
    if storage_file.exists():
        storage_file.unlink(missing_ok=True)
    db.delete(document)
    db.commit()
