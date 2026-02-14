"""Import job model"""
from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum, Text
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class ImportStatus(str, enum.Enum):
    """Import job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some docs succeeded, some failed


class ImportJob(Base):
    """Import job model for tracking Google Docs imports"""
    __tablename__ = "import_jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Job information
    source_url = Column(String, nullable=False)
    status = Column(SQLEnum(ImportStatus), default=ImportStatus.PENDING, nullable=False)
    
    # Progress tracking
    total_docs = Column(Integer, default=0)
    processed_docs = Column(Integer, default=0)
    failed_docs = Column(Integer, default=0)
    
    # Results
    imported_doc_ids = Column(Text, nullable=True)  # JSON list of document IDs
    error_message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)  # JSON with detailed errors
    
    # User
    user_email = Column(String, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<ImportJob(id={self.id}, status={self.status}, progress={self.processed_docs}/{self.total_docs})>"
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage"""
        if self.total_docs == 0:
            return 0.0
        return (self.processed_docs / self.total_docs) * 100

