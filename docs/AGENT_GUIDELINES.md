# Agent guidelines

Guidelines for AI agents and humans working on this repo. Follow the loop below and the code rules so work stays consistent and verifiable.

---

## 1. Agent loop (close the loop)

For non-trivial work, follow this sequence and verify before finishing:

1. **Research** – Read relevant code and docs (`docs/UNDERSTANDING.md`, `docs/CONTEXT.md`, service/API code). Understand current behavior and config.
2. **Plan** – Write concrete steps (file/area, what to change). State what we are *not* doing. Get alignment if needed.
3. **Implement** – Apply changes following the **Code guidelines** below.
4. **Verify** – Confirm the change conforms to these guidelines (no new violations). Run tests or smoke-check if applicable.

Agents should start from research/plan and use this doc as the standard for implementation and verification.

---

## 2. Code guidelines

### Backend (Python)

- **Logging** – Use `logging` (e.g. `logger.info`, `logger.error`, `logger.debug`). Do not use `print()` for normal or error output in app code. CLI scripts (e.g. `validate_config.py`) may use `print`.
- **Debug / dev-only behavior** – No writing to `/tmp` or filesystem for debugging in normal code paths. No `print("[DEBUG] ...")`. Use `logger.debug()` so level can be controlled by `LOG_LEVEL`.
- **Comments** – Prefer code that is clear without comments. When commenting, explain *why* or non-obvious behavior. Remove comments that only restate the next line.
- **Config** – Use `app.config.settings`; no hardcoded paths, org names, or environment-specific values in code.
- **Errors** – Prefer explicit handling and `logger.error()`; avoid silent catches.

### Frontend (TypeScript/React)

- **Logging** – No `console.log` in production paths. Remove or guard with `process.env.NODE_ENV === 'development'` if needed for local debugging.
- **No `debugger`** statements in committed code.

### General

- **Docstrings** – Keep on public APIs and service entrypoints. Remove or shorten when they only repeat the function name.
- **TODOs** – Prefer resolving or turning into a short comment (e.g. “from auth when available”). Avoid bare `# TODO` with no context.

---

## 3. Verification checklist

Before considering a task done, confirm:

- [ ] No new `print()` in backend app code (only `logger`).
- [ ] No new `console.log` or `debugger` in frontend (or dev-only guarded).
- [ ] No new hardcoded paths, org names, or secrets.
- [ ] Comments add value (why / non-obvious); redundant comments removed.
- [ ] Research/plan was followed and changes match the plan.

---

## 4. Where to look

| Need | Location |
|------|----------|
| Orientation | `docs/CONTEXT.md` |
| Architecture, config, flows | `docs/UNDERSTANDING.md` |
| Migration / generic vs checkout | `GENERIC_KNOWLEDGE_SYSTEM_PLAN.md` (local), `docs/DIFF_FROM_CHECKOUT_KNOWLEDGE.md` |
| Backend config | `backend/app/config.py`, `backend/.env.example` |
| API surface | `backend/app/api/v1/`, `/api/docs` |
