"""Collection model for organizing documents and repositories"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base

# Association tables for many-to-many relationships
collection_documents = Table(
    'collection_documents',
    Base.metadata,
    Column('collection_id', String, ForeignKey('collections.id', ondelete='CASCADE')),
    Column('document_id', String, ForeignKey('documents.id', ondelete='CASCADE'))
)

collection_repositories = Table(
    'collection_repositories',
    Base.metadata,
    Column('collection_id', String, ForeignKey('collections.id', ondelete='CASCADE')),
    Column('repository_id', String, ForeignKey('code_repositories.id', ondelete='CASCADE'))
)


class Collection(Base):
    """Model for project collections/workspaces"""
    __tablename__ = "collections"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    color = Column(String, default='#3B82F6')  # Hex color for UI
    icon = Column(String, default='📁')  # Emoji or icon name
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    documents = relationship(
        "Document",
        secondary=collection_documents,
        back_populates="collections"
    )
    repositories = relationship(
        "CodeRepository",
        secondary=collection_repositories,
        back_populates="collections"
    )
    
    def __repr__(self):
        return f"<Collection(id={self.id}, name={self.name})>"

