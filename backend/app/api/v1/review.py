"""Document Review API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging
import json
import asyncio

from app.core.database import get_db
from app.config import settings
from app.services.ai_review_service import AIReviewService
from app.models.document_review import ReviewType

router = APIRouter()
logger = logging.getLogger(__name__)


class SaveReviewRequest(BaseModel):
    """Request model for saving a reviewed document"""
    document_id: str
    document_title: str
    review_type: str
    reviewed_content: str
    personas: List[str]
    model: str


class ReviewRequest(BaseModel):
    """Request model for creating a review"""
    document_id: str
    review_type: str = ReviewType.COMPREHENSIVE.value
    focus_areas: Optional[List[str]] = None
    model: Optional[str] = "sonnet-4"  # Default to Claude 4.5 Sonnet
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "0bd12bad-8761-4324-9742-f06bc7a22013",
                "review_type": "comprehensive",
                "focus_areas": ["architecture", "technical"],
                "model": "sonnet-4"
            }
        }


class ReviewResponse(BaseModel):
    """Response model for review creation"""
    review_id: str
    status: str
    message: str
    original_document_id: str
    review_type: str


class ReviewStatusResponse(BaseModel):
    """Response model for review status"""
    review_id: str
    status: str
    review_type: str
    original_document_id: str
    original_document_title: Optional[str] = None
    reviewed_document_id: Optional[str] = None
    reviewed_document_title: Optional[str] = None
    reviewed_document_path: Optional[str] = None
    streaming_content: Optional[str] = None
    total_comments: int
    comment_categories: Optional[dict] = None
    ai_model: Optional[str] = None
    error_message: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None
    created_by: Optional[str] = None


async def _run_review_job(review_id: str, model: str = "sonnet-4.5"):
    """Background task to process review"""
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        service = AIReviewService(db)
        await service.process_review(review_id, model=model)
    except Exception as e:
        logger.error(f"Background review job {review_id} failed: {e}")
    finally:
        db.close()


@router.get("/stream/{document_id}")
async def stream_review(
    document_id: str,
    review_type: str = "comprehensive",
    personas: str = "engineering-leader,principal-engineer",
    model: str = "sonnet-4.5",
    test: bool = False,
    db: Session = Depends(get_db)
):
    """
    Stream AI review in real-time using Server-Sent Events
    """
    logger.info(f"SSE endpoint called for document {document_id}, model={model}, test={test}")

    async def event_generator():
        try:
            logger.info(f"Starting stream for document {document_id}, model={model}, test={test}")
            
            # Send initial event
            yield f"data: {json.dumps({'type': 'start', 'message': 'Starting review...'})}\n\n"
            await asyncio.sleep(0.1)
            
            # Test mode for debugging
            if test:
                logger.info("Running in TEST mode")
                yield f"data: {json.dumps({'type': 'info', 'message': 'Test mode enabled'})}\n\n"
                
                test_content = "# Test Review\n\nThis is a test review streaming in real-time.\n\n"
                for char in test_content:
                    yield f"data: {json.dumps({'type': 'content', 'content': char})}\n\n"
                    await asyncio.sleep(0.05)
                
                yield f"data: {json.dumps({'type': 'complete', 'message': 'Test completed!'})}\n\n"
                return
            
            # Real review
            service = AIReviewService(db)
            
            # Get document
            from app.services.document_service import DocumentService
            doc_service = DocumentService(db)
            document = doc_service.get_document_by_id(document_id)
            
            if not document:
                logger.error(f"❌ Document {document_id} not found")
                yield f"data: {json.dumps({'type': 'error', 'message': 'Document not found'})}\n\n"
                return
            
            logger.info(f"📄 Reviewing document: {document.title}")
            yield f"data: {json.dumps({'type': 'info', 'message': f'Reviewing: {document.title}'})}\n\n"
            
            # Stream the review - choose method based on model
            persona_list = personas.split(',')
            chunk_count = 0
            
            # Choose streaming method based on model
            if model == 'claude-code':
                logger.info(f"Using Claude Code CLI for {document.title}")
                stream_method = service.stream_review_claude_code(document, review_type, persona_list, model)
            elif model.startswith('claude-'):
                logger.info(f"Using Claude API for {document.title}")
                stream_method = service.stream_review_claude(document, review_type, persona_list, model)
            else:
                logger.info(f"Using Cursor Agent for {document.title}")
                stream_method = service.stream_review(document, review_type, persona_list, model)
            
            async for chunk in stream_method:
                chunk_count += 1
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                await asyncio.sleep(0)  # Allow other tasks to run
            
            logger.info(f"Review completed: {chunk_count} chunks streamed")
            yield f"data: {json.dumps({'type': 'complete', 'message': 'Review completed!'})}\n\n"
            
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "*"
        }
    )

@router.post("/document/{document_id}", response_model=ReviewResponse)
async def create_document_review(
    document_id: str,
    request: ReviewRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new AI review for a document
    
    The review will be processed in the background. Use the review_id to check status.
    """
    try:
        service = AIReviewService(db)
        
        # Create review job
        review = await service.create_review_job(
            document_id=document_id,
            review_type=request.review_type,
            focus_areas=request.focus_areas,
            created_by=None,  # TODO: Get from auth
            model=request.model or "sonnet-4"
        )
        
        # Start processing in background
        background_tasks.add_task(_run_review_job, review.id, request.model or "sonnet-4")
        
        return ReviewResponse(
            review_id=review.id,
            status=review.status,
            message=f"Review job created. Processing document with {request.review_type} review.",
            original_document_id=document_id,
            review_type=review.review_type
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create review: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create review: {str(e)}")


@router.get("/jobs/{review_id}", response_model=ReviewStatusResponse)
async def get_review_status(
    review_id: str,
    db: Session = Depends(get_db)
):
    """Get status of a review job"""
    service = AIReviewService(db)
    review = service.get_review_by_id(review_id)
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Get document titles
    original_title = review.original_document.title if review.original_document else None
    reviewed_title = None
    reviewed_path = None
    
    if review.reviewed_document:
        reviewed_title = review.reviewed_document.title
        reviewed_path = review.reviewed_document.vault_path
    
    return ReviewStatusResponse(
        review_id=review.id,
        status=review.status,
        review_type=review.review_type,
        original_document_id=review.original_document_id,
        original_document_title=original_title,
        reviewed_document_id=review.reviewed_document_id,
        reviewed_document_title=reviewed_title,
        reviewed_document_path=reviewed_path,
        streaming_content=review.streaming_content,
        total_comments=review.total_comments or 0,
        comment_categories=review.comment_categories,
        ai_model=review.ai_model,
        error_message=review.error_message,
        started_at=review.started_at.isoformat(),
        completed_at=review.completed_at.isoformat() if review.completed_at else None,
        created_by=review.created_by
    )


@router.get("/history", response_model=List[ReviewStatusResponse])
async def list_review_history(
    document_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List review history with optional filters"""
    service = AIReviewService(db)
    reviews = service.list_reviews(
        document_id=document_id,
        status=status,
        limit=limit
    )
    
    result = []
    for review in reviews:
        original_title = review.original_document.title if review.original_document else None
        reviewed_title = None
        reviewed_path = None
        
        if review.reviewed_document:
            reviewed_title = review.reviewed_document.title
            reviewed_path = review.reviewed_document.vault_path
        
        result.append(ReviewStatusResponse(
            review_id=review.id,
            status=review.status,
            review_type=review.review_type,
            original_document_id=review.original_document_id,
            original_document_title=original_title,
            reviewed_document_id=review.reviewed_document_id,
            reviewed_document_title=reviewed_title,
            reviewed_document_path=reviewed_path,
            total_comments=review.total_comments or 0,
            comment_categories=review.comment_categories,
            ai_model=review.ai_model,
            error_message=review.error_message,
            started_at=review.started_at.isoformat(),
            completed_at=review.completed_at.isoformat() if review.completed_at else None,
            created_by=review.created_by
        ))
    
    return result


@router.post("/save")
async def save_reviewed_document(
    request: SaveReviewRequest,
    db: Session = Depends(get_db)
):
    """
    Save the reviewed document to Obsidian vault (or success only when Obsidian is disabled).
    """
    try:
        import os
        from datetime import datetime
        
        logger.info(f"💾 Saving reviewed document: {request.document_title}")
        
        if not settings.obsidian_enabled:
            return {
                "success": True,
                "vault_path": None,
                "obsidian_uri": None,
                "message": "Review saved (Obsidian vault not configured)."
            }
        
        vault_base = settings.OBSIDIAN_VAULT_PATH or ""
        review_dir = os.path.join(vault_base, "05 - AI", "AI Reviews")
        os.makedirs(review_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in request.document_title)
        safe_title = safe_title.replace(' ', '_')
        filename = f"{safe_title}_reviewed_{timestamp}.md"
        vault_path = os.path.join(review_dir, filename)
        
        personas_str = ", ".join(request.personas)
        header = f"""---
original_document: {request.document_title}
review_type: {request.review_type}
personas: {personas_str}
ai_model: {request.model}
reviewed_at: {datetime.now().isoformat()}
---

"""
        
        with open(vault_path, 'w', encoding='utf-8') as f:
            f.write(header + request.reviewed_content)
        
        logger.info(f"✅ Saved to: {vault_path}")
        
        relative_path = os.path.relpath(vault_path, vault_base)
        vault_name = settings.obsidian_vault_name
        obsidian_uri = f"obsidian://open?vault={vault_name}&file={relative_path.replace(' ', '%20')}"
        
        return {
            "success": True,
            "vault_path": relative_path,
            "obsidian_uri": obsidian_uri,
            "message": "Reviewed document saved successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to save reviewed document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

