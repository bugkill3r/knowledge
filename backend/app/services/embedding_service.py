"""
Embedding Service - Generate and manage vector embeddings for documents
"""

import logging
from typing import List, Optional, Dict
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import Document
from app.models.embedding import Embedding
from app.models.code_repository import CodeChunk

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and storing vector embeddings"""
    
    def __init__(self):
        """Initialize embedding service with ChromaDB and sentence transformer"""
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_DB_PATH,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        self.collection = self.chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"description": "Knowledge base embeddings"}
        )
        
        # Initialize sentence transformer model
        # Using a smaller, efficient model for local embeddings
        logger.info("Loading sentence transformer model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Sentence transformer model loaded successfully")
    
    def chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks for embedding
        
        Args:
            text: The text to chunk
            chunk_size: Maximum characters per chunk
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        if not text or len(text) == 0:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Get chunk
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary if possible
            if end < len(text):
                # Look for last period, question mark, or exclamation in chunk
                last_sentence_end = max(
                    chunk.rfind('. '),
                    chunk.rfind('? '),
                    chunk.rfind('! ')
                )
                
                if last_sentence_end > chunk_size * 0.5:  # Only if we found a decent break point
                    chunk = chunk[:last_sentence_end + 1]
                    end = start + last_sentence_end + 1
            
            chunks.append(chunk.strip())
            start = end - overlap
        
        return [c for c in chunks if len(c.strip()) > 0]
    
    def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts
        
        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process at once
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        try:
            # Generate embeddings using sentence transformer
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_numpy=True
            )
            
            # Convert to list of lists
            return embeddings.tolist()
        
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def store_document_embeddings(
        self,
        db: Session,
        document: Document,
        force_regenerate: bool = False
    ) -> int:
        """
        Generate and store embeddings for a document
        
        Args:
            db: Database session
            document: Document to process
            force_regenerate: If True, regenerate even if embeddings exist
            
        Returns:
            Number of chunks created
        """
        # Check if embeddings already exist
        if not force_regenerate:
            existing_count = db.query(Embedding).filter(
                Embedding.document_id == document.id
            ).count()
            
            if existing_count > 0:
                logger.info(f"Document {document.id} already has {existing_count} embeddings")
                return existing_count
        
        # Delete existing embeddings if regenerating
        if force_regenerate:
            db.query(Embedding).filter(Embedding.document_id == document.id).delete()
            # Also delete from ChromaDB
            try:
                self.collection.delete(where={"document_id": str(document.id)})
            except Exception as e:
                logger.warning(f"Error deleting from ChromaDB: {e}")
        
        # Get document content
        content = document.content_md or ""
        if not content.strip():
            logger.warning(f"Document {document.id} has no content to embed")
            return 0
        
        # Add title and metadata context to first chunk
        title_context = f"# {document.title}\n\n"
        if document.metadata_json:
            metadata = document.metadata_json
            if metadata.get('summary'):
                title_context += f"Summary: {metadata['summary']}\n\n"
            if metadata.get('tags'):
                title_context += f"Tags: {', '.join(metadata['tags'])}\n\n"
        
        content_with_context = title_context + content
        
        # Chunk the content
        chunks = self.chunk_text(content_with_context)
        logger.info(f"Split document {document.id} into {len(chunks)} chunks")
        
        if not chunks:
            logger.warning(f"No chunks created for document {document.id}")
            return 0
        
        # Generate embeddings
        embeddings = self.generate_embeddings(chunks)
        
        # Store in database and ChromaDB
        chunk_count = 0
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            # Create database record
            db_embedding = Embedding(
                document_id=document.id,
                chunk_text=chunk,
                chunk_index=i
            )
            db.add(db_embedding)
            chunk_count += 1
            
            # Store in ChromaDB
            self.collection.add(
                ids=[f"{document.id}_{i}"],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "document_id": str(document.id),
                    "document_title": document.title,
                    "chunk_index": i,
                    "source_url": document.source_url or "",
                    "vault_path": document.vault_path or ""
                }]
            )
        
        db.commit()
        logger.info(f"Stored {chunk_count} embeddings for document {document.id}")
        return chunk_count
    
    def generate_code_embeddings(self, code_chunk: CodeChunk) -> str:
        """
        Generates embedding for a single code chunk and stores it in ChromaDB.
        Returns the chunk ID.
        """
        # Prepare text for embedding
        chunk_text = self._format_code_chunk_for_embedding(code_chunk)
        
        # Prepare metadata
        metadata = {
            "chunk_id": code_chunk.id,
            "repository_id": code_chunk.repository_id,
            "file_path": code_chunk.file_path,
            "chunk_type": code_chunk.chunk_type,
            "chunk_name": code_chunk.chunk_name or "unknown",
            "full_name": code_chunk.full_name or code_chunk.chunk_name or "unknown",
            "language": code_chunk.language,
            "start_line": code_chunk.start_line,
            "end_line": code_chunk.end_line,
            "source_type": "code",  # Differentiate from docs/sheets
            "doc_type": "code",  # For filter compatibility
        }
        
        try:
            self.collection.add(
                documents=[chunk_text],
                metadatas=[metadata],
                ids=[f"code-{code_chunk.id}"]
            )
            logger.debug(f"Generated embedding for code chunk: {code_chunk.full_name}")
            return code_chunk.id
        except Exception as e:
            logger.error(f"Error storing code embedding for {code_chunk.id}: {e}")
            raise
    
    def _format_code_chunk_for_embedding(self, code_chunk: CodeChunk) -> str:
        """
        Format a code chunk for embedding generation.
        Includes signature, docstring, and code content.
        """
        parts = []
        
        # Add chunk type and name
        if code_chunk.chunk_type and code_chunk.chunk_name:
            parts.append(f"{code_chunk.chunk_type.title()}: {code_chunk.chunk_name}")
        
        # Add file path context
        parts.append(f"File: {code_chunk.file_path}")
        
        # Add signature if available
        if code_chunk.signature:
            parts.append(f"Signature: {code_chunk.signature}")
        
        # Add docstring if available
        if code_chunk.docstring:
            parts.append(f"Documentation: {code_chunk.docstring}")
        
        # Add code content (limit to first 1000 chars for very long chunks)
        code_preview = code_chunk.code_content[:1000] if len(code_chunk.code_content) > 1000 else code_chunk.code_content
        parts.append(f"Code:\n{code_preview}")
        
        return "\n\n".join(parts)
    
    def search_similar(
        self,
        query: str,
        n_results: int = 10,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for similar content using semantic similarity
        
        Args:
            query: Search query text
            n_results: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of results with documents, distances, and metadata
        """
        # Generate embedding for query
        query_embedding = self.model.encode([query])[0].tolist()
        
        # Search in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_metadata
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'id': results['ids'][0][i],
                'document': results['documents'][0][i],
                'distance': results['distances'][0][i],
                'metadata': results['metadatas'][0][i]
            })
        
        return formatted_results
    
    def batch_process_documents(
        self,
        db: Session,
        document_ids: Optional[List[str]] = None,
        force_regenerate: bool = False
    ) -> Dict[str, int]:
        """
        Process multiple documents in batch
        
        Args:
            db: Database session
            document_ids: Optional list of document IDs to process (None = all)
            force_regenerate: If True, regenerate even if embeddings exist
            
        Returns:
            Dictionary with processing stats
        """
        # Get documents to process
        query = db.query(Document)
        if document_ids:
            query = query.filter(Document.id.in_(document_ids))
        
        documents = query.all()
        
        stats = {
            'total': len(documents),
            'processed': 0,
            'skipped': 0,
            'failed': 0,
            'total_chunks': 0
        }
        
        logger.info(f"Processing {stats['total']} documents for embeddings")
        
        for doc in documents:
            try:
                chunks = self.store_document_embeddings(
                    db=db,
                    document=doc,
                    force_regenerate=force_regenerate
                )
                
                if chunks > 0:
                    stats['processed'] += 1
                    stats['total_chunks'] += chunks
                else:
                    stats['skipped'] += 1
                    
            except Exception as e:
                logger.error(f"Failed to process document {doc.id}: {e}")
                stats['failed'] += 1
        
        logger.info(f"Batch processing complete: {stats}")
        return stats


# Global instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service instance"""
    global _embedding_service
    
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    
    return _embedding_service

