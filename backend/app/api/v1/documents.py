"""Document API endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.services.document_service import DocumentService

router = APIRouter()


class DocumentResponse(BaseModel):
    """Response model for document"""
    id: str
    title: str
    source_url: Optional[str]
    source_type: str
    doc_type: str
    status: str
    vault_path: str
    content_md: Optional[str] = None
    content_html: Optional[str] = None
    summary: Optional[str]
    keywords: Optional[List[str]]
    author: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    limit: int = 100,
    offset: int = 0,
    include_content: bool = False,
    db: Session = Depends(get_db)
):
    """List all documents (optionally with content)"""
    document_service = DocumentService(db)
    documents = document_service.list_documents(limit=limit, offset=offset)
    
    result = []
    for doc in documents:
        result.append(DocumentResponse(
            id=doc.id,
            title=doc.title,
            source_url=doc.source_url,
            source_type=doc.source_type.value,
            doc_type=doc.doc_type.value if doc.doc_type else 'doc',
            status=doc.status.value,
            vault_path=doc.vault_path,
            content_md=doc.content_md if include_content else None,
            content_html=doc.content_html if include_content else None,
            summary=doc.summary,
            keywords=doc.keywords,
            author=doc.author,
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat()
        ))
    
    return result


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """Get document by ID with full content"""
    document_service = DocumentService(db)
    doc = document_service.get_document_by_id(document_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        source_url=doc.source_url,
        source_type=doc.source_type.value,
        doc_type=doc.doc_type.value if doc.doc_type else 'doc',
        status=doc.status.value,
        vault_path=doc.vault_path,
        content_md=doc.content_md,
        content_html=doc.content_html,
        summary=doc.summary,
        keywords=doc.keywords,
        author=doc.author,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat()
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """Delete document"""
    document_service = DocumentService(db)
    success = document_service.delete_document(document_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"message": "Document deleted successfully"}

