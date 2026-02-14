"""Entity models"""
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class EntityType(str, enum.Enum):
    """Entity type enumeration"""
    PERSON = "person"
    SYSTEM = "system"
    PRODUCT = "product"
    TEAM = "team"
    TECHNOLOGY = "technology"


class Entity(Base):
    """Entity model for extracted entities"""
    __tablename__ = "entities"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Entity information
    name = Column(String, nullable=False, index=True)
    entity_type = Column(SQLEnum(EntityType), nullable=False)
    
    # Metadata
    metadata_json = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    documents = relationship("DocumentEntity", back_populates="entity", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Entity(id={self.id}, name={self.name}, type={self.entity_type})>"


class DocumentEntity(Base):
    """Association table for documents and entities with relevance scores"""
    __tablename__ = "document_entities"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_id = Column(String, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Relevance score (0.0 to 1.0)
    relevance_score = Column(Float, default=0.5)
    
    # Context where entity appears
    context = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="entities")
    entity = relationship("Entity", back_populates="documents")
    
    def __repr__(self):
        return f"<DocumentEntity(document_id={self.document_id}, entity_id={self.entity_id}, score={self.relevance_score})>"

