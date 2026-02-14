"""Collections API endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.collection import Collection
from app.models.document import Document
from app.models.code_repository import CodeRepository

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionCreate(BaseModel):
    """Request to create a collection"""
    name: str
    description: Optional[str] = None
    color: str = '#3B82F6'
    icon: str = '📁'


class CollectionUpdate(BaseModel):
    """Request to update a collection"""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class CollectionResponse(BaseModel):
    """Collection response"""
    id: str
    name: str
    description: Optional[str]
    color: str
    icon: str
    document_count: int
    repository_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentSummary(BaseModel):
    """Document summary for collection items"""
    id: str
    title: str
    doc_type: Optional[str]
    created_at: datetime


class RepositorySummary(BaseModel):
    """Repository summary for collection items"""
    id: str
    name: str
    primary_language: Optional[str]
    created_at: datetime


class CollectionItemsResponse(BaseModel):
    """Collection items response"""
    documents: List[DocumentSummary]
    repositories: List[RepositorySummary]


@router.post("/", response_model=CollectionResponse)
async def create_collection(
    collection: CollectionCreate,
    db: Session = Depends(get_db)
):
    """Create a new collection"""
    new_collection = Collection(**collection.dict())
    db.add(new_collection)
    db.commit()
    db.refresh(new_collection)
    
    return CollectionResponse(
        **new_collection.__dict__,
        document_count=0,
        repository_count=0
    )


@router.get("/", response_model=List[CollectionResponse])
async def list_collections(db: Session = Depends(get_db)):
    """List all collections"""
    collections = db.query(Collection).all()
    return [
        CollectionResponse(
            **c.__dict__,
            document_count=len(c.documents),
            repository_count=len(c.repositories)
        )
        for c in collections
    ]


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(collection_id: str, db: Session = Depends(get_db)):
    """Get a specific collection"""
    collection = db.query(Collection).filter_by(id=collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    return CollectionResponse(
        **collection.__dict__,
        document_count=len(collection.documents),
        repository_count=len(collection.repositories)
    )


@router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: str,
    updates: CollectionUpdate,
    db: Session = Depends(get_db)
):
    """Update a collection"""
    collection = db.query(Collection).filter_by(id=collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    for key, value in updates.dict(exclude_unset=True).items():
        setattr(collection, key, value)
    
    db.commit()
    db.refresh(collection)
    
    return CollectionResponse(
        **collection.__dict__,
        document_count=len(collection.documents),
        repository_count=len(collection.repositories)
    )


@router.delete("/{collection_id}")
async def delete_collection(collection_id: str, db: Session = Depends(get_db)):
    """Delete a collection"""
    collection = db.query(Collection).filter_by(id=collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    db.delete(collection)
    db.commit()
    return {"message": "Collection deleted successfully"}


@router.post("/{collection_id}/documents/{document_id}")
async def add_document_to_collection(
    collection_id: str,
    document_id: str,
    db: Session = Depends(get_db)
):
    """Add a document to a collection"""
    collection = db.query(Collection).filter_by(id=collection_id).first()
    document = db.query(Document).filter_by(id=document_id).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document not in collection.documents:
        collection.documents.append(document)
        db.commit()
    
    return {"message": "Document added to collection"}


@router.delete("/{collection_id}/documents/{document_id}")
async def remove_document_from_collection(
    collection_id: str,
    document_id: str,
    db: Session = Depends(get_db)
):
    """Remove a document from a collection"""
    collection = db.query(Collection).filter_by(id=collection_id).first()
    document = db.query(Document).filter_by(id=document_id).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document in collection.documents:
        collection.documents.remove(document)
        db.commit()
    
    return {"message": "Document removed from collection"}


@router.post("/{collection_id}/repositories/{repository_id}")
async def add_repository_to_collection(
    collection_id: str,
    repository_id: str,
    db: Session = Depends(get_db)
):
    """Add a repository to a collection"""
    collection = db.query(Collection).filter_by(id=collection_id).first()
    repository = db.query(CodeRepository).filter_by(id=repository_id).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    if repository not in collection.repositories:
        collection.repositories.append(repository)
        db.commit()
    
    return {"message": "Repository added to collection"}


@router.delete("/{collection_id}/repositories/{repository_id}")
async def remove_repository_from_collection(
    collection_id: str,
    repository_id: str,
    db: Session = Depends(get_db)
):
    """Remove a repository from a collection"""
    collection = db.query(Collection).filter_by(id=collection_id).first()
    repository = db.query(CodeRepository).filter_by(id=repository_id).first()
    
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    if repository in collection.repositories:
        collection.repositories.remove(repository)
        db.commit()
    
    return {"message": "Repository removed from collection"}


@router.get("/{collection_id}/items", response_model=CollectionItemsResponse)
async def get_collection_items(
    collection_id: str,
    db: Session = Depends(get_db)
):
    """Get all documents and repositories in a collection"""
    collection = db.query(Collection).filter_by(id=collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    documents = [
        DocumentSummary(
            id=doc.id,
            title=doc.title,
            doc_type=doc.doc_type.value if doc.doc_type else None,
            created_at=doc.created_at
        )
        for doc in collection.documents
    ]
    
    repositories = [
        RepositorySummary(
            id=repo.id,
            name=repo.name,
            primary_language=repo.primary_language,
            created_at=repo.created_at
        )
        for repo in collection.repositories
    ]
    
    return CollectionItemsResponse(
        documents=documents,
        repositories=repositories
    )

