"""
Search API - Semantic search using vector embeddings
"""

from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import asyncio
import json
import logging
import tempfile
import os

from app.config import settings
from app.services.embedding_service import get_embedding_service
from app.services.ai_service import get_ai_service
from app.core.database import get_db
from app.models.document import Document
from app.models.code_repository import CodeRepository

router = APIRouter(prefix="/search", tags=["search"])
logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """Individual search result"""
    document_id: str
    document_title: str
    chunk_text: str
    similarity_score: float
    chunk_index: int
    source_url: Optional[str] = None
    vault_path: Optional[str] = None
    # Code-specific fields
    doc_type: Optional[str] = None
    language: Optional[str] = None
    repository_id: Optional[str] = None
    repository_name: Optional[str] = None
    file_path: Optional[str] = None
    chunk_type: Optional[str] = None
    chunk_name: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None


class SearchResponse(BaseModel):
    """Search response with results"""
    query: str
    results: List[SearchResult]
    total_results: int
    ai_answer: Optional[str] = None  # RAG-generated answer


@router.get("", response_model=SearchResponse)
async def semantic_search(
    q: str = Query(..., description="Search query", min_length=3),
    limit: int = Query(10, description="Number of results to return", ge=1, le=50),
    generate_answer: bool = Query(True, description="Generate AI answer using RAG"),
    doc_type: Optional[str] = Query(None, description="Filter by document type (prd, tech-spec, kt, etc.)"),
    author: Optional[str] = Query(None, description="Filter by author"),
    date_from: Optional[str] = Query(None, description="Filter by date from (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter by date to (YYYY-MM-DD)"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    db: Session = Depends(get_db)
):
    """
    Perform semantic search across all documents with optional RAG
    
    Uses vector similarity to find relevant content based on meaning,
    not just keyword matching. Optionally generates an AI answer based
    on the retrieved context (Retrieval-Augmented Generation).
    
    Supports advanced filtering by:
    - Document type (prd, tech-spec, kt, meeting, runbook, etc.)
    - Author name
    - Date range (created_at)
    - Tags
    """
    try:
        # Get embedding service
        embedding_service = get_embedding_service()
        
        # Perform search (get more results for filtering)
        raw_results = embedding_service.search_similar(
            query=q,
            n_results=limit * 3  # Get more to allow for filtering
        )
        
        # Format and filter results
        search_results = []
        for result in raw_results:
            metadata = result.get('metadata', {})
            
            # Apply filters
            if doc_type and metadata.get('doc_type') != doc_type:
                continue
            
            if author and metadata.get('author', '').lower() != author.lower():
                continue
            
            # Date filtering
            if date_from or date_to:
                created_at_str = metadata.get('created_at')
                if created_at_str:
                    try:
                        from datetime import datetime
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        
                        if date_from:
                            date_from_dt = datetime.fromisoformat(date_from)
                            if created_at < date_from_dt:
                                continue
                        
                        if date_to:
                            date_to_dt = datetime.fromisoformat(date_to)
                            if created_at > date_to_dt:
                                continue
                    except (ValueError, AttributeError):
                        pass
            
            # Tag filtering (if tags are stored in metadata)
            if tags:
                tag_list = [t.strip().lower() for t in tags.split(',')]
                doc_tags = metadata.get('tags', [])
                if isinstance(doc_tags, list):
                    doc_tags_lower = [t.lower() for t in doc_tags]
                    if not any(tag in doc_tags_lower for tag in tag_list):
                        continue
            
            # Calculate similarity score (ChromaDB returns cosine distance in range [0, 2])
            # Convert distance to similarity score (0-1, higher is better)
            # For cosine distance: 0 = identical, 2 = opposite
            distance = result.get('distance', 2.0)
            similarity = max(0, (2 - distance) / 2)
            
            # Fetch repository name if this is a code result
            repository_name = None
            if metadata.get('repository_id'):
                repo = db.query(CodeRepository).filter_by(id=metadata.get('repository_id')).first()
                if repo:
                    repository_name = repo.name
            
            search_results.append(SearchResult(
                document_id=metadata.get('document_id', ''),
                document_title=metadata.get('document_title', metadata.get('chunk_name', 'Unknown')),
                chunk_text=result.get('document', ''),
                similarity_score=round(similarity, 4),
                chunk_index=metadata.get('chunk_index', 0),
                source_url=metadata.get('source_url'),
                vault_path=metadata.get('vault_path'),
                # Code-specific fields
                doc_type=metadata.get('doc_type'),
                language=metadata.get('language'),
                repository_id=metadata.get('repository_id'),
                repository_name=repository_name,
                file_path=metadata.get('file_path'),
                chunk_type=metadata.get('chunk_type'),
                chunk_name=metadata.get('chunk_name'),
                start_line=metadata.get('start_line'),
                end_line=metadata.get('end_line')
            ))
            
            # Limit results after filtering
            if len(search_results) >= limit:
                break
        
        # Generate AI answer using RAG if requested
        ai_answer = None
        if generate_answer and search_results:
            try:
                ai_service = get_ai_service()
                if ai_service.client:
                    # Combine top results as context
                    context_chunks = []
                    for i, result in enumerate(search_results[:5], 1):  # Use top 5 results
                        context_chunks.append(
                            f"[Source {i}: {result.document_title}]\n{result.chunk_text}"
                        )
                    
                    context = "\n\n---\n\n".join(context_chunks)
                    
                    # Generate answer using LLM
                    response = ai_service.client.chat.completions.create(
                        model=ai_service.model,
                        messages=[
                            {
                                "role": "system",
                                "content": f"""You are a helpful assistant for {settings.PROJECT_NAME}. Answer from the provided context. Be concise, cite sources. If context is insufficient, say so."""
                            },
                            {
                                "role": "user",
                                "content": f"""Question: {q}

Context from knowledge base:
{context}

Please provide a clear, accurate answer based on the context above. 
Mention which documents or sources support your answer."""
                            }
                        ],
                        temperature=0.3,
                        max_tokens=500
                    )
                    
                    ai_answer = response.choices[0].message.content.strip()
            except Exception as e:
                # Don't fail the entire request if RAG fails
                import logging
                logging.warning(f"RAG answer generation failed: {e}")
        
        return SearchResponse(
            query=q,
            results=search_results,
            total_results=len(search_results),
            ai_answer=ai_answer
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/filters")
async def get_filter_options(db: Session = Depends(get_db)) -> Dict:
    """
    Get available filter options for advanced search
    
    Returns unique values for:
    - Document types
    - Authors
    - Tags
    - Date range
    """
    try:
        documents = db.query(Document).all()
        
        # Extract unique values
        doc_types = set()
        authors = set()
        all_tags = set()
        dates = []
        
        for doc in documents:
            if doc.doc_type:
                doc_types.add(doc.doc_type.value)
            if doc.author:
                authors.add(doc.author)
            if doc.keywords:
                if isinstance(doc.keywords, list):
                    all_tags.update(doc.keywords)
            if doc.created_at:
                dates.append(doc.created_at)
        
        # Get date range
        date_range = {}
        if dates:
            date_range = {
                "min": min(dates).isoformat(),
                "max": max(dates).isoformat()
            }
        
        return {
            "doc_types": sorted(list(doc_types)),
            "authors": sorted(list(authors)),
            "tags": sorted(list(all_tags)),
            "date_range": date_range,
            "total_documents": len(documents)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get filter options: {str(e)}"
        )


@router.get("/suggestions", response_model=List[str])
async def get_search_suggestions(
    q: str = Query(..., description="Partial query", min_length=2),
    limit: int = Query(5, description="Number of suggestions", ge=1, le=10)
):
    """
    Get search suggestions based on partial query
    
    This is a simple implementation that returns related document titles.
    Could be enhanced with more sophisticated suggestion logic.
    """
    try:
        embedding_service = get_embedding_service()
        
        # Search for similar content
        results = embedding_service.search_similar(
            query=q,
            n_results=limit * 2  # Get more to deduplicate
        )
        
        # Extract unique document titles
        titles = []
        seen = set()
        
        for result in results:
            metadata = result.get('metadata', {})
            title = metadata.get('document_title', '')
            
            if title and title not in seen:
                titles.append(title)
                seen.add(title)
                
                if len(titles) >= limit:
                    break
        
        return titles
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get suggestions: {str(e)}"
        )


@router.get("/answer-stream")
async def stream_search_answer(
    q: str = Query(..., description="Search query", min_length=3),
    limit: int = Query(10, description="Number of context results", ge=1, le=50),
    model: str = Query("claude-code", description="Model to use (claude-code, claude-api, openai)"),
    db: Session = Depends(get_db)
):
    """
    Stream AI answer to search query using Claude Code CLI with RAG context
    
    Performs semantic search to get relevant context, then streams answer
    using Claude Code in headless mode for real-time response.
    """
    
    async def event_generator():
        try:
            # Step 1: Get relevant context using semantic search
            logger.info(f"🔍 Searching for context: {q}")
            yield f"data: {json.dumps({'type': 'status', 'message': 'Searching knowledge base...'})}\n\n"
            
            embedding_service = get_embedding_service()
            raw_results = embedding_service.search_similar(query=q, n_results=limit)
            
            # Format context from top results
            context_chunks = []
            sources = []
            for i, result in enumerate(raw_results[:5], 1):  # Top 5 results
                metadata = result.get('metadata', {})
                doc_title = metadata.get('document_title', metadata.get('chunk_name', 'Unknown'))
                chunk_text = result.get('document', '')
                
                context_chunks.append(f"[Source {i}: {doc_title}]\n{chunk_text}")
                sources.append({
                    'title': doc_title,
                    'similarity': round(max(0, (2 - result.get('distance', 2.0)) / 2), 4),
                    'vault_path': metadata.get('vault_path'),
                    'source_url': metadata.get('source_url')
                })
            
            context = "\n\n---\n\n".join(context_chunks)
            
            # Send sources to frontend
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            
            # Step 2: Build prompt for Claude
            prompt = f"""You are an assistant for {settings.PROJECT_NAME}.

**Question**: {q}

**Context from Knowledge Base**:
{context}

**Instructions**:
- Provide a clear, accurate answer based on the context above
- Be concise but thorough - aim for 2-4 paragraphs
- Cite which documents/sources support your answer
- If the context doesn't contain enough information, say so clearly
- Draw connections between different sources if relevant
- Focus on actionable insights

Answer:"""

            logger.info("Streaming answer using %s", model)
            yield f"data: {json.dumps({'type': 'status', 'message': f'Generating answer with {model}...'})}\n\n"
            
            # Step 3: Stream answer using Claude Code CLI
            if model == "claude-code":
                # Write prompt to temp file to avoid shell limits
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(prompt)
                    temp_file = f.name
                
                try:
                    # Use stdin redirection from file
                    process = await asyncio.create_subprocess_shell(
                        f"cat {temp_file} | claude --print",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    # Stream output line by line
                    while True:
                        line = await process.stdout.readline()
                        if not line:
                            break
                        
                        text = line.decode('utf-8', errors='ignore')
                        if text.strip():
                            yield f"data: {json.dumps({'type': 'content', 'text': text})}\n\n"
                    
                    await process.wait()
                    
                    if process.returncode != 0:
                        stderr = await process.stderr.read()
                        error_msg = stderr.decode('utf-8', errors='ignore')
                        logger.error(f"❌ Claude Code failed: {error_msg}")
                        yield f"data: {json.dumps({'type': 'error', 'message': f'Claude Code failed: {error_msg}'})}\n\n"
                    else:
                        logger.info("✅ Answer generated successfully")
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
            
            elif model == "claude-api":
                # Use direct Anthropic API
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic()
                
                async with client.messages.stream(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                ) as stream:
                    async for text in stream.text_stream:
                        if text:
                            yield f"data: {json.dumps({'type': 'content', 'text': text})}\n\n"
                
                logger.info("✅ Answer generated successfully")
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
            else:
                # Fallback to OpenAI
                ai_service = get_ai_service()
                if not ai_service.client:
                    raise Exception("OpenAI client not configured")
                
                response = ai_service.client.chat.completions.create(
                    model=ai_service.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1000,
                    stream=True
                )
                
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        text = chunk.choices[0].delta.content
                        yield f"data: {json.dumps({'type': 'content', 'text': text})}\n\n"
                
                logger.info("✅ Answer generated successfully")
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
        except Exception as e:
            logger.error(f"❌ Search answer streaming failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

