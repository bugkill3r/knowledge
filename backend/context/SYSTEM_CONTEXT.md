# Knowledge System – context for LLMs

Generic knowledge management: import docs (Google Docs, etc.) into an Obsidian vault, search with vector embeddings, chat over content with RAG.

## Purpose

- Ingest Google Docs (and optionally Sheets, PDFs, code repos) into a configurable Obsidian vault path.
- Store metadata in SQLite, embeddings in ChromaDB.
- Provide search (semantic), chat (RAG), collections, document review, and optional code/graph features.

## Architecture

- **Backend (FastAPI):** REST API for imports, documents, search, collections, code, graph, review. Services: import, document (vault paths from config), embedding (ChromaDB), AI (OpenAI/Anthropic/Azure).
- **Frontend (Next.js):** Google OAuth, dashboard (import, documents, search, bulk import, code repos, collections, graph, document review).
- **Config:** All paths and naming from env: `OBSIDIAN_VAULT_PATH`, `VAULT_ROOT_FOLDER`, `PROJECT_NAME`, `DOMAIN`, `CHROMA_COLLECTION_NAME`, etc. No hardcoded org or product names.

## Data flow (import)

User pastes Google Docs URL → frontend sends to backend with OAuth token → backend fetches doc, optional linked docs → HTML to markdown → metadata + optional AI tags/summary → save to SQLite and write markdown to vault under `VAULT_ROOT_FOLDER/Docs/...` → return job id; frontend polls status.

## Vault layout (default)

Under `OBSIDIAN_VAULT_PATH/VAULT_ROOT_FOLDER/`: `Docs/`, `Docs/Google Docs/`, `Docs/PRDs/`, `Docs/Tech Specs/`, `Docs/Runbooks/`, `Strategy/`, `Strategy/Knowledge Transfer/`, `Strategy/Decision Log/`. Overridable via code/config.

## Key APIs

- `POST /api/v1/imports/google-docs` – import from URL (body: url, recursive, user_email).
- `GET /api/v1/imports/jobs/{id}` – job status.
- `GET /api/v1/documents/` – list documents.
- `GET /api/v1/search?q=...` – semantic search, optional RAG answer.
- `GET /api/v1/search/answer-stream?q=...` – streaming RAG answer.

## Extension points

- New document sources: add a service and route; same document model and vault writer.
- New AI provider: implement same interface in `ai_service`, switch via `AI_PROVIDER` env.
- Vault folder structure: controlled by `ensure_vault_structure()` and config; no product-specific folders in code.

Last updated: generic version for use with any vault and project name.
