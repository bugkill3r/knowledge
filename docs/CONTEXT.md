# Knowledge System – context for humans and LLMs

**Purpose:** One-page orientation. Where to look, what’s fixed, what’s config. Kept short so it stays in the “smart zone” ([Context is all you need](https://www.mishras.xyz/posts/context-is-all-you-need)).

## What this repo is

- **Import** Google Docs (and optionally Sheets, PDF, code) into an Obsidian vault.
- **Store** metadata in SQLite, embeddings in ChromaDB.
- **Search** (semantic) and **chat** (RAG) over the vault.
- **Generic:** No org names in code. One deployment = one vault root + one project name (env).

## Where to look

| Need | File / dir |
|------|------------|
| Run both servers | `./run.sh` (kills 8000/3000, starts backend + frontend) |
| Backend config | `backend/app/config.py`; `backend/.env` |
| Frontend env | `frontend/.env.local` |
| Vault layout | `config.ensure_vault_structure()`; env `VAULT_ROOT_FOLDER`, `OBSIDIAN_VAULT_PATH` |
| API surface | `backend/app/api/v1/`; OpenAPI at `/api/docs` |
| System context for LLMs | `backend/context/SYSTEM_CONTEXT.md` |
| What we did and why | `docs/PROGRESS.md`, `docs/RESEARCH.md` |
| How it works | `docs/UNDERSTANDING.md` |
| Full migration plan | `GENERIC_KNOWLEDGE_SYSTEM_PLAN.md` |

## Conventions

- **Config over code** for identity, vault paths, prompts. Env wins; optional config file later.
- **No slop:** No marketing copy, no emoji in code/UI strings, no “AI-powered” badges. Direct language.
- **Extension:** New doc source = new service + route. New AI provider = new client behind `AI_PROVIDER`. No plugin SDK.

## If you’re doing research → plan → implement

1. **Research:** Read `UNDERSTANDING.md` + the relevant service/API. Compress to “what exists, where, how it’s wired.”
2. **Plan:** Explicit steps, file:line where useful, “what we’re NOT doing.” Review plan before coding.
3. **Implement:** Execute plan; keep context small. After a phase, optionally compress progress into `PROGRESS.md`.
