from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.kpis import router as kpis_router
from backend.app.config import settings
from backend.app.db.database import get_db, init_db
from backend.app.db.models import Conversation, Document, Message, QueryFeedback, User, UsageEvent
from backend.app.services.auth_service import create_access_token, hash_password, verify_password
from backend.app.services.demo_dashboard_service import DEMO_ACCOUNT_ASSIGNMENTS
from backend.app.services.document_service import delete_document, ensure_default_user, ensure_demo_users, get_document_by_id, get_documents, save_document
from backend.app.services.embedding_service import embedding_provider
from backend.app.services.file_registry import compute_content_hash, is_supported_extension
from backend.app.services.rag_service import rag_service

app = FastAPI(title=settings.app_name, version="1.0.0")
app.include_router(dashboard_router)
app.include_router(kpis_router)
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
app.mount(
  "/assets",
  StaticFiles(directory=str(FRONTEND_DIST / "assets"), check_dir=False),
  name="frontend-assets",
)


DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>J&J KPI Dashboard</title>
    <style>
      :root { color-scheme: light; font-family: Inter, Arial, sans-serif; --bg:#eef4fb; --card:#fff; --muted:#64748b; --accent:#1d4ed8; --border:#dbeafe; }
      * { box-sizing: border-box; }
      body { margin:0; background: linear-gradient(180deg,#eef6ff 0%, #f8fafc 100%); color:#0f172a; }
      .auth-shell { min-height:100vh; display:grid; place-items:center; padding:24px; }
      .auth-card, .dashboard-shell { width:min(100%,1100px); background:rgba(255,255,255,.96); border:1px solid rgba(148,163,184,.2); border-radius:24px; box-shadow:0 20px 70px rgba(15,23,42,.08); }
      .auth-card { max-width:480px; padding:32px; }
      .brand { display:inline-flex; align-items:center; justify-content:center; width:52px; height:52px; background:linear-gradient(135deg,#1d4ed8,#60a5fa); color:#fff; border-radius:16px; font-weight:800; }
      .auth-card h1 { margin:12px 0 8px; font-size:2.1rem; }
      .auth-card p { color:var(--muted); margin:0 0 20px; }
      form { display:grid; gap:16px; }
      label { display:grid; gap:8px; font-weight:600; }
      input, select, button { font:inherit; }
      input, select { width:100%; padding:12px 14px; border:1px solid #dbe3f0; border-radius:12px; }
      button { border:none; border-radius:12px; background:linear-gradient(135deg,#1d4ed8,#3b82f6); color:#fff; padding:12px 18px; font-weight:700; cursor:pointer; }
      .demo-note { margin-top:16px; color:var(--muted); font-size:.9rem; }
      .error { margin-top:12px; padding:10px 12px; border-radius:10px; background:#fef2f2; color:#b91c1c; border:1px solid #fecaca; }
      .dashboard-shell { padding:18px; display:block; }
      .topbar { display:flex; justify-content:space-between; gap:12px; align-items:center; margin-bottom:18px; }
      .topbar h2 { margin:0; }
      .toolbar { display:flex; gap:12px; align-items:center; }
      .kpis { display:grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap:14px; margin-bottom:18px; }
      .kpi-card, .panel { background:var(--card); border:1px solid rgba(148,163,184,.2); border-radius:18px; padding:18px; }
      .kpi-card strong { font-size:1.8rem; display:block; margin:8px 0 4px; }
      .kpi-card small { color:var(--muted); }
      .panel-grid { display:grid; grid-template-columns: repeat(auto-fit,minmax(260px,1fr)); gap:16px; }
      .list { display:grid; gap:10px; }
      .item { display:flex; justify-content:space-between; gap:12px; align-items:center; padding:10px 0; border-bottom:1px solid #edf2f7; }
      .item:last-child { border-bottom:none; }
      .badge { font-size:0.76rem; background:#dbeafe; color:#1d4ed8; border-radius:999px; padding:6px 8px; font-weight:700; }
      .loading { color:var(--muted); }
      @media (max-width: 700px) { .topbar { flex-direction:column; align-items:flex-start; } .toolbar { width:100%; justify-content:space-between; } }
    </style>
  </head>
  <body>
    <div id="authView" class="auth-shell">
      <div class="auth-card">
        <div class="brand">J&J</div>
        <h1>Medical Device KPI Console</h1>
        <p>Secure operational dashboard for business services teams.</p>
        <form id="loginForm">
          <label>Email
            <input id="email" type="email" value="admin@local.dev" required />
          </label>
          <label>Password
            <input id="password" type="password" value="local-dev" required />
          </label>
          <button type="submit">Sign in</button>
        </form>
        <div id="loginError" class="error" style="display:none"></div>
        <div class="demo-note">Demo access: admin@local.dev / local-dev</div>
      </div>
    </div>

    <div id="dashboardView" class="auth-shell" style="display:none;">
      <div class="dashboard-shell">
        <div class="topbar">
          <div>
            <div style="color:#64748b; font-size:.72rem; letter-spacing:.08em; text-transform:uppercase; font-weight:700;">Operational dashboard</div>
            <h2>Performance overview</h2>
          </div>
          <div class="toolbar">
            <label style="display:grid; gap:6px; font-weight:600;">Persona
              <select id="personaSelect">
                <option value="operations">Operations</option>
                <option value="sales">Sales</option>
              </select>
            </label>
            <button type="button" id="logoutBtn">Sign out</button>
          </div>
        </div>

        <div id="statusCards" class="kpis"></div>
        <div class="panel-grid">
          <div class="panel">
            <h3>Metric overview</h3>
            <div id="metricCards" class="list"></div>
          </div>
          <div class="panel">
            <h3>Responsibilities</h3>
            <div id="responsibilityList" class="list"></div>
          </div>
          <div class="panel">
            <h3>Actions</h3>
            <div id="actionList" class="list"></div>
          </div>
          <div class="panel">
            <h3>Workflow</h3>
            <div id="workflowList" class="list"></div>
          </div>
        </div>
      </div>
    </div>

    <script>
      const authView = document.getElementById('authView');
      const dashboardView = document.getElementById('dashboardView');
      const loginError = document.getElementById('loginError');
      const metricCards = document.getElementById('metricCards');
      const responsibilityList = document.getElementById('responsibilityList');
      const actionList = document.getElementById('actionList');
      const workflowList = document.getElementById('workflowList');
      const statusCards = document.getElementById('statusCards');
      const personaSelect = document.getElementById('personaSelect');

      function showError(message) {
        loginError.textContent = message;
        loginError.style.display = message ? 'block' : 'none';
      }

      function showDashboard() {
        authView.style.display = 'none';
        dashboardView.style.display = 'grid';
      }

      function showLogin() {
        authView.style.display = 'grid';
        dashboardView.style.display = 'none';
      }

      async function fetchDashboard(persona='operations') {
        const response = await fetch(`/api/dashboard/persona?persona=${persona}`);
        if (!response.ok) throw new Error('Dashboard could not load');
        return response.json();
      }

      async function login(email, password) {
        const response = await fetch('/api/auth/login', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ email, password })
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || 'Login failed');
        return payload;
      }

      function renderStatus(items) {
        statusCards.innerHTML = items.map(item => `
          <div class="kpi-card">
            <small>${item.label}</small>
            <strong>${item.value}</strong>
          </div>
        `).join('');
      }

      function renderMetrics(items) {
        metricCards.innerHTML = items.map(item => `
          <div class="item">
            <div>
              <strong>${item.label}</strong>
              <div style="color:#64748b; font-size:.8rem;">${item.status || 'healthy'}</div>
            </div>
            <span class="badge">${typeof item.value === 'number' ? item.value.toLocaleString() : item.value}${item.unit ? ' ' + item.unit : ''}</span>
          </div>
        `).join('');
      }

      function renderList(target, items, renderer) {
        if (!items || !items.length) {
          target.innerHTML = '<div class="loading">No data available.</div>';
          return;
        }
        target.innerHTML = items.map(renderer).join('');
      }

      function loadDashboard(persona) {
        fetchDashboard(persona)
          .then((payload) => {
            renderStatus(payload.status_panel?.items || []);
            renderMetrics(payload.metric_panel?.items || []);
            renderList(responsibilityList, payload.responsibility_panel?.items || [], (item) => `
              <div class="item">
                <div><strong>${item.title}</strong><div style="color:#64748b; font-size:.8rem;">${item.owner}</div></div>
                <div style="text-align:right;"><div class="badge">${item.status}</div><div style="color:#64748b; font-size:.75rem; margin-top:4px;">${item.due}</div></div>
              </div>
            `);
            renderList(actionList, payload.action_panel?.items || [], (item) => `
              <div class="item">
                <div><strong>${item.title}</strong><div style="color:#64748b; font-size:.8rem;">${item.kpi}</div></div>
                <span class="badge">${item.priority}</span>
              </div>
            `);
            renderList(workflowList, payload.workflow_panel?.items || [], (item) => `
              <div class="item">
                <div><strong>${item.step}</strong></div>
                <span class="badge">${item.status}</span>
              </div>
            `);
          })
          .catch((err) => {
            showError(err.message || 'Dashboard failed to load');
          });
      }

      document.getElementById('loginForm').addEventListener('submit', async (event) => {
        event.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        try {
          showError('');
          await login(email, password);
          showDashboard();
          loadDashboard(personaSelect.value);
        } catch (err) {
          showError(err.message || 'Login failed');
        }
      });

      document.getElementById('logoutBtn').addEventListener('click', () => {
        showLogin();
        showError('');
      });

      personaSelect.addEventListener('change', () => {
        loadDashboard(personaSelect.value);
      });
    </script>
  </body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def root_page() -> Response:
  index_file = FRONTEND_DIST / "index.html"
  if index_file.is_file():
    return FileResponse(index_file)
  if settings.environment == "development":
    return RedirectResponse("http://localhost:5173/")
  raise HTTPException(status_code=503, detail="Build the React frontend before serving the application.")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page() -> Response:
  return root_page()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8, max_length=128)
    name: str = "User"


class LoginRequest(BaseModel):
    email: str
    password: str
    persona_id: str | None = None


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    conversation_id: str | None = None


class FeedbackRequest(BaseModel):
    question: str
    answer: str
    helpful: bool = True
    notes: str | None = None


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    with next(get_db()) as db:
        ensure_default_user(db)
    ensure_demo_users(db)


def get_current_user(db: Session = Depends(get_db)) -> User:
    if settings.auth_mode == "single-user":
        return ensure_default_user(db)
    raise HTTPException(status_code=401, detail="Authentication is disabled for local mode only.")


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "environment": settings.environment,
        "auth_mode": settings.auth_mode,
        "database": "sqlite",
        "vector_store": "chroma",
    }


@app.get("/api/health/llm")
def llm_health() -> dict:
    try:
        sample = embedding_provider.embed_query("health check")
        return {"status": "ok", "provider": settings.default_provider, "model": settings.embedding_model, "probe": len(sample)}
    except Exception as exc:  # pragma: no cover
        return {"status": "degraded", "provider": settings.default_provider, "error": str(exc)}


@app.post("/api/auth/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    email = payload.email.strip().lower()
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    user = User(email=email, name=payload.name.strip() or "User", password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "name": user.name}


@app.post("/api/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    email = payload.email.strip().lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    assignment = DEMO_ACCOUNT_ASSIGNMENTS.get(user.email)
    if assignment is None:
      raise HTTPException(status_code=403, detail="No dashboard is assigned to this account")
    if payload.persona_id and payload.persona_id != assignment["persona_id"]:
      raise HTTPException(status_code=403, detail="This account is not assigned to the selected designation")
    role = assignment["role"]
    return {
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "role": role,
      "persona_id": assignment["persona_id"],
      "designation": assignment["designation"],
        "access_token": create_access_token(user.id, user.email, role),
    }


@app.get("/api/documents")
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    docs = get_documents(db, user.id)
    return [{
        "document_id": doc.document_id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "created_at": doc.created_at.isoformat(),
        "error_message": doc.error_message,
    } for doc in docs]


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    suffix = Path(file.filename).suffix.lower()
    if not is_supported_extension(suffix):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")
    data = await file.read()
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail="File exceeds configured size limit")

    document = save_document(db, data, file.filename, owner_id=user.id)
    return {
        "document_id": document.document_id,
        "filename": document.filename,
        "status": document.status,
        "chunk_count": document.chunk_count,
    }


@app.get("/api/documents/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    doc = db.query(Document).filter(Document.document_id == document_id, Document.owner_id == user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "document_id": doc.document_id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "created_at": doc.created_at.isoformat(),
        "metadata": doc.metadata_json,
        "error_message": doc.error_message,
    }


@app.get("/api/documents/{document_id}/preview")
def preview_document(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    doc = db.query(Document).filter(Document.document_id == document_id, Document.owner_id == user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(doc.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file not found")
    text = path.read_text(encoding="utf-8", errors="replace")
    return {"document_id": doc.document_id, "filename": doc.filename, "preview": text[:4000]}


@app.get("/api/documents/{document_id}/status")
def document_status(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    doc = db.query(Document).filter(Document.document_id == document_id, Document.owner_id == user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document_id": doc.document_id, "status": doc.status, "chunk_count": doc.chunk_count, "error_message": doc.error_message}


@app.post("/api/documents/{document_id}/retry")
def retry_document(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    doc = db.query(Document).filter(Document.document_id == document_id, Document.owner_id == user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.status = "processing"
    doc.error_message = None
    db.add(doc)
    db.commit()
    return {"document_id": doc.document_id, "status": doc.status}


@app.delete("/api/documents/{document_id}")
def delete_document_route(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    doc = db.query(Document).filter(Document.document_id == document_id, Document.owner_id == user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    delete_document(db, doc.document_id)
    return {"status": "deleted", "document_id": document_id}


@app.get("/api/conversations")
def list_conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    conversations = db.query(Conversation).filter(Conversation.owner_id == user.id).order_by(Conversation.updated_at.desc()).all()
    return [{"conversation_id": c.conversation_id, "title": c.title, "updated_at": c.updated_at.isoformat()} for c in conversations]


@app.post("/api/conversations")
def create_conversation(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    conversation_id = f"conv-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{user.id}"
    conversation = Conversation(conversation_id=conversation_id, title="New chat", owner_id=user.id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return {"conversation_id": conversation.conversation_id, "title": conversation.title}


@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    conversation = db.query(Conversation).filter(Conversation.conversation_id == conversation_id, Conversation.owner_id == user.id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = db.query(Message).filter(Message.conversation_id == conversation.id).order_by(Message.created_at.asc()).all()
    return {"conversation_id": conversation.conversation_id, "title": conversation.title, "messages": [{"role": m.role, "content": m.content, "citation_json": m.citation_json} for m in messages]}


@app.patch("/api/conversations/{conversation_id}")
def rename_conversation(conversation_id: str, title: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    conversation = db.query(Conversation).filter(Conversation.conversation_id == conversation_id, Conversation.owner_id == user.id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation.title = title
    db.add(conversation)
    db.commit()
    return {"conversation_id": conversation.conversation_id, "title": conversation.title}


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation_route(conversation_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    conversation = db.query(Conversation).filter(Conversation.conversation_id == conversation_id, Conversation.owner_id == user.id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conversation)
    db.commit()
    return {"status": "deleted", "conversation_id": conversation_id}


@app.post("/api/chat")
def chat(payload: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    conversation = None
    if payload.conversation_id:
        conversation = db.query(Conversation).filter(Conversation.conversation_id == payload.conversation_id, Conversation.owner_id == user.id).first()
    if conversation is None:
        conversation = Conversation(conversation_id=f"conv-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{user.id}", title="New chat", owner_id=user.id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    chunks = rag_service.search(payload.question, top_k=settings.retrieval_top_k)
    answer = rag_service.answer(payload.question, chunks)
    db.add(Message(conversation_id=conversation.id, role="user", content=payload.question, citation_json="[]"))
    db.add(Message(conversation_id=conversation.id, role="assistant", content=answer["answer"], citation_json=str(answer.get("citations", []))))
    db.add(UsageEvent(event_type="question", event_data=payload.question[:200], user_id=user.id))
    db.commit()

    return {
        "conversation_id": conversation.conversation_id,
        "answer": answer["answer"],
        "citations": answer.get("citations", []),
        "sources": chunks,
    }


@app.post("/api/feedback")
def feedback(payload: FeedbackRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    record = QueryFeedback(question=payload.question, answer=payload.answer, helpful=payload.helpful, notes=payload.notes)
    db.add(record)
    db.commit()
    return {"status": "saved"}


@app.get("/api/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    docs = db.query(Document).filter(Document.owner_id == user.id).count()
    successful = db.query(Document).filter(Document.owner_id == user.id, Document.status == "completed").count()
    conversations = db.query(Conversation).filter(Conversation.owner_id == user.id).count()
    question_count = db.query(Message).join(Conversation).filter(Conversation.owner_id == user.id, Message.role == "user").count()
    chunks = sum(doc.chunk_count for doc in db.query(Document).filter(Document.owner_id == user.id).all())
    return {
        "total_documents": docs,
        "indexed_documents": successful,
        "total_conversations": conversations,
        "total_questions": question_count,
        "total_chunks": chunks,
        "token_usage": 0,
    }


@app.get("/api/dashboard/activity")
def dashboard_activity(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    events = db.query(UsageEvent).filter(UsageEvent.user_id == user.id).order_by(UsageEvent.created_at.desc()).limit(10).all()
    return [{"type": event.event_type, "detail": event.event_data, "created_at": event.created_at.isoformat()} for event in events]


@app.get("/api/settings")
def settings_route() -> dict:
    return {
        "provider": settings.default_provider,
        "chat_model": settings.chat_model,
        "embedding_model": settings.embedding_model,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "top_k": settings.retrieval_top_k,
        "theme": "light",
        "voice_enabled": True,
    }


@app.patch("/api/settings")
def update_settings(payload: dict) -> dict:
    return {"status": "updated", "values": payload}


@app.get("/kpis/{kpi_id}", response_class=HTMLResponse)
def kpi_detail_page(kpi_id: str) -> Response:
    return root_page()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
