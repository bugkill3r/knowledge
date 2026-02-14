"""Document Review model"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class ReviewStatus(enum.Enum):
    """Review job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewType(enum.Enum):
    """Type of review"""
    COMPREHENSIVE = "comprehensive"  # Full detailed review
    QUICK = "quick"  # High-level quick review
    TECHNICAL = "technical"  # Focus on technical aspects
    STRATEGIC = "strategic"  # Focus on strategic alignment


class DocumentReview(Base):
    """Document review tracking"""
    __tablename__ = "document_reviews"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Source and reviewed documents
    original_document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    reviewed_document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    
    # Review configuration
    review_type = Column(String, nullable=False, default=ReviewType.COMPREHENSIVE.value)
    focus_areas = Column(JSON, nullable=True)
    
    # Review status and streaming content
    status = Column(String, nullable=False, default=ReviewStatus.PENDING.value)
    streaming_content = Column(Text, nullable=True)  # Real-time streaming content
    total_comments = Column(Integer, default=0)
    comment_categories = Column(JSON, nullable=True)  # {"strategic": 5, "technical": 3, ...}
    
    # AI configuration
    ai_model = Column(String, nullable=True)  # "gpt-4", "claude-3-opus", etc.
    review_prompt = Column(Text, nullable=True)  # The actual prompt used
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # User tracking
    created_by = Column(String, nullable=True)
    
    # Additional metadata
    metadata_json = Column(JSON, nullable=True)
    
    # Relationships
    original_document = relationship("Document", foreign_keys=[original_document_id])
    reviewed_document = relationship("Document", foreign_keys=[reviewed_document_id])
    
    def __repr__(self):
        return f"<DocumentReview {self.id} - {self.status}>"

