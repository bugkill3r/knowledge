"""Graph service for building knowledge graph visualizations"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from app.models.document import Document
from app.models.code_repository import CodeRepository
from app.models.spreadsheet import SpreadsheetData
from app.models.collection import Collection
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class GraphService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()
    
    def build_knowledge_graph(
        self,
        collection_id: Optional[str] = None,
        include_docs: bool = True,
        include_code: bool = True,
        include_sheets: bool = True
    ) -> Dict:
        """Build the complete knowledge graph with nodes and edges"""
        nodes = []
        edges = []
        
        # Get filtered items if collection is specified
        if collection_id:
            collection = self.db.query(Collection).filter_by(id=collection_id).first()
            if not collection:
                return {"nodes": [], "edges": []}
            
            documents = collection.documents if include_docs else []
            repositories = collection.repositories if include_code else []
        else:
            documents = self.db.query(Document).all() if include_docs else []
            repositories = self.db.query(CodeRepository).all() if include_code else []
        
        # Add document nodes
        for doc in documents:
            nodes.append({
                "id": f"doc-{doc.id}",
                "type": "document",
                "data": {
                    "label": doc.title,
                    "doc_type": doc.doc_type.value if doc.doc_type else "doc",
                    "source_url": doc.source_url,
                    "vault_path": doc.vault_path,
                    "author": doc.author,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "entity_type": "document"
                },
                "position": {"x": 0, "y": 0}  # Will be calculated by layout algorithm
            })
            
            # Add edges for spreadsheets linked to this document
            if include_sheets:
                sheets = self.db.query(SpreadsheetData).filter_by(document_id=doc.id).all()
                for sheet in sheets:
                    # Add sheet node
                    nodes.append({
                        "id": f"sheet-{sheet.id}",
                        "type": "spreadsheet",
                        "data": {
                            "label": sheet.sheet_title or "Untitled Sheet",
                            "parent_doc": doc.title,
                            "sheet_url": sheet.sheet_url,
                            "entity_type": "spreadsheet"
                        },
                        "position": {"x": 0, "y": 0}
                    })
                    
                    # Add edge from document to sheet
                    edges.append({
                        "id": f"edge-doc-{doc.id}-sheet-{sheet.id}",
                        "source": f"doc-{doc.id}",
                        "target": f"sheet-{sheet.id}",
                        "type": "has_sheet",
                        "label": "contains",
                        "animated": False
                    })
        
        # Add repository nodes
        for repo in repositories:
            nodes.append({
                "id": f"repo-{repo.id}",
                "type": "repository",
                "data": {
                    "label": repo.name,
                    "language": repo.primary_language,
                    "total_files": repo.total_files,
                    "total_functions": repo.total_functions,
                    "lines_of_code": repo.lines_of_code,
                    "local_path": repo.local_path,
                    "entity_type": "repository"
                },
                "position": {"x": 0, "y": 0}
            })
        
        # Add semantic relationships between docs and code using embeddings
        logger.info("Finding semantic relationships between documents and code...")
        semantic_edges = self._find_semantic_relationships(documents, repositories)
        edges.extend(semantic_edges)
        logger.info(f"Added {len(semantic_edges)} semantic relationships")
        
        # Skip collection node - it clutters the view
        # The semantic relationships are more valuable
        
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "document_count": len([n for n in nodes if n["type"] == "document"]),
                "repository_count": len([n for n in nodes if n["type"] == "repository"]),
                "spreadsheet_count": len([n for n in nodes if n["type"] == "spreadsheet"]),
                "collection_count": len([n for n in nodes if n["type"] == "collection"])
            }
        }
    
    def _find_semantic_relationships(
        self,
        documents: List[Document],
        repositories: List[CodeRepository],
        min_confidence: float = 0.3  # Lower threshold since cross-modal similarity is lower
    ) -> List[Dict]:
        """Find semantic relationships between documents and code using embeddings"""
        edges = []
        seen_edges = set()  # Track edge pairs to avoid duplicates
        
        # For each document, find related code repositories
        for i, doc in enumerate(documents):
            try:
                # Use document title and summary as query
                query_text = f"{doc.title}"
                if doc.summary:
                    query_text += f" {doc.summary[:200]}"
                
                # Search for similar code chunks
                # Note: We can't filter by repository_id existence in ChromaDB directly
                # So we search all and filter results
                # Need MANY results since doc-to-doc similarity is much higher than doc-to-code
                all_results = self.embedding_service.search_similar(
                    query=query_text,
                    n_results=500  # Get many more to find code results mixed in
                )
                
                # Filter to only code results (those with repository_id)
                results = [r for r in all_results if r.get('metadata', {}).get('repository_id')][:10]
                
                # Group by repository and calculate confidence
                repo_scores = {}
                for result in results:
                    repo_id = result.get('metadata', {}).get('repository_id')
                    if not repo_id:
                        continue
                    
                    # ChromaDB returns squared L2 distance, which can be > 1
                    # Lower distance = more similar
                    # For cosine similarity embeddings, distance is typically 0-2
                    distance = result.get('distance', 2.0)
                    
                    # Convert distance to similarity score (inverse relationship)
                    # Distance of 0 = perfect match (similarity 1.0)
                    # Distance of 2 = opposite (similarity 0.0)
                    similarity = max(0, 1 - (distance / 2.0))
                    
                    if similarity < min_confidence:
                        continue
                    
                    if repo_id not in repo_scores:
                        repo_scores[repo_id] = []
                    repo_scores[repo_id].append(similarity)
                
                # Create edges for top related repositories
                for repo_id, scores in repo_scores.items():
                    # Check if this repo is in our filtered list
                    if not any(r.id == repo_id for r in repositories):
                        continue
                    
                    # Check for duplicates
                    edge_key = (doc.id, repo_id)
                    if edge_key in seen_edges:
                        continue
                    seen_edges.add(edge_key)
                    
                    avg_confidence = sum(scores) / len(scores)
                    
                    edges.append({
                        "id": f"edge-semantic-doc-{doc.id}-repo-{repo_id}",
                        "source": f"doc-{doc.id}",
                        "target": f"repo-{repo_id}",
                        "type": "related",
                        "label": f"{int(avg_confidence * 100)}%",
                        "animated": True,
                        "confidence": avg_confidence
                    })
                    
            except Exception as e:
                logger.warning(f"Error finding relationships for doc {doc.id}: {e}")
                continue
        
        # Also find relationships between documents
        for i, doc1 in enumerate(documents):
            try:
                query_text = f"{doc1.title}"
                if doc1.summary:
                    query_text += f" {doc1.summary[:200]}"
                
                # Search for similar documents
                results = self.embedding_service.search_similar(
                    query=query_text,
                    n_results=10  # Get more to account for filtering
                )
                
                # Filter to only document results (those with document_id but not repository_id)
                results = [r for r in results if r.get('metadata', {}).get('document_id') and not r.get('metadata', {}).get('repository_id')][:5]
                
                for result in results:
                    doc2_id = result.get('metadata', {}).get('document_id')
                    if not doc2_id or doc2_id == doc1.id:
                        continue
                    
                    # Check if this doc is in our filtered list
                    if not any(d.id == doc2_id for d in documents):
                        continue
                    
                    # Convert distance to similarity (same as above)
                    distance = result.get('distance', 2.0)
                    similarity = max(0, 1 - (distance / 2.0))
                    
                    if similarity < min_confidence:
                        continue
                    
                    # Avoid duplicate edges using normalized pair
                    edge_key = tuple(sorted([doc1.id, doc2_id]))
                    if edge_key in seen_edges:
                        continue
                    seen_edges.add(edge_key)
                    
                    edges.append({
                        "id": f"edge-semantic-doc-{doc1.id}-doc-{doc2_id}",
                        "source": f"doc-{doc1.id}",
                        "target": f"doc-{doc2_id}",
                        "type": "related",
                        "label": f"{int(similarity * 100)}%",
                        "animated": False,
                        "confidence": similarity
                    })
                        
            except Exception as e:
                logger.warning(f"Error finding doc relationships for {doc1.id}: {e}")
                continue
        
        # Also find relationships between code repositories
        for i, repo1 in enumerate(repositories):
            try:
                # Use repository name as query
                query_text = repo1.name
                
                # Search for similar code
                all_results = self.embedding_service.search_similar(
                    query=query_text,
                    n_results=100
                )
                
                # Filter to only code results
                results = [r for r in all_results if r.get('metadata', {}).get('repository_id')][:10]
                
                # Group by repository
                repo_scores = {}
                for result in results:
                    repo2_id = result.get('metadata', {}).get('repository_id')
                    if not repo2_id or repo2_id == repo1.id:
                        continue
                    
                    # Check if this repo is in our filtered list
                    if not any(r.id == repo2_id for r in repositories):
                        continue
                    
                    distance = result.get('distance', 2.0)
                    similarity = max(0, 1 - (distance / 2.0))
                    
                    if similarity < min_confidence:
                        continue
                    
                    if repo2_id not in repo_scores:
                        repo_scores[repo2_id] = []
                    repo_scores[repo2_id].append(similarity)
                
                # Create edges for related repositories
                for repo2_id, scores in repo_scores.items():
                    # Avoid duplicates using normalized pair
                    edge_key = tuple(sorted([repo1.id, repo2_id]))
                    if edge_key in seen_edges:
                        continue
                    seen_edges.add(edge_key)
                    
                    avg_confidence = sum(scores) / len(scores)
                    
                    edges.append({
                        "id": f"edge-semantic-repo-{repo1.id}-repo-{repo2_id}",
                        "source": f"repo-{repo1.id}",
                        "target": f"repo-{repo2_id}",
                        "type": "related",
                        "label": f"{int(avg_confidence * 100)}%",
                        "animated": False,
                        "confidence": avg_confidence
                    })
                    
            except Exception as e:
                logger.warning(f"Error finding repo relationships for {repo1.id}: {e}")
                continue
        
        return edges
    
    def get_node_details(self, node_id: str, node_type: str) -> Optional[Dict]:
        """Get detailed information about a specific node"""
        entity_id = node_id.split('-', 1)[1] if '-' in node_id else node_id
        
        if node_type == "document":
            doc = self.db.query(Document).filter_by(id=entity_id).first()
            if doc:
                return {
                    "id": doc.id,
                    "title": doc.title,
                    "doc_type": doc.doc_type.value if doc.doc_type else None,
                    "source_url": doc.source_url,
                    "vault_path": doc.vault_path,
                    "author": doc.author,
                    "summary": doc.summary,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None
                }
        
        elif node_type == "repository":
            repo = self.db.query(CodeRepository).filter_by(id=entity_id).first()
            if repo:
                return {
                    "id": repo.id,
                    "name": repo.name,
                    "language": repo.primary_language,
                    "local_path": repo.local_path,
                    "total_files": repo.total_files,
                    "total_functions": repo.total_functions,
                    "total_classes": repo.total_classes,
                    "lines_of_code": repo.lines_of_code,
                    "last_synced": repo.last_synced.isoformat() if repo.last_synced else None
                }
        
        elif node_type == "spreadsheet":
            sheet = self.db.query(SpreadsheetData).filter_by(id=entity_id).first()
            if sheet:
                return {
                    "id": sheet.id,
                    "sheet_title": sheet.sheet_title,
                    "document_id": sheet.document_id,
                    "sheet_url": sheet.sheet_url,
                    "sheet_id": sheet.sheet_id
                }
        
        return None

