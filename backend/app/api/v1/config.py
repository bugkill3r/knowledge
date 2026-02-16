"""Public config endpoint for frontend (onboarding, feature flags)."""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import settings, write_vault_path

router = APIRouter()


class VaultPathUpdate(BaseModel):
    path: str


@router.get("/config")
def get_config():
    """Return public config: Obsidian enabled, project name, vault path. No auth required."""
    return {
        "project_name": settings.PROJECT_NAME,
        "obsidian_enabled": settings.obsidian_enabled,
        "obsidian_vault_path": settings.effective_obsidian_vault_path or None,
    }


@router.put("/config/vault-path")
def update_vault_path(body: VaultPathUpdate):
    """Set vault path (self-serve). Path must be absolute. No auth required."""
    path = (body.path or "").strip()
    if not path:
        raise HTTPException(400, "Vault path cannot be empty")
    p = Path(path)
    if not p.is_absolute():
        raise HTTPException(400, "Vault path must be absolute")
    write_vault_path(path)
    return {"ok": True, "obsidian_vault_path": path}
