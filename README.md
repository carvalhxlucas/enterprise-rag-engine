# Enterprise RAG Engine

A production-ready **Retrieval-Augmented Generation (RAG)** application that lets users upload documents (PDF, DOCX, TXT), ingest them into a vector store, and chat with an AI assistant over their content. The system uses OpenAI for embeddings and chat, Qdrant for vector search, PostgreSQL for document metadata, and Celery for async ingestion.

<img width="1916" height="896" alt="enterprise-rag-engine" src="https://github.com/user-attachments/assets/17f8e1ab-653c-4d86-8bd8-8443c5cf1e8f" />


---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick Start (Docker)](#quick-start-docker)
- [Local Development](#local-development)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Document Ingestion Pipeline](#document-ingestion-pipeline)
- [RAG Chat Flow](#rag-chat-flow)
- [Testing](#testing)
- [Observability](#observability)
- [Project Structure](#project-structure)

---

## Features

- **Document ingestion**: Upload PDF, DOCX, and TXT files; content is extracted, chunked, embedded, and stored in Qdrant with metadata in PostgreSQL.
- **Async processing**: Ingestion runs in background Celery tasks; clients poll task status by `task_id`.
- **RAG chat**: Streaming chat over user documents with configurable persona (technical / sarcastic), temperature, and optional hybrid search.
- **Multi-tenant by user**: All operations are scoped by `X-User-ID` header; documents and vectors are filtered by `user_id`.
- **Observability**: Optional Langfuse integration for tracing (e.g. health endpoint).
- **RAG evals**: Ragas-based evaluation (answer relevance, faithfulness) with optional mocked context for CI.

---

## Architecture

```
                    ┌─────────────┐
                    │   Frontend  │  Next.js (port 3001)
                    │  (Next.js)  │
                    └──────┬──────┘
                           │ HTTP / SSE
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           Backend (FastAPI, port 8000)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ /api/v1/    │  │ /api/v1/     │  │ /api/v1/     │  │ /health         │ │
│  │ ingest/*   │  │ chat/*       │  │ documents    │  │                 │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────────┘  └─────────────────┘ │
│         │                │                                                 │
│         │                │  ChatOrchestrator → EmbeddingService            │
│         │                │                 → QdrantClient (search)        │
│         │                │                 → OpenAI (completions)          │
│         │                │                                                 │
│         │  StorageService│  Celery (ingest_document_task)                  │
│         │  → save_file   │  → extract text → chunk → embed → Qdrant        │
│         │  Celery.delay  │  → PostgreSQL (Document record)                 │
└─────────┼────────────────┼───────────────────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ PostgreSQL  │   │   Qdrant     │   │    Redis     │   │   Langfuse   │
│ (metadata)  │   │ (vectors)    │   │ (Celery)     │   │ (optional)   │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
```

- **Frontend**: Next.js app; talks to backend API (ingest, chat stream, documents).
- **Backend**: FastAPI app; exposes REST + SSE; uses PostgreSQL (SQLAlchemy async), Qdrant, Redis, and optionally Langfuse.
- **Celery worker**: Runs `ingest_document_task` (extract → chunk → embed → upsert to Qdrant, update Document in PostgreSQL).
- **Qdrant**: Vector store; collection `documents` with payloads `user_id`, `doc_id`, `filename`, `page_number`, `chunk_index`.
- **PostgreSQL**: Stores `Document` rows (user_id, filename, mime_type, storage_path, status, error_message).
- **Redis**: Broker and result backend for Celery.
- **Langfuse**: Optional; used for tracing (e.g. `/health`); requires Clickhouse + PostgreSQL when self-hosted via Docker.

---

## Tech Stack

| Layer        | Technology |
|-------------|------------|
| Backend     | Python 3.11+, FastAPI, Uvicorn, Pydantic, SQLAlchemy (async), asyncpg |
| Vector DB   | Qdrant |
| Relational  | PostgreSQL 16 |
| Queue       | Celery, Redis |
| LLM / Embed | OpenAI (GPT-4o-mini, text-embedding-3-small) |
| Doc parsing | PyMuPDF (PDF), python-docx (DOCX), stdlib (TXT) |
| Frontend    | Next.js 14, React 18, TypeScript, Tailwind CSS |
| Observability | Langfuse (optional) |
| Evals       | Ragas (answer_relevancy, faithfulness) |

---

## Prerequisites

- **Docker & Docker Compose** (for full stack), or
- **Local**: Python 3.11+, Node 22+, PostgreSQL 16, Redis, Qdrant. Optional: Langfuse (or omit keys to disable).
- **OpenAI API key** for embeddings and chat (and for RAG evals if you run them).

---

## Quick Start (Docker)

1. **Clone and set environment**

   ```bash
   git clone <repo-url>
   cd enterprise-rag-engine
   cp env.docker.example .env.docker
   cp env.backend.example .env.backend
   ```

   In `.env.docker` or `.env.backend`, set at least:

   - `OPENAI_API_KEY=sk-...` (required for ingest and chat)

   For Docker Compose, the stack reads from `.env` by default; you can symlink or copy:

   ```bash
   cp .env.docker .env
   ```

2. **Start the stack**

   ```bash
   docker compose up -d
   ```

   This starts:

   - **PostgreSQL** (5433)
   - **Clickhouse** (8123, 9001) — for Langfuse
   - **Qdrant** (6333)
   - **Redis** (6378)
   - **Langfuse** (3100)
   - **Backend** (8000)
   - **Celery worker** (same image as backend)
   - **Frontend** (3001)

3. **Verify**

   - Backend: `curl http://localhost:8000/health`
   - Frontend: open `http://localhost:3001`
   - Langfuse: `http://localhost:3100` (if keys are set)

4. **Upload and chat**

   - Use the frontend or call the API with header `X-User-ID: <user-id>` (see [API Reference](#api-reference)).

---

## Local Development

### Backend

1. **Create virtualenv and install deps**

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Run infrastructure** (PostgreSQL, Redis, Qdrant; optionally Langfuse via Docker or cloud)

   ```bash
   docker compose up -d postgres redis qdrant
   # Optional: docker compose up -d langfuse clickhouse
   ```

3. **Configure env**

   Copy `env.backend.example` to `.env` in project root or `backend/`, and set:

   - `DATABASE_URL` (e.g. `postgresql+asyncpg://rag_user:rag_password@localhost:5432/enterprise_rag` — adjust port if mapped to 5433)
   - `QDRANT_URL` (e.g. `http://localhost:6333`)
   - `REDIS_URL` (e.g. `redis://localhost:6379/0` or `redis://localhost:6378/0` if using Docker Redis on 6378)
   - `OPENAI_API_KEY`
   - Optional: `LANGFUSE_*` if using Langfuse

4. **Run API and worker**

   ```bash
   # Terminal 1
   uvicorn app.main:app --reload --port 8000

   # Terminal 2
   celery -A app.workers.celery_app worker --loglevel=info
   ```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` (or use default if already set in env).

---

## Configuration

Backend is configured via environment variables (Pydantic Settings). Main ones:

| Variable | Description | Example |
|----------|-------------|---------|
| `APP_NAME` | Service name | `Enterprise RAG Engine` |
| `APP_ENV` | Environment label | `local`, `staging`, `production` |
| `DEBUG` | Debug mode | `true` / `false` |
| `DATABASE_URL` | PostgreSQL (async) URL | `postgresql+asyncpg://user:pass@host:5432/db` |
| `QDRANT_URL` | Qdrant HTTP URL | `http://localhost:6333` |
| `QDRANT_API_KEY` | Optional Qdrant API key | — |
| `REDIS_URL` | Redis URL for Celery | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `OLLAMA_BASE_URL` | Optional local LLM | `http://localhost:11434` |
| `USE_LOCAL_LLM` | Use local LLM for chat | `false` |
| `USE_LOCAL_EMBEDDINGS` | Use local embeddings | `false` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | — |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | — |
| `LANGFUSE_HOST` | Langfuse server URL | `http://localhost:3100` |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated) | `http://localhost:3001,http://localhost:3000` |
| `ALLOWED_HOSTS` | TrustedHost hosts (comma-separated) | `localhost,127.0.0.1` |
| `STORAGE_PATH` | Local path for uploaded files | `./storage` |

---

## API Reference

Base URL: `http://localhost:8000` (or your backend host).

All ingest and chat endpoints expect the **`X-User-ID`** header (any string) to scope data per user.

### Health

- **GET /health**  
  Returns `{"status": "ok", "service": "<APP_NAME>"}`. Traced with Langfuse when configured.

### Ingest

- **POST /api/v1/ingest/upload**  
  - **Headers**: `X-User-ID: <user-id>`  
  - **Body**: multipart form with `file` (PDF, DOCX, or TXT).  
  - **Response**: `202 Accepted` with `{"task_id": "<celery-task-id>", "message": "..."}`.  
  - **Errors**: 400 if filename missing or MIME invalid; 500 on storage/task failure.

- **GET /api/v1/ingest/status/{task_id}**  
  - **Response**: `200` with `{"status": "pending"|"processing"|"completed"|"failed"|"unknown", "step": "...", "progress": 0..100, "error": "..."}`.

### Chat

- **POST /api/v1/chat/stream**  
  - **Headers**: `X-User-ID: <user-id>`, `Content-Type: application/json`.  
  - **Body**:  
    ```json
    {
      "message": "User message",
      "history": [{"role": "user"|"assistant"|"system", "content": "..."}],
      "config": {
        "persona": "technical" | "sarcastic",
        "temperature": 0.7,
        "use_hybrid_search": true
      }
    }
    ```  
  - **Response**: `200` with `Content-Type: text/event-stream`. Events: `data: {"content": "..."}` chunks, then `event: end`.

### Documents

- **GET /api/v1/documents**  
  - **Response**: `200` with `{"documents": []}` (list endpoint; currently returns empty list).

---

## Document Ingestion Pipeline

1. **Upload** (API): Client sends file; backend validates MIME (PDF, DOCX, TXT), saves file via `StorageService` under `STORAGE_PATH/<user_id>/<uuid>_<filename>`, enqueues `ingest_document_task.delay(path, user_id, filename, mime_type)`.
2. **Celery task**:
   - Extract text by MIME (PyMuPDF, python-docx, or plain text).
   - Chunk with `chunk_pages(..., chunk_size=1500, chunk_overlap=200)`.
   - Generate embeddings via OpenAI `text-embedding-3-small`.
   - Ensure Qdrant collection `documents` exists (create if not); upsert points with payload `user_id`, `doc_id`, `filename`, `page_number`, `chunk_index`.
   - Create/update `Document` in PostgreSQL (status `processing` → `completed` or `failed`).
3. **Status**: Client polls `GET /api/v1/ingest/status/{task_id}` until `status` is `completed` or `failed`.

---

## RAG Chat Flow

1. Client sends **POST /api/v1/chat/stream** with `message`, `history`, and `config`.
2. **ChatOrchestrator**:
   - Builds system prompt from `config.persona` (technical vs sarcastic).
   - Embeds the user message; searches Qdrant with filter `user_id = X-User-ID`, limit 5.
   - Builds context string from hit payloads (filename, page, chunk).
   - Calls OpenAI Chat Completions (GPT-4o-mini) with system + context + history + user message, stream=True.
3. Response is streamed as SSE; each chunk is `data: {"content": "..."}`; stream ends with `event: end`.

---

## Testing

### Unit tests

- **Location**: `backend/tests/` (excluding `evals/`).
- **Markers**: `unit` for fast tests; `evals` for RAG evals (Ragas).
- **Run**:
  ```bash
  cd backend
  pip install -r requirements-test.txt
  pytest tests/ -m unit -v
  ```
- **Scope**: Config, chunking, MIME validation, storage, security, ingest API (mocked storage/Celery), chat API (mocked orchestrator), documents, health. No real DB/Qdrant/OpenAI required when using the provided fixtures.

### RAG evals (Ragas)

- **Location**: `backend/tests/evals/`.
- **Docs**: `backend/tests/evals/README.md`.
- **Run** (with OpenAI key):
  ```bash
  cd backend
  pip install -r requirements-eval.txt
  export OPENAI_API_KEY=sk-...
  pytest tests/evals -m evals -v
  ```
- **CI**: Use `RAG_EVAL_USE_MOCK_CONTEXT=1` and `reference_contexts` in `fixtures/ground_truth_rag.json` to avoid Qdrant and reduce API cost; Ragas still uses the LLM as judge.

---

## Observability

- **Langfuse**: If `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_HOST` are set, the backend creates a Langfuse client and decorates selected endpoints (e.g. `/health` with `@observe()`). On shutdown, it flushes the client.
- **Docker**: The Compose stack runs Langfuse (with PostgreSQL and Clickhouse) and passes Langfuse env to the backend; leave keys empty to disable.

---

## Project Structure

```
enterprise-rag-engine/
├── backend/
│   ├── app/
│   │   ├── api/v1/routers/   # ingest, chat, documents
│   │   ├── core/              # security (X-User-ID), observability (Langfuse)
│   │   ├── db/                # SQLAlchemy models, async session, init_db
│   │   ├── models/            # Pydantic schemas (request/response)
│   │   ├── services/          # ChatOrchestrator, EmbeddingService, StorageService
│   │   ├── utils/             # chunking, mime_validator, text_extraction (PDF/DOCX/TXT)
│   │   ├── workers/           # Celery app, ingestion_tasks
│   │   ├── config.py          # Settings (Pydantic Settings)
│   │   ├── dependencies.py    # get_qdrant_client, get_app_settings
│   │   └── main.py            # FastAPI app, lifespan, CORS, routes
│   ├── tests/
│   │   ├── api/               # test_ingest, test_chat, test_documents
│   │   ├── unit/              # test_config, test_chunking, test_mime_validator, test_storage, test_security
│   │   ├── evals/             # RAG evals (Ragas), fixtures
│   │   ├── conftest.py        # pytest fixtures, TestClient, mocks
│   │   └── test_main.py       # create_app, health
│   ├── requirements.txt
│   ├── requirements-test.txt
│   ├── requirements-eval.txt
│   ├── pytest.ini
│   └── Dockerfile
├── frontend/                  # Next.js app
│   ├── Dockerfile
│   └── package.json
├── .github/workflows/
│   └── rag-evals.yml          # Run RAG evals on PRs (backend changes)
├── docker-compose.yml        # Full stack: postgres, clickhouse, qdrant, redis, langfuse, backend, celery-worker, frontend
├── env.backend.example
├── env.docker.example
└── README.md
```

---

## License

See repository license file.
