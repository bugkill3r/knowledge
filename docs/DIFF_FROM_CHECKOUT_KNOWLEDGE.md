# Code diff: Checkout Knowledge System → this repo

**Source dir:** `/Users/saurabh/Dev/misc/rzp-personal/checkout-knowledge-system`  
**Target:** this repo (`knowledge`)

Diffs below are from `diff -rq` and `diff -u` run between those two trees (excluding runtime artifacts like `.env`, `__pycache__`, `node_modules`, `.next`, `venv`, `data`, `knowledge.db` from the inventory).

---

## File inventory

### Backend – files that differ
| Source (checkout) | Target (knowledge) |
|-------------------|--------------------|
| `backend/app/config.py` | ✓ differs |
| `backend/app/main.py` | ✓ differs |
| `backend/app/__init__.py` | ✓ differs |
| `backend/app/api/v1/__init__.py` | ✓ differs |
| `backend/app/api/v1/imports.py` | ✓ differs |
| `backend/app/api/v1/review.py` | ✓ differs |
| `backend/app/api/v1/search.py` | ✓ differs |
| `backend/app/models/document_review.py` | ✓ differs |
| `backend/app/models/tag.py` | ✓ differs |
| `backend/app/services/ai_review_service.py` | ✓ differs |
| `backend/app/services/ai_service.py` | ✓ differs |
| `backend/app/services/document_service.py` | ✓ differs |
| `backend/app/services/embedding_service.py` | ✓ differs |
| `backend/app/services/import_service.py` | ✓ differs |
| `backend/app/services/pdf_service.py` | ✓ differs |
| `backend/context/SYSTEM_CONTEXT.md` | ✓ differs |
| `backend/.env.example` | ✓ differs |
| `backend/requirements.txt` | ✓ differs |
| `backend/validate_config.py` | ✓ differs |

**Only in knowledge:** `backend/app/api/v1/config.py`, `.env`, `data/`, `knowledge.db`, `venv/`, `__pycache__/`  
**Only in source:** `backend/RTO_Prediction_Model_Strategy_REVIEWED.md`

### Frontend – files that differ
| Source (checkout) | Target (knowledge) |
|-------------------|--------------------|
| `frontend/src/app/layout.tsx` | ✓ differs |
| `frontend/src/app/page.tsx` | ✓ differs |
| `frontend/src/app/dashboard/page.tsx` | ✓ differs |
| `frontend/src/app/providers.tsx` | ✓ differs |
| `frontend/src/app/token/page.tsx` | ✓ differs |
| `frontend/src/app/api/auth/[...nextauth]/route.ts` | ✓ differs |
| `frontend/src/components/AddRepositoryModal.tsx` | ✓ differs |
| `frontend/src/components/CodeNetworkGraph.tsx` | ✓ differs |
| `frontend/src/components/Collections.tsx` | ✓ differs |
| `frontend/src/components/DocumentList.tsx` | ✓ differs |
| `frontend/src/components/DocumentReview.tsx` | ✓ differs |
| `frontend/src/components/Search.tsx` | ✓ differs |
| `frontend/src/components/StreamingReview.tsx` | ✓ differs |
| `frontend/.env.example` | ✓ differs |
| `frontend/package.json` | ✓ differs |
| `frontend/package-lock.json` | ✓ differs |
| `frontend/tsconfig.json` | ✓ differs |

**Only in knowledge:** `frontend/src/app/onboarding/`, `frontend/src/lib/`, `.env.local`, `.nvmrc`, `node_modules/`, `.next/`

---

## Actual unified diffs (key files)

### `backend/app/config.py`
- DB: `checkout_knowledge.db` → `knowledge.db`
- Removed: `CHECKOUT_VAULT_PATH = "01 - Checkout"`; added: `VAULT_ROOT_FOLDER`, `OBSIDIAN_VAULT_PATH` optional (empty = no Obsidian), `DOMAIN`, `CHROMA_COLLECTION_NAME`, `REVIEW_FOCUS_AREAS`, `PDF2MD_PATH`
- Removed: `vault_checkout_path`; added: `obsidian_enabled`, `obsidian_vault_name`, `vault_content_root`
- `docs_path`: `vault_checkout_path / "05 - Docs"` → `vault_content_root / "Docs"`
- `ensure_vault_structure()`: Checkout tree (`01 - Team`, `02 - OKRs`, `06 - Products/01 - COD`, etc.) → generic tree (`Docs`, `Strategy`, etc.); no-op when Obsidian disabled
- `PROJECT_NAME`: `"Checkout Knowledge System"` → `"Knowledge System"`

### `backend/app/services/document_service.py`
- `save_to_vault()`: returns `Optional[Path]`, no-op when `not settings.obsidian_enabled`; path uses `settings.OBSIDIAN_VAULT_PATH or ""`
- `frontmatter['domain']`: `'checkout'` → `settings.DOMAIN`
- `_generate_vault_path()`: all `settings.CHECKOUT_VAULT_PATH + "/05 - Docs/..."` etc. → `prefix + "Docs/Google Docs"`, `prefix + "Docs/PRDs"`, …, `prefix + "Strategy/Knowledge Transfer"` (prefix = `VAULT_ROOT_FOLDER + "/"` or `""`)
- Delete from vault: guarded by `settings.obsidian_enabled`

### `backend/app/services/embedding_service.py`
- Collection: `name="checkout_knowledge"`, `metadata={"description": "Checkout team knowledge base embeddings"}` → `name=settings.CHROMA_COLLECTION_NAME`, `metadata={"description": "Knowledge base embeddings"}`

### `backend/app/services/ai_service.py`
- Tagging prompt: checkout-specific (“checkout/payments team”, “checkout/cod”, “product/rto”) → single line with `Domain: {settings.DOMAIN}`

### `backend/app/services/pdf_service.py`
- `__init__`: hardcoded path `/Users/mishra.saurabh/Dev/personal/ai/ideas/pdf2md_tool/pdf2md` → optional `pdf2md_path`, from `settings.PDF2MD_PATH`
- `copy_images_to_vault`: path `vault_path + "01 - Checkout/05 - Docs/Google Docs/..."` → `settings.vault_content_root / "Docs" / "Google Docs" / "images" / safe_title`; early return when `not settings.obsidian_enabled`
- `get_pdf_service()`: uses `settings.PDF2MD_PATH`

### `backend/app/api/v1/review.py`
- Example `focus_areas`: `["cod", "rto", "checkout"]` → `["architecture", "technical"]`
- Save-review endpoint: vault base `~/Documents/rzpobs` → `settings.OBSIDIAN_VAULT_PATH`; when `not settings.obsidian_enabled` return success with no vault path; Obsidian URI uses `settings.obsidian_vault_name`

### `frontend/src/app/layout.tsx`
- Removed: `Inter` font
- Title: `'Checkout Knowledge System'` → `process.env.NEXT_PUBLIC_APP_NAME || 'Knowledge System'`
- Description: `'Intelligent knowledge management for Checkout team'` → `'Import docs, store in Obsidian, search and chat.'`
- Added: custom icon (inline SVG)
- Body: `className={inter.className}` → `className="font-sans antialiased"`

---

## 1. Backend config (`backend/app/config.py`)

**Checkout (before):**
```python
DATABASE_URL = "sqlite:///./checkout_knowledge.db"
CHECKOUT_VAULT_PATH = "01 - Checkout"
# vault_checkout_path, docs_path, google_docs_path derived from vault + CHECKOUT_VAULT_PATH
PROJECT_NAME = "Checkout Knowledge System"
```

**This repo (after):**
```python
# config.py (current)
DATABASE_URL: str = "sqlite:///./knowledge.db"
OBSIDIAN_VAULT_PATH: Optional[str] = ""   # Empty = no Obsidian
VAULT_ROOT_FOLDER: str = "Knowledge"
# docs_path, google_docs_path derived from vault_content_root
PROJECT_NAME: str = "Knowledge System"

@property
def vault_content_root(self) -> Path:
    if not self.obsidian_enabled:
        return Path()
    root = Path(self.OBSIDIAN_VAULT_PATH or "")
    if self.VAULT_ROOT_FOLDER:
        return root / self.VAULT_ROOT_FOLDER
    return root
```

---

## 2. Vault folder structure

**Checkout (before):** Hardcoded tree, e.g. `01 - Team`, `02 - OKRs`, `05 - Docs`, `06 - Products/01 - COD`, etc.

**This repo (after):** Single root + fixed generic tree under `vault_content_root`:
```python
# config.py – ensure_vault_structure()
paths = [
    self.vault_content_root,
    self.docs_path,
    self.google_docs_path,
    self.docs_path / "PRDs",
    self.docs_path / "Tech Specs",
    self.docs_path / "Runbooks",
    self.vault_content_root / "Strategy",
    self.vault_content_root / "Strategy" / "Knowledge Transfer",
    self.vault_content_root / "Strategy" / "Decision Log",
]
```

No `01 - Checkout` or product-specific paths.

---

## 3. Document service – frontmatter (`backend/app/services/document_service.py`)

**Checkout (before):**
```python
frontmatter['domain'] = 'checkout'
```

**This repo (after):**
```python
frontmatter['domain'] = settings.DOMAIN   # DOMAIN: str = "general" in config
```

---

## 4. Embedding service – Chroma collection (`backend/app/services/embedding_service.py`)

**Checkout (before):**
```python
name="checkout_knowledge"
```

**This repo (after):**
```python
name=settings.CHROMA_COLLECTION_NAME   # CHROMA_COLLECTION_NAME: str = "knowledge"
```

---

## 5. AI service – tagging prompt (`backend/app/services/ai_service.py`)

**Checkout (before):** Prompts used org-specific examples like “checkout/payments team”, “checkout/cod”, “product/rto”.

**This repo (after):**
```python
"content": f"""You are a document tagging assistant. Suggest 3-7 tags as category/subcategory. Domain: {settings.DOMAIN}. Return ONLY a comma-separated list of tags."""
```

---

## 6. PDF service – vault path (`backend/app/services/pdf_service.py`)

**Checkout (before):** Paths built with `"01 - Checkout"` (or similar hardcoded vault segment).

**This repo (after):**
```python
vault_images_dir = str(settings.vault_content_root / "Docs" / "Google Docs" / "images" / safe_title)
```

---

## 7. Review API – default focus areas (`backend/app/api/v1/review.py`)

**Checkout (before):**
```python
focus_areas: ["cod", "rto", "checkout"]   # default
```

**This repo (after):**
```python
focus_areas: Optional[List[str]] = None
# Example in schema: ["architecture", "technical"]
# ai_review_service: focus_areas or ["architecture", "technical"]
```

---

## 8. AI review service – default focus areas (`backend/app/services/ai_review_service.py`)

**Checkout (before):** Defaults and examples tied to “cod”, “rto”, “checkout”.

**This repo (after):**
```python
focus_areas=focus_areas or ["architecture", "technical"],
```

---

## 9. Frontend – layout title (`frontend/src/app/layout.tsx`)

**Checkout (before):**
```tsx
title: "Checkout Knowledge System"
description: "…" // org-specific
```

**This repo (after):**
```tsx
const appName = process.env.NEXT_PUBLIC_APP_NAME || 'Knowledge System'
export const metadata: Metadata = {
  title: appName,
  description: 'Import docs, store in Obsidian, search and chat.',
  …
}
```

---

## 10. Frontend – dashboard and pages

**Checkout (before):** “Checkout Knowledge” and similar copy hardcoded in `app/page.tsx`, `app/dashboard/page.tsx`, etc.

**This repo (after):**
```tsx
// app/page.tsx, dashboard/page.tsx, onboarding/page.tsx
process.env.NEXT_PUBLIC_APP_NAME || 'Knowledge System'
```

---

## 11. Frontend – placeholders (Collections, AddRepositoryModal)

**Checkout (before):** “e.g., Checkout Project”, “e.g., checkout-api”.

**This repo (after):** Generic placeholders (e.g. “Project Alpha”, “my-repo”) or from config; no “Checkout” in UI strings.

---

## Summary table

| Area              | Checkout (before)                    | This repo (after)                          |
|-------------------|--------------------------------------|--------------------------------------------|
| DB file           | `checkout_knowledge.db`              | `knowledge.db` (env)                       |
| Vault root        | `CHECKOUT_VAULT_PATH = "01 - Checkout"` | `OBSIDIAN_VAULT_PATH` + `VAULT_ROOT_FOLDER` |
| Chroma collection | `checkout_knowledge`                 | `settings.CHROMA_COLLECTION_NAME`           |
| Frontmatter domain| `'checkout'`                        | `settings.DOMAIN` (default `"general"`)    |
| Focus areas       | `["cod", "rto", "checkout"]`         | `None` or `["architecture", "technical"]`  |
| App name          | “Checkout Knowledge System”         | `NEXT_PUBLIC_APP_NAME` / “Knowledge System” |

To get a real `git diff` you’d need the Checkout Knowledge System repo (or a backup) and run e.g. `diff -r checkout-repo/ backend/` and same for `frontend/`.
