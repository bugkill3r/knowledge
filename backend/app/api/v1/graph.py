"""Graph API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.services.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/knowledge-graph")
async def get_knowledge_graph(
    collection_id: Optional[str] = Query(None, description="Filter by collection ID"),
    include_docs: bool = Query(True, description="Include documents"),
    include_code: bool = Query(True, description="Include code repositories"),
    include_sheets: bool = Query(True, description="Include spreadsheets"),
    db: Session = Depends(get_db)
):
    """
    Get the knowledge graph with nodes and edges.
    
    Returns a graph structure compatible with ReactFlow:
    - nodes: Array of node objects with id, type, data, and position
    - edges: Array of edge objects with id, source, target, and type
    - stats: Summary statistics about the graph
    """
    service = GraphService(db)
    
    try:
        graph = service.build_knowledge_graph(
            collection_id=collection_id,
            include_docs=include_docs,
            include_code=include_code,
            include_sheets=include_sheets
        )
        return graph
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build graph: {str(e)}")


@router.get("/node/{node_type}/{node_id}")
async def get_node_details(
    node_type: str,
    node_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific node.
    
    Args:
        node_type: Type of node (document, repository, spreadsheet, collection)
        node_id: ID of the node (can include type prefix like 'doc-uuid')
    """
    service = GraphService(db)
    
    try:
        details = service.get_node_details(node_id, node_type)
        if not details:
            raise HTTPException(status_code=404, detail="Node not found")
        return details
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get node details: {str(e)}")

