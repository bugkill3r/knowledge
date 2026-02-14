"""Document model"""
from sqlalchemy import Column, String, Text, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class DocumentType(str, enum.Enum):
    """Document type enumeration"""
    PRD = "prd"
    TECH_SPEC = "tech-spec"
    KNOWLEDGE_TRANSFER = "kt"
    MEETING = "meeting"
    RUNBOOK = "runbook"
    DOC = "doc"
    DECISION = "decision"


class DocumentStatus(str, enum.Enum):
    """Document status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class DocumentSource(str, enum.Enum):
    """Document source enumeration"""
    GOOGLE_DOCS = "google-docs"
    MANUAL = "manual"
    IMPORTED = "imported"


class Document(Base):
    """Document model for storing imported and created documents"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Basic information
    title = Column(String, nullable=False, index=True)
    source_url = Column(String, nullable=True)
    source_type = Column(SQLEnum(DocumentSource), nullable=False)
    doc_type = Column(SQLEnum(DocumentType), nullable=True)
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.DRAFT)
    
    # Content
    content_md = Column(Text, nullable=False)
    content_html = Column(Text, nullable=True)
    
    # Vault integration
    vault_path = Column(String, nullable=False)  # Relative path in vault
    
    # Metadata
    metadata_json = Column(JSON, nullable=True)  # Additional metadata
    
    # AI-generated fields
    summary = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)  # List of keywords
    
    # Ownership
    author = Column(String, nullable=True)
    imported_by = Column(String, nullable=True)
    
    # Processing flags
    ai_processed = Column(String, default="false")  # Using String for SQLite compatibility
    embeddings_generated = Column(String, default="false")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_synced = Column(DateTime, nullable=True)
    
    # Relationships
    embeddings = relationship("Embedding", back_populates="document", cascade="all, delete-orphan")
    entities = relationship("DocumentEntity", back_populates="document", cascade="all, delete-orphan")
    tags = relationship("DocumentTag", back_populates="document", cascade="all, delete-orphan")
    spreadsheets = relationship("SpreadsheetData", back_populates="document", cascade="all, delete-orphan")
    collections = relationship(
        "Collection",
        secondary="collection_documents",
        back_populates="documents"
    )
    
    def __repr__(self):
        return f"<Document(id={self.id}, title={self.title})>"

