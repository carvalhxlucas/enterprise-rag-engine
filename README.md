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

- **Document ingestion**: Upload PDF, DOCX, and TXT files; content is extracted, chunked, embedded with OpenAI, and stored in Qdrant (including the chunk text) with metadata tracked in PostgreSQL.
- **Async processing**: Ingestion runs in background Celery tasks; clients poll task status by `task_id` and receive a `document_id` on completion.
- **Document deletion**: Remove a document and all its associated data (vectors from Qdrant, file from disk, record from PostgreSQL) via a single API call.
- **Document preview**: Uploaded files are previewed inline in the UI — native PDF rendering, plain-text display, or a fallback message for unsupported types.
- **RAG chat**: Streaming chat over user documents with configurable persona (technical / sarcastic) and temperature. Retrieved chunks include the actual text content passed as context to the LLM.
- **Multi-tenant by user**: All operations are scoped by `X-User-ID` header; documents and vectors are filtered by `user_id`.
- **Observability**: Optional Langfuse integration for tracing and cost/latency tracking.
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
│                         Backend (FastAPI, port 8000)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────────────┐  │
│  │ /api/v1/     │  │ /api/v1/     │  │ /api/v1/documents              │  │
│  │ ingest/*     │  │ chat/*       │  │   GET  /documents              │  │
│  │              │  │              │  │   DELETE /documents/{id}       │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────────────────────────┘  │
│         │                 │                                                │
│         │                 │  ChatOrchestrator → EmbeddingService           │
│         │                 │                 → QdrantClient (search)        │
│         │                 │                 → OpenAI (completions)         │
│         │                 │                                                │
│  StorageService + Celery.delay()   Celery (ingest_document_task)           │
│  → save to disk            │       → extract text → chunk → embed          │
│                            │       → upsert to Qdrant (with text)          │
│                            │       → create Document in PostgreSQL          │
└────────────────────────────┼────────────────────────────────────────────-─┘
                             │
          ┌──────────────────┼──────────────────┬──────────────────┐
          ▼                  ▼                  ▼                  ▼
   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
   │ PostgreSQL  │   │   Qdrant    │   │    Redis    │   │  Langfuse   │
   │ (metadata)  │   │  (vectors)  │   │  (Celery)   │   │ (optional)  │
   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
```

- **Frontend**: Next.js app; handles file upload with inline preview, ingestion progress, streaming chat, and document deletion.
- **Backend**: FastAPI app; REST + SSE; uses PostgreSQL (SQLAlchemy async + asyncpg), Qdrant, Redis, and optionally Langfuse.
- **Celery worker**: Runs `ingest_document_task` (extract → chunk → embed → upsert to Qdrant with chunk text → update Document status in PostgreSQL).
- **Qdrant**: Vector store; collection `documents` with payloads `user_id`, `doc_id`, `filename`, `page_number`, `chunk_index`, `text`, `access_level`.
- **PostgreSQL**: Stores `Document` rows (user_id, filename, mime_type, storage_path, status, error_message).
- **Redis**: Broker and result backend for Celery.
- **Langfuse**: Optional; tracing for cost and latency. Requires Clickhouse + PostgreSQL when self-hosted.

---

## Tech Stack

| Layer         | Technology                                                   |
|--------------|--------------------------------------------------------------|
| Backend      | Python 3.11+, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy (async), asyncpg |
| Vector DB    | Qdrant                                                        |
| Relational   | PostgreSQL 16                                                 |
| Queue        | Celery 5, Redis 7                                             |
| LLM / Embed  | OpenAI (GPT-4o-mini, text-embedding-3-small)                 |
| Doc parsing  | PyMuPDF (PDF), python-docx (DOCX), stdlib (TXT)              |
| Frontend     | Next.js 14, React 18, TypeScript, Tailwind CSS               |
| Observability | Langfuse (optional)                                          |
| Evals        | Ragas (answer_relevancy, faithfulness)                        |

---

## Prerequisites

- **Docker & Docker Compose** — for the full stack (recommended).
- **Or locally**: Python 3.11+, Node 22+, PostgreSQL 16, Redis 7, Qdrant. Langfuse is optional.
- **OpenAI API key** — required for embeddings (ingestion) and chat completions. Also used by RAG evals.

---

## Quick Start (Docker)

1. **Clone and configure**

   ```bash
   git clone <repo-url>
   cd enterprise-rag-engine
   cp env.docker.example .env
   ```

   Open `.env` and set your OpenAI key:

   ```
   OPENAI_API_KEY=sk-...
   ```

   > The `LANGFUSE_ENCRYPTION_KEY` in the example file must be a 64-character hex string. The example ships a valid pre-generated value; replace it if you want your own.

2. **Start the stack**

   ```bash
   docker compose up -d
   ```

   Services started:

   | Service        | Port  |
   |---------------|-------|
   | Frontend       | 3001  |
   | Backend API    | 8000  |
   | PostgreSQL     | 5433  |
   | Qdrant         | 6333  |
   | Redis          | 6378  |
   | Langfuse       | 3100  |
   | Clickhouse     | 8123  |

3. **Verify**

   ```bash
   curl http://localhost:8000/health
   # {"status":"ok","service":"Enterprise RAG Engine"}
   ```

   Open **http://localhost:3001** for the UI.

4. **Use**
   - Upload a PDF, DOCX, or TXT via the sidebar. The Document Viewer on the right renders a live preview while ingestion runs in the background.
   - Once indexed (green "Indexed" badge), ask questions in the chat. The assistant retrieves relevant chunks from your document and streams an answer.
   - To remove the document, click the trash icon in the Document Viewer header. This deletes vectors, the stored file, and the database record.

---

## Local Development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Start infrastructure:

```bash
docker compose up -d postgres redis qdrant
```

Create a `.env` in the project root (or `backend/`) with at minimum:

```
DATABASE_URL=postgresql+asyncpg://rag_user:rag_password@localhost:5433/enterprise_rag
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6378/0
OPENAI_API_KEY=sk-...
```

Run API and worker:

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
npm run dev        # http://localhost:3000
npm run lint
```

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` in `frontend/.env.local` if the backend runs on a different address.

---

## Configuration

Backend is configured via environment variables (Pydantic Settings, case-insensitive, read from `.env`).

| Variable               | Description                                     | Default / Example                         |
|------------------------|-------------------------------------------------|-------------------------------------------|
| `APP_ENV`              | Environment label                               | `local`                                   |
| `DATABASE_URL`         | PostgreSQL async URL                            | `postgresql+asyncpg://user:pass@host/db`  |
| `QDRANT_URL`           | Qdrant HTTP URL                                 | `http://localhost:6333`                   |
| `QDRANT_API_KEY`       | Optional Qdrant API key                         | —                                         |
| `REDIS_URL`            | Redis URL for Celery broker + backend           | `redis://localhost:6379/0`                |
| `OPENAI_API_KEY`       | OpenAI API key (required)                       | `sk-...`                                  |
| `OLLAMA_BASE_URL`      | Optional local LLM base URL                     | `http://localhost:11434`                  |
| `USE_LOCAL_LLM`        | Route chat to local LLM instead of OpenAI       | `false`                                   |
| `USE_LOCAL_EMBEDDINGS` | Route embeddings to local model                 | `false`                                   |
| `LANGFUSE_PUBLIC_KEY`  | Langfuse public key (optional)                  | —                                         |
| `LANGFUSE_SECRET_KEY`  | Langfuse secret key (optional)                  | —                                         |
| `LANGFUSE_HOST`        | Langfuse server URL                             | `http://localhost:3100`                   |
| `ALLOWED_ORIGINS`      | CORS origins, comma-separated                   | `http://localhost:3001,http://localhost:3000` |
| `ALLOWED_HOSTS`        | TrustedHost hosts, comma-separated              | `localhost,backend`                       |
| `STORAGE_PATH`         | Directory for uploaded files                    | `./storage`                               |

---

## API Reference

Base URL: `http://localhost:8000`

All ingest, chat, and document endpoints require the **`X-User-ID`** header to scope data per user.

### Health

**GET /health**
Returns `{"status": "ok", "service": "<APP_NAME>"}`.

---

### Ingest

**POST /api/v1/ingest/upload**

Upload a document to be ingested.

- **Headers**: `X-User-ID: <user-id>`
- **Body**: multipart/form-data with field `file` (PDF, DOCX, or TXT)
- **Response `202`**:
  ```json
  { "task_id": "<celery-task-id>", "message": "File uploaded and ingestion queued" }
  ```
- **Errors**: `400` if filename is missing or MIME type is unsupported; `500` on storage or task failure.

---

**GET /api/v1/ingest/status/{task_id}**

Poll ingestion progress.

- **Response `200`**:
  ```json
  {
    "status": "pending" | "processing" | "completed" | "failed" | "unknown",
    "step": "extracting_text" | "chunking" | "generating_embeddings" | "storing_vectors" | "completed" | null,
    "progress": 0,
    "error": null,
    "document_id": "<uuid>"
  }
  ```
  `document_id` is only populated when `status` is `"completed"`.

---

### Chat

**POST /api/v1/chat/stream**

Send a message and receive a streamed response.

- **Headers**: `X-User-ID: <user-id>`, `Content-Type: application/json`
- **Body**:
  ```json
  {
    "message": "What does section 3 say about fault tolerance?",
    "history": [
      { "role": "user", "content": "..." },
      { "role": "assistant", "content": "..." }
    ],
    "config": {
      "persona": "technical",
      "temperature": 0.7,
      "use_hybrid_search": true
    }
  }
  ```
- **Response `200`** — `text/event-stream`:
  ```
  data: {"content": "The section describes..."}

  data: {"content": " a leader-election protocol..."}

  event: end
  data: {}
  ```

---

### Documents

**GET /api/v1/documents**

- **Response `200`**: `{"documents": []}` *(list not yet implemented)*

---

**DELETE /api/v1/documents/{document_id}**

Delete a document and all its associated data.

- **Headers**: `X-User-ID: <user-id>`
- **Response `204`**: No content.
- Removes Qdrant vectors (filtered by `doc_id` + `user_id`), the file from disk, and the PostgreSQL record.
- **Errors**: `404` if the document does not exist or belongs to a different user.

---

## Document Ingestion Pipeline

1. **Upload** — client sends a file; backend validates MIME type, saves it under `STORAGE_PATH/<user_id>/<uuid>_<filename>`, and enqueues a Celery task, returning a `task_id`.
2. **Celery task** (`ingest_document_task`):
   - Extract text pages by MIME type (PyMuPDF → PDF, python-docx → DOCX, stdlib → TXT).
   - Chunk with `chunk_size=1500`, `chunk_overlap=200`.
   - Generate embeddings via OpenAI `text-embedding-3-small` (1536 dimensions).
   - Ensure Qdrant collection `documents` exists; upsert points with payload: `user_id`, `doc_id`, `filename`, `page_number`, `chunk_index`, `text` (the chunk content), `access_level`.
   - Create a `Document` record in PostgreSQL; update status to `completed` or `failed`.
3. **Status polling** — client calls `GET /api/v1/ingest/status/{task_id}` until `status` is `completed` (receives `document_id`) or `failed`.

> **Note**: The Celery task creates a fresh SQLAlchemy async engine (with `NullPool`) per database call to avoid cross-event-loop connection reuse errors when using `asyncio.run()` inside a synchronous Celery task.

---

## RAG Chat Flow

1. Client sends **POST /api/v1/chat/stream** with `message`, `history`, and `config`.
2. **ChatOrchestrator**:
   - Builds system prompt from `config.persona` (`technical` or `sarcastic`).
   - Embeds the user message via `EmbeddingService`.
   - Searches Qdrant with filter `user_id = <X-User-ID>`, limit 5; retrieves chunks including their `text` content.
   - Builds context string: `[Source: <filename>, page <n>]\n<chunk text>` per hit, joined by `---`.
   - Calls OpenAI Chat Completions (GPT-4o-mini) with system prompt + context block + message history + user message, `stream=True`.
3. Response is streamed as SSE; each chunk yields `data: {"content": "..."}`. Stream ends with `event: end`.

---

## Testing

### Unit tests

```bash
cd backend
pip install -r requirements-test.txt
pytest tests/ -m unit -v

# Single file
pytest tests/unit/test_chunking.py -v
```

No real database, Qdrant, or OpenAI required — all external services are mocked via pytest fixtures in `tests/conftest.py`.

### RAG evals (Ragas)

```bash
cd backend
pip install -r requirements-eval.txt
export OPENAI_API_KEY=sk-...

# With real Qdrant context
pytest tests/evals -m evals -v

# With mocked context (CI-safe, no Qdrant needed)
RAG_EVAL_USE_MOCK_CONTEXT=1 pytest tests/evals -m evals -v
```

Reference contexts live in `tests/evals/fixtures/ground_truth_rag.json`. The CI workflow (`.github/workflows/rag-evals.yml`) always uses `RAG_EVAL_USE_MOCK_CONTEXT=1` and requires the `OPENAI_API_KEY` secret.

---

## Observability

Langfuse is **optional**. Leave `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` empty to disable it entirely — the backend starts normally without them.

When enabled, the backend initializes a Langfuse client and traces selected handlers (e.g. `/health`) with `@observe()`. On shutdown, the client flushes any pending events.

When self-hosting via Docker Compose, Langfuse requires:
- A dedicated PostgreSQL database (`langfuse`)
- Clickhouse for event storage
- `LANGFUSE_ENCRYPTION_KEY` — must be a **64-character hex string** (32 bytes). Generate one with: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- `LANGFUSE_NEXTAUTH_SECRET` — any string, used for session signing

Access the Langfuse dashboard at **http://localhost:3100**.

---

## Project Structure

```
enterprise-rag-engine/
├── backend/
│   ├── app/
│   │   ├── api/v1/routers/
│   │   │   ├── ingest.py        # POST /ingest/upload, GET /ingest/status/{task_id}
│   │   │   ├── chat.py          # POST /chat/stream (SSE)
│   │   │   └── documents.py     # GET /documents, DELETE /documents/{id}
│   │   ├── core/
│   │   │   ├── security.py      # X-User-ID header validation
│   │   │   └── observability.py # Langfuse client setup
│   │   ├── db/
│   │   │   ├── models.py        # Document SQLAlchemy model
│   │   │   └── session.py       # Async engine, session factory, init_db
│   │   ├── models/schemas.py    # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── chat.py          # ChatOrchestrator (embed → search → complete)
│   │   │   ├── embeddings.py    # EmbeddingService (OpenAI text-embedding-3-small)
│   │   │   └── storage.py       # StorageService (save/read files)
│   │   ├── utils/
│   │   │   ├── chunking.py      # chunk_pages (size 1500, overlap 200)
│   │   │   ├── text_extraction.py  # PDF / DOCX / TXT extraction
│   │   │   └── mime_validator.py   # MIME type validation via libmagic
│   │   ├── workers/
│   │   │   ├── celery_app.py    # Celery app (broker=Redis, include=ingestion_tasks)
│   │   │   └── ingestion_tasks.py  # ingest_document_task
│   │   ├── config.py            # Settings (Pydantic Settings, .env)
│   │   ├── dependencies.py      # get_qdrant_client
│   │   └── main.py              # FastAPI app, lifespan, CORS, routes
│   ├── tests/
│   │   ├── api/                 # test_ingest, test_chat, test_documents
│   │   ├── unit/                # test_config, test_chunking, test_mime_validator, test_storage, test_security
│   │   ├── evals/               # Ragas evals + fixtures/ground_truth_rag.json
│   │   └── conftest.py          # Fixtures, TestClient, mocks
│   ├── requirements.txt
│   ├── requirements-test.txt
│   ├── requirements-eval.txt
│   ├── pytest.ini
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Main UI: upload, preview, chat, delete
│   │   └── layout.tsx
│   ├── Dockerfile
│   └── package.json
├── .github/workflows/
│   └── rag-evals.yml            # CI: RAG evals on PRs touching backend/**
├── docker-compose.yml
├── env.docker.example
├── env.backend.example
└── README.md
```
