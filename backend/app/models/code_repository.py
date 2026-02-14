"""Code repository models"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Contributor(Base):
    """Model for code contributors (from Git commits)"""
    __tablename__ = "contributors"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    commits = relationship("Commit", back_populates="author")
    
    def __repr__(self):
        return f"<Contributor(name={self.name}, email={self.email})>"


class CodeRepository(Base):
    """Model for code repositories"""
    __tablename__ = "code_repositories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    local_path = Column(String, nullable=False, unique=True)
    git_url = Column(String, nullable=True)
    branch = Column(String, default='main')
    primary_language = Column(String, nullable=True)  # python, typescript, go
    
    # Statistics
    total_files = Column(Integer, default=0)
    total_functions = Column(Integer, default=0)
    total_classes = Column(Integer, default=0)
    lines_of_code = Column(Integer, default=0)
    total_commits = Column(Integer, default=0)
    
    # Sync metadata
    last_commit_hash = Column(String, nullable=True)
    last_synced = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    chunks = relationship("CodeChunk", back_populates="repository", cascade="all, delete-orphan")
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan")
    collections = relationship(
        "Collection",
        secondary="collection_repositories",
        back_populates="repositories"
    )
    
    def __repr__(self):
        return f"<CodeRepository(id={self.id}, name={self.name}, language={self.primary_language})>"


class Commit(Base):
    """Model for Git commits"""
    __tablename__ = "commits"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sha = Column(String, unique=True, index=True, nullable=False)
    message = Column(Text, nullable=False)
    authored_date = Column(DateTime, nullable=False)
    
    # Foreign keys
    repository_id = Column(String, ForeignKey("code_repositories.id"), nullable=False)
    author_id = Column(String, ForeignKey("contributors.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    repository = relationship("CodeRepository", back_populates="commits")
    author = relationship("Contributor", back_populates="commits")
    
    def __repr__(self):
        return f"<Commit(sha={self.sha[:8]}, repo={self.repository_id})>"


class CodeChunk(Base):
    """Model for code chunks (functions, classes, files)"""
    __tablename__ = "code_chunks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String, ForeignKey('code_repositories.id'), nullable=False, index=True)
    
    # File information
    file_path = Column(String, nullable=False)  # Relative to repo root
    language = Column(String, nullable=False)  # python, typescript, go, javascript
    
    # Chunk metadata
    chunk_type = Column(String, nullable=False)  # function, class, method, file
    chunk_name = Column(String, nullable=True, index=True)  # function/class name
    full_name = Column(String, nullable=True)  # e.g., "ClassName.method_name"
    
    # Content
    code_content = Column(Text, nullable=False)
    docstring = Column(Text, nullable=True)
    signature = Column(String, nullable=True)  # e.g., "def func(arg1: str) -> int"
    
    # Location
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    
    # Git metadata
    last_commit_hash = Column(String, nullable=True)
    last_modified = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    repository = relationship("CodeRepository", back_populates="chunks")
    
    def __repr__(self):
        return f"<CodeChunk(id={self.id}, name={self.chunk_name}, type={self.chunk_type}, lang={self.language})>"

