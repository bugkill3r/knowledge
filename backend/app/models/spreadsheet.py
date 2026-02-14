"""
Spreadsheet data model
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class SpreadsheetData(Base):
    """Model for storing Google Sheets data and analysis"""
    
    __tablename__ = "spreadsheet_data"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    sheet_url = Column(String, nullable=False)
    sheet_id = Column(String, nullable=False)
    sheet_title = Column(String)
    csv_data = Column(Text)  # Raw CSV data
    markdown_table = Column(Text)  # Markdown formatted table
    ai_analysis = Column(JSON)  # AI-generated insights
    metadata_json = Column(JSON)  # Sheet metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    document = relationship("Document", back_populates="spreadsheets")

