"""Document service for managing documents and saving to vault"""
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import yaml
import json
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentType, DocumentSource, DocumentStatus
from app.models.import_job import ImportJob, ImportStatus
from app.config import settings


class DocumentService:
    """Service for managing documents and Obsidian vault integration"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_document(
        self,
        title: str,
        content_md: str,
        source_url: Optional[str] = None,
        source_type: DocumentSource = DocumentSource.MANUAL,
        doc_type: Optional[DocumentType] = None,
        metadata: Optional[Dict] = None,
        author: Optional[str] = None,
        imported_by: Optional[str] = None,
    ) -> Document:
        """Create a new document in database"""
        
        # Generate vault path
        vault_path = self._generate_vault_path(title, doc_type, source_type)
        
        document = Document(
            title=title,
            content_md=content_md,
            source_url=source_url,
            source_type=source_type,
            doc_type=doc_type or DocumentType.DOC,
            status=DocumentStatus.ACTIVE,
            vault_path=vault_path,
            metadata_json=metadata,
            author=author,
            imported_by=imported_by,
        )
        
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        
        return document
    
    def save_to_vault(
        self,
        document: Document,
        additional_metadata: Optional[Dict] = None
    ) -> Optional[Path]:
        """Save document to Obsidian vault with frontmatter. No-op when Obsidian is disabled."""
        if not settings.obsidian_enabled:
            return None
        # Ensure vault structure exists
        settings.ensure_vault_structure()
        # Build full path
        full_path = Path(settings.effective_obsidian_vault_path or "") / document.vault_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build frontmatter
        frontmatter = self._build_frontmatter(document, additional_metadata)
        
        # Build complete content
        content = f"---\n{yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)}---\n\n{document.content_md}"
        
        # Write to file
        full_path.write_text(content, encoding='utf-8')
        
        # Update document sync time
        document.last_synced = datetime.utcnow()
        self.db.commit()
        
        return full_path
    
    def _build_frontmatter(
        self,
        document: Document,
        additional_metadata: Optional[Dict] = None
    ) -> Dict:
        """Build frontmatter metadata for Obsidian"""
        
        frontmatter = {
            'title': document.title,
            'created': document.created_at.strftime('%Y-%m-%d'),
            'updated': document.updated_at.strftime('%Y-%m-%d'),
            'status': document.status.value,
            'type': document.doc_type.value if document.doc_type else 'doc',
        }
        
        # Add source information
        if document.source_url:
            frontmatter['doc_source'] = document.source_type.value
            frontmatter['source_url'] = document.source_url
            frontmatter['imported_date'] = document.created_at.strftime('%Y-%m-%d')
        
        if document.imported_by:
            frontmatter['imported_by'] = document.imported_by
        
        # Add author
        if document.author:
            frontmatter['author'] = document.author
        
        # Add AI-generated fields
        if document.summary:
            frontmatter['summary'] = document.summary
        
        if document.keywords:
            frontmatter['keywords'] = document.keywords
        
        # Add tags (placeholder - will be populated by AI service)
        frontmatter['tags'] = ['imported', 'google-docs'] if document.source_type == DocumentSource.GOOGLE_DOCS else ['manual']
        
        frontmatter['domain'] = settings.DOMAIN
        
        # Add processing flags
        frontmatter['ai_processed'] = document.ai_processed == 'true'
        frontmatter['embeddings_generated'] = document.embeddings_generated == 'true'
        
        # Merge additional metadata
        if additional_metadata:
            frontmatter.update(additional_metadata)
        
        # Add metadata from JSON field
        if document.metadata_json:
            frontmatter.update(document.metadata_json)
        
        return frontmatter
    
    def _generate_vault_path(
        self,
        title: str,
        doc_type: Optional[DocumentType],
        source_type: DocumentSource
    ) -> str:
        """Generate vault path based on document type and source"""
        
        # Sanitize title for filename
        filename = self._sanitize_filename(title) + '.md'
        
        prefix = (settings.VAULT_ROOT_FOLDER + "/") if settings.VAULT_ROOT_FOLDER else ""
        if source_type == DocumentSource.GOOGLE_DOCS:
            base_folder = prefix + "Docs/Google Docs"
        elif doc_type == DocumentType.PRD:
            base_folder = prefix + "Docs/PRDs"
        elif doc_type == DocumentType.TECH_SPEC:
            base_folder = prefix + "Docs/Tech Specs"
        elif doc_type == DocumentType.RUNBOOK:
            base_folder = prefix + "Docs/Runbooks"
        elif doc_type == DocumentType.KNOWLEDGE_TRANSFER:
            base_folder = prefix + "Strategy/Knowledge Transfer"
        elif doc_type == DocumentType.DECISION:
            base_folder = prefix + "Strategy/Decision Log"
        else:
            base_folder = prefix + "Docs"
        return f"{base_folder}/{filename}"
    
    def _sanitize_filename(self, title: str) -> str:
        """Sanitize title for use as filename"""
        # Replace invalid characters
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        sanitized = title
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Limit length
        max_length = 200
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip()
    
    def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        """Get document by ID"""
        return self.db.query(Document).filter(Document.id == doc_id).first()
    
    def get_document_by_source_url(self, source_url: str) -> Optional[Document]:
        """Get document by source URL"""
        return self.db.query(Document).filter(Document.source_url == source_url).first()
    
    def list_documents(self, limit: int = 100, offset: int = 0) -> List[Document]:
        """List all documents"""
        return self.db.query(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset).all()
    
    def update_document(self, doc_id: str, **kwargs) -> Optional[Document]:
        """Update document fields"""
        document = self.get_document_by_id(doc_id)
        if not document:
            return None
        
        for key, value in kwargs.items():
            if hasattr(document, key):
                setattr(document, key, value)
        
        document.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(document)
        
        return document
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete document from database and vault"""
        document = self.get_document_by_id(doc_id)
        if not document:
            return False
        
        # Delete from vault (only when Obsidian is enabled)
        if settings.obsidian_enabled and settings.effective_obsidian_vault_path:
            vault_file = Path(settings.effective_obsidian_vault_path) / document.vault_path
            if vault_file.exists():
                vault_file.unlink()
        
        # Delete from database
        self.db.delete(document)
        self.db.commit()
        
        return True

