"""Embedding model"""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Embedding(Base):
    """Embedding model for document chunks"""
    __tablename__ = "embeddings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Chunk information
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    
    # ChromaDB reference
    chroma_id = Column(String, nullable=True)  # ID in ChromaDB
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="embeddings")
    
    def __repr__(self):
        return f"<Embedding(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"

