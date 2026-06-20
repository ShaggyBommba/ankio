"""HTMX routes for document intake and retention overview."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from application.app import App, get_app

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

routes = APIRouter(tags=["reviews"])


@routes.get("/", response_class=HTMLResponse)
def index(request: Request, app: App = Depends(get_app)) -> HTMLResponse:
    logger.info("HTMX index request")
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "notes": [],
            "overview": app.review_overview(),
        },
    )


@routes.post("/notes", response_class=HTMLResponse)
def create_notes(
    request: Request,
    content: str = Form(...),
    app: App = Depends(get_app),
) -> HTMLResponse:
    if not content.strip():
        logger.info("HTMX document create rejected because content is empty")
        return templates.TemplateResponse(
            request,
            "partials/create_result.html",
            {
                "error": "Document content is required.",
                "notes": [],
                "overview": app.review_overview(),
            },
        )

    logger.info("HTMX document create request content_length=%s", len(content.strip()))
    document = app.create(content.strip())
    logger.info("HTMX document create queued document_id=%s", document.id)
    return templates.TemplateResponse(
        request,
        "partials/create_result.html",
        {
            "error": None,
            "message": f"Document {document.id[:8]} stored. Note generation is queued.",
            "notes": [],
            "overview": app.review_overview(),
        },
    )


@routes.get("/overview", response_class=HTMLResponse)
def overview(request: Request, app: App = Depends(get_app)) -> HTMLResponse:
    logger.info("HTMX overview fragment request")
    return templates.TemplateResponse(
        request,
        "partials/overview_panel.html",
        {"overview": app.review_overview()},
    )
