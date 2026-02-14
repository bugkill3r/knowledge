"""Public config endpoint for frontend (onboarding, feature flags)."""
from fastapi import APIRouter
from app.config import settings

router = APIRouter()


@router.get("/config")
def get_config():
    """Return public config: Obsidian enabled, project name. No auth required."""
    return {
        "project_name": settings.PROJECT_NAME,
        "obsidian_enabled": settings.obsidian_enabled,
    }
