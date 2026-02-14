"""Code repository API endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.core.database import get_db
from app.models.code_repository import CodeRepository, CodeChunk
from app.services.code_ingestion_service import CodeIngestionService

router = APIRouter(prefix="/code", tags=["code"])


class RepositoryIngestRequest(BaseModel):
    """Request to ingest a code repository"""
    local_path: str
    name: Optional[str] = None
    git_url: Optional[str] = None
    branch: str = "main"


class RepositoryResponse(BaseModel):
    """Repository response"""
    id: str
    name: str
    local_path: str
    primary_language: Optional[str]
    total_files: int
    total_functions: int
    total_classes: int
    lines_of_code: int
    last_synced: Optional[str]
    
    class Config:
        from_attributes = True


class CodeChunkResponse(BaseModel):
    """Code chunk response"""
    id: str
    chunk_name: Optional[str]
    chunk_type: str
    language: str
    file_path: str
    signature: Optional[str]
    start_line: int
    end_line: int
    
    class Config:
        from_attributes = True


@router.post("/repositories", response_model=RepositoryResponse)
async def ingest_repository(
    request: RepositoryIngestRequest,
    db: Session = Depends(get_db)
):
    """
    Ingest a code repository
    
    Scans the repository, extracts code chunks, and indexes them.
    """
    try:
        service = CodeIngestionService(db)
        repo = service.ingest_repository(
            repo_path=request.local_path,
            repo_name=request.name,
            git_url=request.git_url,
            branch=request.branch
        )
        
        return RepositoryResponse(
            id=repo.id,
            name=repo.name,
            local_path=repo.local_path,
            primary_language=repo.primary_language,
            total_files=repo.total_files,
            total_functions=repo.total_functions,
            total_classes=repo.total_classes,
            lines_of_code=repo.lines_of_code,
            last_synced=repo.last_synced.isoformat() if repo.last_synced else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/repositories", response_model=List[RepositoryResponse])
async def list_repositories(
    db: Session = Depends(get_db)
):
    """List all code repositories"""
    repos = db.query(CodeRepository).all()
    
    return [
        RepositoryResponse(
            id=repo.id,
            name=repo.name,
            local_path=repo.local_path,
            primary_language=repo.primary_language,
            total_files=repo.total_files,
            total_functions=repo.total_functions,
            total_classes=repo.total_classes,
            lines_of_code=repo.lines_of_code,
            last_synced=repo.last_synced.isoformat() if repo.last_synced else None
        )
        for repo in repos
    ]


@router.get("/repositories/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: str,
    db: Session = Depends(get_db)
):
    """Get repository details"""
    repo = db.query(CodeRepository).filter_by(id=repo_id).first()
    
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    return RepositoryResponse(
        id=repo.id,
        name=repo.name,
        local_path=repo.local_path,
        primary_language=repo.primary_language,
        total_files=repo.total_files,
        total_functions=repo.total_functions,
        total_classes=repo.total_classes,
        lines_of_code=repo.lines_of_code,
        last_synced=repo.last_synced.isoformat() if repo.last_synced else None
    )


@router.get("/repositories/{repo_id}/chunks", response_model=List[CodeChunkResponse])
async def get_repository_chunks(
    repo_id: str,
    chunk_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get code chunks for a repository"""
    query = db.query(CodeChunk).filter_by(repository_id=repo_id)
    
    if chunk_type:
        query = query.filter_by(chunk_type=chunk_type)
    
    chunks = query.limit(100).all()
    
    return [
        CodeChunkResponse(
            id=chunk.id,
            chunk_name=chunk.chunk_name,
            chunk_type=chunk.chunk_type,
            language=chunk.language,
            file_path=chunk.file_path,
            signature=chunk.signature,
            start_line=chunk.start_line,
            end_line=chunk.end_line
        )
        for chunk in chunks
    ]


@router.delete("/repositories/{repo_id}")
async def delete_repository(
    repo_id: str,
    db: Session = Depends(get_db)
):
    """Delete a repository and all its chunks"""
    repo = db.query(CodeRepository).filter_by(id=repo_id).first()
    
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    db.delete(repo)
    db.commit()
    
    return {"message": f"Repository {repo.name} deleted"}


@router.get("/stats")
async def get_code_stats(db: Session = Depends(get_db)):
    """Get code repository statistics"""
    from sqlalchemy import func
    
    total_repos = db.query(func.count(CodeRepository.id)).scalar() or 0
    total_chunks = db.query(func.count(CodeChunk.id)).scalar() or 0
    total_functions = db.query(func.sum(CodeRepository.total_functions)).scalar() or 0
    total_classes = db.query(func.sum(CodeRepository.total_classes)).scalar() or 0
    total_loc = db.query(func.sum(CodeRepository.lines_of_code)).scalar() or 0
    
    # Language breakdown
    lang_stats = db.query(
        CodeRepository.primary_language,
        func.count(CodeRepository.id).label('count')
    ).group_by(CodeRepository.primary_language).all()
    
    return {
        "total_repositories": total_repos,
        "total_chunks": total_chunks,
        "total_functions": total_functions,
        "total_classes": total_classes,
        "total_lines_of_code": total_loc,
        "languages": {lang: count for lang, count in lang_stats if lang}
    }


@router.get("/network-graph")
async def get_network_graph(db: Session = Depends(get_db)):
    """Get network graph data for visualization (repos and contributors)"""
    from app.models.code_repository import Contributor, Commit
    
    nodes = []
    edges = []
    
    repos = db.query(CodeRepository).all()
    contributors = db.query(Contributor).all()
    
    # Create repository nodes
    repo_y = 100
    for repo in repos:
        nodes.append({
            "id": f"repo-{repo.id}",
            "data": {"label": repo.name},
            "position": {"x": 400, "y": repo_y}
        })
        repo_y += 200
    
    # Create contributor nodes
    contrib_x = 0
    for contributor in contributors:
        nodes.append({
            "id": f"contrib-{contributor.id}",
            "data": {"label": contributor.name or contributor.email.split('@')[0]},
            "position": {"x": contrib_x, "y": 350}
        })
        contrib_x += 150
    
    # Create edges from repos to contributors based on commits
    commit_relationships = db.query(
        Commit.repository_id,
        Commit.author_id
    ).distinct().all()
    
    for repo_id, author_id in commit_relationships:
        edges.append({
            "id": f"edge-{repo_id}-{author_id}",
            "source": f"repo-{repo_id}",
            "target": f"contrib-{author_id}"
        })
    
    return {"nodes": nodes, "edges": edges}


@router.get("/contributors")
async def get_contributors(db: Session = Depends(get_db)):
    """Get all contributors with commit counts"""
    from app.models.code_repository import Contributor, Commit
    from sqlalchemy import func
    
    contributors_with_counts = db.query(
        Contributor,
        func.count(Commit.id).label('commit_count')
    ).outerjoin(
        Commit, Contributor.id == Commit.author_id
    ).group_by(
        Contributor.id
    ).all()
    
    return [
        {
            "id": contributor.id,
            "name": contributor.name,
            "email": contributor.email,
            "commit_count": commit_count
        }
        for contributor, commit_count in contributors_with_counts
    ]


@router.get("/activity")
async def get_recent_activity(db: Session = Depends(get_db)):
    """Get recent commit activity"""
    from app.models.code_repository import Commit
    from sqlalchemy.orm import joinedload
    
    recent_commits = db.query(Commit).options(
        joinedload(Commit.author),
        joinedload(Commit.repository)
    ).order_by(
        Commit.authored_date.desc()
    ).limit(10).all()
    
    return [
        {
            "sha": commit.sha[:8],
            "message": commit.message.strip().split('\n')[0][:100],
            "author": commit.author.name or commit.author.email,
            "repository": commit.repository.name,
            "date": commit.authored_date.isoformat()
        }
        for commit in recent_commits
    ]

