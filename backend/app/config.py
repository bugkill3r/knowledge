"""Application configuration"""
from pydantic_settings import BaseSettings
from typing import Optional, Literal
from pathlib import Path


class Settings(BaseSettings):
    """Settings from environment. No org-specific defaults."""

    DATABASE_URL: str = "sqlite:///./knowledge.db"

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_KEY: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-12-01-preview"
    AZURE_OPENAI_MODEL: str = "gpt-4"

    GEMINI_API_KEY: Optional[str] = None

    AI_PROVIDER: Literal["openai", "anthropic", "azure"] = "azure"
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    OBSIDIAN_VAULT_PATH: Optional[str] = ""  # Empty = no Obsidian; RAG/search still work
    OBSIDIAN_VAULT_NAME: Optional[str] = None  # For obsidian:// URI; default: last path segment
    VAULT_ROOT_FOLDER: str = "Knowledge"

    DOMAIN: str = "general"
    CHROMA_COLLECTION_NAME: str = "knowledge"
    REVIEW_FOCUS_AREAS: Optional[str] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        path_val = (self.OBSIDIAN_VAULT_PATH or "").strip()
        if path_val:
            vault_path = Path(path_val)
            if not vault_path.is_absolute():
                raise ValueError(
                    "OBSIDIAN_VAULT_PATH must be absolute when set. "
                    f"Got: {self.OBSIDIAN_VAULT_PATH}"
                )
            if not vault_path.exists():
                vault_path.mkdir(parents=True, exist_ok=True)

    @property
    def obsidian_enabled(self) -> bool:
        """True if vault sync is configured (documents written to Obsidian)."""
        return bool((self.OBSIDIAN_VAULT_PATH or "").strip())

    CHROMA_DB_PATH: str = "./data/chromadb"
    # Optional: path to pdf2md CLI (https://github.com/bugkill3r/pdf2md) for PDF image extraction
    PDF2MD_PATH: Optional[str] = None
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    FRONTEND_URL: str = "http://localhost:3000"
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Knowledge System"
    VERSION: str = "1.0.0"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def async_database_url(self) -> str:
        if self.is_sqlite:
            return self.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
        return self.DATABASE_URL

    @property
    def obsidian_vault_name(self) -> str:
        """Vault name for obsidian:// URIs (env or last segment of path)."""
        if not self.obsidian_enabled:
            return "vault"
        if self.OBSIDIAN_VAULT_NAME:
            return self.OBSIDIAN_VAULT_NAME
        return Path(self.OBSIDIAN_VAULT_PATH or "").name or "vault"

    @property
    def vault_content_root(self) -> Path:
        """Root folder inside the vault for this instance. Only valid when obsidian_enabled."""
        if not self.obsidian_enabled:
            return Path()
        root = Path(self.OBSIDIAN_VAULT_PATH or "")
        if self.VAULT_ROOT_FOLDER:
            return root / self.VAULT_ROOT_FOLDER
        return root

    @property
    def docs_path(self) -> Path:
        return self.vault_content_root / "Docs"

    @property
    def google_docs_path(self) -> Path:
        return self.docs_path / "Google Docs"

    def ensure_vault_structure(self):
        """Create vault folder structure. No-op when obsidian_enabled is False."""
        if not self.obsidian_enabled:
            return
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
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
