"""MCP server entrypoint for agent-driven note and review workflows."""

from __future__ import annotations

from logging import getLogger
from typing import Annotated

from application.app import get_app
from application.dto import GeneratedNote
from domain.entity import AnswerAssessment
from infrastructure.config import get_settings
from mcp.server.fastmcp import FastMCP
from pydantic import Field

logger = getLogger(__name__)


INSTRUCTIONS = """
Use this server to store study material and drive spaced-repetition reviews.

Note generation workflow:
1. Call submit_document with the source text to store the document.
2. Generate factual question/answer notes externally.
3. Call store_generated_notes with the document_id and generated notes.

Review workflow:
1. Call get_next_review_card.
2. Ask the learner the returned question. Do not reveal the answer before they respond.
3. Assess the learner answer externally using quality 0-5.
4. Call record_review_assessment with the card_id and assessment.

This application stores documents, notes, review cards, attempts, and scheduling state.
It does not assess learner answers.
"""


def mcp() -> FastMCP:
    """Build the MCP server and register agent-facing tools."""
    settings = get_settings()
    app = get_app()
    server = FastMCP(
        settings.name,
        instructions=INSTRUCTIONS.strip(),
        host=settings.mcp_host,
        port=settings.mcp_port,
    )

    @server.tool(
        description=(
            "Store a source document for study-note generation. Returns the document "
            "id that generated notes should be attached to."
        )
    )
    def submit_document(content: str) -> dict[str, object]:
        logger.info("MCP submit_document request content_length=%s", len(content))
        document = app.create(content)
        logger.info("MCP submit_document stored document_id=%s", document.id)
        return {"document": document.model_dump(mode="json"), "queued": True}

    @server.tool(
        description=(
            "Store externally generated notes for a document and create review cards. "
            "The operation is idempotent per document; existing notes are returned."
        )
    )
    def store_generated_notes(
        document_id: str,
        notes: list[GeneratedNote],
    ) -> dict[str, object]:
        logger.info(
            "MCP store_generated_notes request document_id=%s notes=%s",
            document_id,
            len(notes),
        )
        stored_notes = app.store_generated_notes(document_id, notes)
        logger.info(
            "MCP store_generated_notes stored document_id=%s notes=%s",
            document_id,
            len(stored_notes),
        )
        return {
            "notes": [note.model_dump(mode="json") for note in stored_notes],
            "count": len(stored_notes),
        }

    @server.tool(
        description=(
            "Return the next due review card. Ask the learner only the question; keep "
            "the answer private until after the learner responds."
        )
    )
    def get_next_review_card() -> dict[str, object | None]:
        logger.info("MCP get_next_review_card request")
        prompt = app.start_review_session()
        if prompt is None:
            logger.info("MCP get_next_review_card returned no due card")
            return {"card": None}
        logger.info(
            "MCP get_next_review_card returned card_id=%s note_id=%s",
            prompt.card_id,
            prompt.note_id,
        )
        return {"card": prompt.model_dump(mode="json")}

    @server.tool(
        description=(
            "Store an externally assessed learner answer and update spaced-repetition "
            "scheduling for the card."
        )
    )
    def record_review_assessment(
        card_id: str,
        quality: Annotated[
            int,
            Field(ge=0, le=5, description="Answer quality from 0 to 5."),
        ],
        correct: bool,
        feedback: str,
        confidence: Annotated[
            float,
            Field(ge=0, le=1, description="Assessment confidence from 0.0 to 1.0."),
        ],
    ) -> dict[str, object]:
        logger.info(
            "MCP record_review_assessment request card_id=%s quality=%s correct=%s",
            card_id,
            quality,
            correct,
        )
        result = app.record_review_assessment(
            card_id=card_id,
            assessment=AnswerAssessment(
                quality=quality,
                correct=correct,
                feedback=feedback,
                confidence=confidence,
            ),
        )
        logger.info(
            "MCP record_review_assessment stored card_id=%s interval_days=%s due_at=%s",
            result.card_id,
            result.interval_days,
            result.due_at.isoformat(),
        )
        return {"review": result.model_dump(mode="json")}

    @server.tool(
        description="Return retention and review-queue metrics for the stored notes."
    )
    def get_retention_overview() -> dict[str, object]:
        logger.info("MCP get_retention_overview request")
        overview = app.review_overview()
        logger.info(
            "MCP get_retention_overview returned notes=%s cards=%s due=%s attempts=%s",
            overview.notes,
            overview.cards,
            overview.due,
            overview.attempts,
        )
        return {"overview": overview.model_dump(mode="json")}

    return server


def main() -> None:
    app = get_app()
    app.start()
    try:
        mcp().run(transport="streamable-http")
    finally:
        app.close()


if __name__ == "__main__":
    main()
