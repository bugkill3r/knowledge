"""API v1 routes"""
from fastapi import APIRouter

from app.api.v1 import documents, imports, search, code, collections, graph, review, cursor, config

router = APIRouter()

# Include sub-routers
router.include_router(config.router, tags=["config"])
router.include_router(documents.router, prefix="/documents", tags=["documents"])
router.include_router(imports.router, prefix="/imports", tags=["imports"])
router.include_router(search.router, tags=["search"])
router.include_router(code.router, tags=["code"])
router.include_router(collections.router, tags=["collections"])
router.include_router(graph.router, tags=["graph"])
router.include_router(review.router, prefix="/review", tags=["review"])
router.include_router(cursor.router, prefix="/cursor", tags=["cursor"])

