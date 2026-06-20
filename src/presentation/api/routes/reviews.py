"""Review API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from application.app import App, get_app
from application.dto import ReviewAssessmentRequest
from domain.entity import AnswerAssessment

logger = logging.getLogger(__name__)

routes = APIRouter(prefix="/reviews", tags=["reviews"])


@routes.post("/session")
def start_review_session(app: App = Depends(get_app)) -> dict[str, dict[str, str] | None]:
    """Start a review session with the next due card."""
    logger.info("API start review session request")
    prompt = app.start_review_session()
    if prompt is None:
        logger.info("API start review session returned no due card")
        return {"card": None}
    logger.info(
        "API start review session returned card_id=%s note_id=%s",
        prompt.card_id,
        prompt.note_id,
    )
    return {"card": prompt.model_dump(mode="json")}


@routes.post("/{card_id}/assessment")
def record_review_assessment(
    card_id: str,
    request: ReviewAssessmentRequest,
    app: App = Depends(get_app),
) -> dict[str, dict[str, object]]:
    """Record an externally produced assessment and update the card schedule."""
    logger.info(
        "API record review assessment card_id=%s quality=%s correct=%s",
        card_id,
        request.quality,
        request.correct,
    )
    try:
        result = app.record_review_assessment(
            card_id,
            AnswerAssessment(**request.model_dump()),
        )
    except ValueError as exc:
        logger.warning(
            "API review assessment failed card_id=%s error=%s",
            card_id,
            exc,
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"review": result.model_dump(mode="json")}


@routes.get("/overview")
def review_overview(app: App = Depends(get_app)) -> dict[str, dict[str, object]]:
    """Return retention and review queue metrics."""
    logger.info("API review overview request")
    overview = app.review_overview()
    logger.info(
        "API review overview returned notes=%s cards=%s due=%s attempts=%s",
        overview.notes,
        overview.review_cards,
        overview.due_cards,
        overview.attempts,
    )
    return {"overview": overview.model_dump(mode="json")}
