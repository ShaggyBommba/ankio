"""HTMX routes for document intake, inspection, deletion, and retention overview."""

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
            "documents": app.documents(),
            "document": None,
            "overview": app.review_overview(),
        },
    )


@routes.post("/notes", response_class=HTMLResponse)
def submit_document(
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
                "message": None,
                "documents": app.documents(),
                "document": None,
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
            "documents": app.documents(),
            "document": app.document(document.id),
            "overview": app.review_overview(),
        },
    )


@routes.get("/documents", response_class=HTMLResponse)
def documents(request: Request, app: App = Depends(get_app)) -> HTMLResponse:
    logger.info("HTMX documents fragment request")
    return templates.TemplateResponse(
        request,
        "partials/documents_panel.html",
        {"documents": app.documents()},
    )


@routes.get("/documents/{document_id}", response_class=HTMLResponse)
def document_detail(
    request: Request,
    document_id: str,
    app: App = Depends(get_app),
) -> HTMLResponse:
    logger.info("HTMX document detail request document_id=%s", document_id)
    document = app.document(document_id)
    status_code = 200 if document is not None else 404
    return templates.TemplateResponse(
        request,
        "partials/document_detail.html",
        {"document": document},
        status_code=status_code,
    )


@routes.delete("/documents/{document_id}", response_class=HTMLResponse)
def delete_document(
    request: Request,
    document_id: str,
    app: App = Depends(get_app),
) -> HTMLResponse:
    logger.info("HTMX document delete request document_id=%s", document_id)
    deleted = app.delete_document(document_id)
    if deleted is None:
        error = f"Document {document_id[:8]} was not found."
        message = None
    else:
        error = None
        message = (
            f"Document {deleted.id[:8]} deleted with {deleted.notes} note(s), "
            f"{deleted.cards} card(s), and {deleted.attempts} attempt(s)."
        )

    return templates.TemplateResponse(
        request,
        "partials/delete_result.html",
        {
            "error": error,
            "message": message,
            "documents": app.documents(),
            "document": None,
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
