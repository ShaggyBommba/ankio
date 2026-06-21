"""System API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from application.app import App, get_app

logger = logging.getLogger(__name__)

routes = APIRouter(tags=["notes"])


@routes.get("/")
def submit_document(content: str, app: App = Depends(get_app)) -> dict[str, object]:
    """Store a document and queue note generation."""
    logger.info("API document create request content_length=%s", len(content))
    document = app.create(content)
    logger.info("API document create queued document_id=%s", document.id)
    return {"document": document.model_dump(mode="json"), "queued": True}
