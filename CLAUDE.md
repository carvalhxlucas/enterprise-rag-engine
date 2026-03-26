# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

Enterprise RAG Engine — a production-ready Retrieval-Augmented Generation (RAG) system. Users upload documents (PDF, DOCX, TXT), which get chunked, embedded, and stored in Qdrant. They then chat with an AI assistant (GPT-4o-mini) that retrieves relevant chunks and streams answers.

Stack: FastAPI + Celery (backend), Next.js 14 (frontend), PostgreSQL (metadata), Qdrant (vectors), Redis (task queue), Langfuse (observability).

## Commands

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run API server
uvicorn app.main:app --reload --port 8000

# Run Celery worker (separate terminal)
celery -A app.workers.celery_app worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev       # dev server on port 3001
npm run build
npm run lint      # ESLint
```

### Docker (full stack)

```bash
cp env.docker.example .env
docker compose up -d
```

### Tests

```bash
cd backend
pip install -r requirements-test.txt

# Unit tests (no external services needed)
pytest tests/ -m unit -v

# Single test file
pytest tests/unit/test_chunking.py -v

# RAG evals (requires OPENAI_API_KEY; use mock context to skip Qdrant)
pip install -r requirements-eval.txt
RAG_EVAL_USE_MOCK_CONTEXT=1 pytest tests/evals -m evals -v
```

`pytest.ini` sets `asyncio_mode = auto`. Markers: `unit` (fast, no external deps) and `evals` (LLM-as-judge via Ragas).

## Architecture

### Request Flows

**Document ingestion:**
1. `POST /api/v1/ingest/upload` → validates MIME, saves to `./storage/<user_id>/<uuid>_<filename>`, enqueues Celery task, returns `task_id`
2. Frontend polls `GET /api/v1/ingest/status/{task_id}` for progress
3. Celery task (`workers/ingestion_tasks.py`): extract text → chunk (1500 chars / 200 overlap) → embed with `text-embedding-3-small` → upsert to Qdrant → update `Document` record in PostgreSQL

**Chat:**
1. `POST /api/v1/chat/stream` → embeds user query → retrieves top-5 Qdrant hits filtered by `user_id` → builds context → streams GPT-4o-mini response as SSE

### Multi-tenancy

All operations are scoped by the `X-User-ID` HTTP header. This header is required on all `/ingest`, `/chat`, and `/documents` endpoints (enforced in `app/core/security.py` and `app/dependencies.py`). Qdrant queries include a `user_id` filter; file storage is namespaced by `user_id`.

### Key Services

| File | Responsibility |
|------|---------------|
| `app/services/chat.py` | `ChatOrchestrator` — full RAG pipeline |
| `app/services/embeddings.py` | OpenAI embeddings wrapper |
| `app/services/storage.py` | File save/load scoped by user |
| `app/workers/ingestion_tasks.py` | Celery task: extract → chunk → embed → upsert |
| `app/utils/chunking.py` | Text splitting logic |
| `app/utils/text_extraction.py` | PDF (PyMuPDF), DOCX (python-docx), TXT parsing |
| `app/core/observability.py` | Langfuse `@observe()` integration |
| `app/config.py` | Pydantic Settings; all env vars; cached via `get_settings()` |

### Qdrant Collection

Collection name: `documents`. Vectors: 1536-dim (`text-embedding-3-small`). Each point payload includes: `user_id`, `doc_id`, `filename`, `page_number`, `chunk_index`, `access_level`.

## CI

`.github/workflows/rag-evals.yml` runs RAG evals on PRs touching `backend/**`. Uses `RAG_EVAL_USE_MOCK_CONTEXT=1` to inject fixed contexts from `tests/evals/fixtures/ground_truth_rag.json` — no Qdrant needed. Requires `OPENAI_API_KEY` repository secret.

## Environment Variables

Copy `env.backend.example` → `.env` for local dev. Key variables: `DATABASE_URL`, `QDRANT_URL`, `REDIS_URL`, `OPENAI_API_KEY`, `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` (optional). Frontend uses `NEXT_PUBLIC_API_BASE_URL` (default: `http://localhost:8000`).
