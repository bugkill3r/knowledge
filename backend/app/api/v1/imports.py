"""Import API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
import logging
import asyncio

from app.core.database import get_db
from app.services.import_service import ImportService
from app.models.import_job import ImportJob, ImportStatus

router = APIRouter()
logger = logging.getLogger(__name__)


class ImportRequest(BaseModel):
    """Request model for importing Google Docs"""
    url: str
    recursive: bool = True
    user_email: Optional[str] = None


class FolderImportRequest(BaseModel):
    """Request to import all docs from a Google Drive folder"""
    folder_url: str
    user_email: Optional[str] = None
    include_subfolders: bool = False


class ImportResponse(BaseModel):
    """Response model for import request"""
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    """Response model for job status"""
    job_id: str
    status: str
    total_docs: int
    processed_docs: int
    failed_docs: int
    progress_percentage: float
    error_message: Optional[str] = None
    imported_doc_ids: Optional[List[str]] = None
    started_at: str
    completed_at: Optional[str] = None


async def _run_import_job(
    job_id: str,
    url: str,
    user_email: Optional[str],
    recursive: bool,
    access_token: str
):
    """Background task to run the import job"""
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        import_service = ImportService(db, access_token)
        await import_service.import_from_url(
            url=url,
            user_email=user_email,
            recursive=recursive,
            job_id=job_id
        )
    except Exception as e:
        logger.error(f"Background import job {job_id} failed: {e}")
        # Update job status to failed
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if job:
            job.status = ImportStatus.FAILED
            job.error_message = str(e)
            from datetime import datetime
            job.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


@router.post("/google-docs", response_model=ImportResponse)
async def import_google_docs(
    request: ImportRequest,
    background_tasks: BackgroundTasks,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """Import documents from Google Docs URL
    
    Requires Authorization header with Google access token
    """
    # Extract access token from Authorization header
    if not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    access_token = authorization.replace('Bearer ', '')
    
    try:
        # Create a pending import job immediately
        from app.models.import_job import ImportJob
        from datetime import datetime
        
        job = ImportJob(
            source_url=request.url,
            status=ImportStatus.PENDING,
            user_email=request.user_email,
            total_docs=1,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Start the import in the background
        background_tasks.add_task(
            _run_import_job,
            job.id,
            request.url,
            request.user_email,
            request.recursive,
            access_token
        )
        
        return ImportResponse(
            job_id=job.id,
            status=job.status.value,
            message=f"Import job queued. Check status using job_id."
        )
        
    except Exception as e:
        logger.error(f"Failed to queue import job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue import: {str(e)}")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_import_job_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Get status of an import job"""
    import_service = ImportService(db, "")  # Token not needed for read-only operation
    
    job = import_service.get_import_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    
    # Parse imported doc IDs if available
    imported_ids = None
    if job.imported_doc_ids:
        import json
        try:
            imported_ids = json.loads(job.imported_doc_ids)
        except:
            pass
    
    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        total_docs=job.total_docs,
        processed_docs=job.processed_docs,
        failed_docs=job.failed_docs,
        progress_percentage=job.progress_percentage,
        error_message=job.error_message,
        imported_doc_ids=imported_ids,
        started_at=job.started_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None
    )


@router.get("/jobs", response_model=List[JobStatusResponse])
async def list_import_jobs(
    user_email: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List import jobs"""
    import_service = ImportService(db, "")
    
    jobs = import_service.list_import_jobs(user_email=user_email, limit=limit)
    
    result = []
    for job in jobs:
        imported_ids = None
        if job.imported_doc_ids:
            import json
            try:
                imported_ids = json.loads(job.imported_doc_ids)
            except:
                pass
        
        result.append(JobStatusResponse(
            job_id=job.id,
            status=job.status.value,
            total_docs=job.total_docs,
            processed_docs=job.processed_docs,
            failed_docs=job.failed_docs,
            progress_percentage=job.progress_percentage,
            error_message=job.error_message,
            imported_doc_ids=imported_ids,
            started_at=job.started_at.isoformat(),
            completed_at=job.completed_at.isoformat() if job.completed_at else None
        ))
    
    return result


@router.post("/google-folder")
async def import_google_folder(
    request: FolderImportRequest,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Import all Google Docs from a folder
    
    Discovers all documents in the specified folder and queues them for import.
    Returns a list of import job IDs.
    """
    if not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    access_token = authorization.replace('Bearer ', '')
    
    try:
        # Extract folder ID from URL
        import re
        folder_id_match = re.search(r'/folders/([a-zA-Z0-9-_]+)', request.folder_url)
        if not folder_id_match:
            raise HTTPException(
                status_code=400,
                detail="Invalid folder URL. Expected format: https://drive.google.com/drive/folders/FOLDER_ID"
            )
        
        folder_id = folder_id_match.group(1)
        
        # Use Drive API to list files
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        
        credentials = Credentials(token=access_token)
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # Query for Google Docs in the folder
        query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false"
        
        results = drive_service.files().list(
            q=query,
            fields="files(id, name, webViewLink, modifiedTime, owners)",
            pageSize=100  # Adjust as needed
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            return {
                "message": "No Google Docs found in this folder",
                "folder_id": folder_id,
                "jobs": []
            }
        
        # Queue imports for each document
        import_service = ImportService(db, access_token)
        job_ids = []
        
        for file in files:
            doc_url = file.get('webViewLink') or f"https://docs.google.com/document/d/{file['id']}"
            
            try:
                result = await import_service.import_from_url(
                    url=doc_url,
                    user_email=request.user_email
                )
                job_ids.append({
                    "job_id": result.get('job_id'),
                    "document_name": file.get('name'),
                    "document_id": file.get('id')
                })
            except Exception as e:
                logger.error(f"Failed to queue import for {file.get('name')}: {e}")
                job_ids.append({
                    "document_name": file.get('name'),
                    "document_id": file.get('id'),
                    "error": str(e)
                })
        
        return {
            "message": f"Queued {len(job_ids)} documents for import",
            "folder_id": folder_id,
            "total_documents": len(files),
            "jobs": job_ids
        }
        
    except Exception as e:
        logger.error(f"Folder import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Folder import failed: {str(e)}")


@router.get("/debug/show-token")
async def show_token_for_scripts(authorization: str = Header(...)):
    """Debug endpoint to display your access token for use in scripts
    
    This is a temporary helper to get your token for the image extraction script.
    """
    if not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    access_token = authorization.replace('Bearer ', '')
    
    return {
        "success": True,
        "token": access_token,
        "token_length": len(access_token),
        "instructions": {
            "step_1": "Copy the token above",
            "step_2": "Open terminal and run:",
            "command": f"export GOOGLE_ACCESS_TOKEN='{access_token}'",
            "step_3": "Then run the extraction script:",
            "script": "Run your image extraction script if you have one (path configurable via env)."
        },
        "note": "This endpoint is for development only. Remove in production."
    }

