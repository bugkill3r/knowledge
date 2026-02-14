# Understanding

One-page view of how the system works. Use for research before planning.

## Architecture

```
User → Frontend (Next.js, :3000) → Backend (FastAPI, :8000) → SQLite + ChromaDB
                                        ↓
                              Obsidian vault (filesystem)
```

- **Frontend:** NextAuth (Google), dashboard (import, documents, search, collections, code, graph, review). Calls backend with `Authorization: Bearer <accessToken>`.
- **Backend:** `app/main.py` mounts `api/v1`. Services: import (Google Docs + optional Sheets/PDF), document (vault paths from config), embedding (ChromaDB + sentence-transformers), AI (OpenAI/Anthropic/Azure).
- **Vault:** `OBSIDIAN_VAULT_PATH` + `VAULT_ROOT_FOLDER` → content root. Under that: `Docs/`, `Docs/Google Docs/`, `Docs/PRDs`, etc. Created by `ensure_vault_structure()`.

## Config hierarchy

1. **Env** – Required: `OBSIDIAN_VAULT_PATH`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SECRET_KEY`. Optional: `VAULT_ROOT_FOLDER`, `PROJECT_NAME`, `DOMAIN`, `CHROMA_COLLECTION_NAME`, `REVIEW_FOCUS_AREAS`, AI keys.
2. **Per-request** – API params (e.g. search limit, focus_areas) override defaults.
3. **Future:** Optional config file (Phase 5) for vault layout, RAG defaults, context profiles.

## Key flows

| Flow | Entry | Backend | Output |
|------|--------|---------|--------|
| Import doc | POST /api/v1/imports/google-docs | ImportService → GoogleDocsService, DocumentService, EmbeddingService | Job id; markdown in vault |
| Search | GET /api/v1/search?q= | EmbeddingService.search_similar, optional AI answer | Results + optional RAG answer |
| Stream answer | GET /api/v1/search/answer-stream?q= | Same retrieval; stream LLM response | SSE stream |

## Important files

| Area | Files |
|------|--------|
| Config | `backend/app/config.py` |
| Vault paths | `document_service._generate_vault_path`, `ensure_vault_structure` |
| RAG | `api/v1/search.py` (chunk count, system prompt from settings) |
| Embeddings | `embedding_service.py` (ChromaDB collection name from config) |
| Auth | `frontend/src/lib/auth.ts`; route `app/api/auth/[...nextauth]/route.ts` |

## Data

- **SQLite:** documents, embeddings (metadata), entities, tags, import_jobs, collections, code_repositories, document_reviews.
- **ChromaDB:** vectors for document chunks and code chunks; collection name from `CHROMA_COLLECTION_NAME`.
- **Vault:** Markdown files with YAML frontmatter; path = `VAULT_ROOT_FOLDER/Docs/...` or similar.
