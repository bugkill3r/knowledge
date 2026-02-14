"""Tag models"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Tag(Base):
    """Tag model for hierarchical tags"""
    __tablename__ = "tags"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Tag information
    name = Column(String, nullable=False, unique=True, index=True)
    parent_id = Column(String, ForeignKey("tags.id"), nullable=True)
    
    # Metadata
    description = Column(String, nullable=True)
    color = Column(String, nullable=True)  # Hex color for UI
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    children = relationship("Tag", backref="parent", remote_side=[id])
    documents = relationship("DocumentTag", back_populates="tag", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tag(id={self.id}, name={self.name})>"


class DocumentTag(Base):
    """Association table for documents and tags"""
    __tablename__ = "document_tags"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = Column(String, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Whether tag was auto-generated or manual
    auto_generated = Column(String, default="false")
    
    # Confidence score for auto-generated tags (0.0 to 1.0)
    confidence = Column(String, nullable=True)  # Storing as string for SQLite
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="tags")
    tag = relationship("Tag", back_populates="documents")
    
    def __repr__(self):
        return f"<DocumentTag(document_id={self.document_id}, tag_id={self.tag_id})>"

