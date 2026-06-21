from __future__ import annotations

import logging
from typing import Callable

from application.adapters.core import DocumentRecord, NoteRecord, UnitOfWork
from application.dto import DocumentDetail, DocumentNoteView, DocumentSummary
from domain.entity import OutboxJob
from utils.time import now, utc

logger = logging.getLogger(__name__)


def preview(content: str, length: int = 180) -> str:
    collapsed = " ".join(content.split())
    if len(collapsed) <= length:
        return collapsed
    return f"{collapsed[: length - 3]}..."


def status(note_count: int, job: OutboxJob[dict[str, object]] | None) -> str:
    if note_count:
        return "ready"
    if job is not None:
        return job.status.value
    return "no_notes"


def cards_for(document: DocumentRecord):
    return [card for note in document.notes for card in note.cards]


def attempts_for(document: DocumentRecord):
    return [attempt for card in cards_for(document) for attempt in card.attempts]


def summary(
    document: DocumentRecord,
    job: OutboxJob[dict[str, object]] | None,
) -> DocumentSummary:
    current = now()
    cards = cards_for(document)
    attempts = attempts_for(document)
    return DocumentSummary(
        id=document.id,
        content_preview=preview(document.content),
        content_length=len(document.content),
        created_at=utc(document.created_at),
        updated_at=utc(document.updated_at),
        notes=len(document.notes),
        cards=len(cards),
        due=sum(1 for card in cards if utc(card.due_at) <= current),
        attempts=len(attempts),
        generation_status=status(len(document.notes), job),
    )


def note_view(note: NoteRecord) -> DocumentNoteView:
    card = note.cards[0] if note.cards else None
    attempts = card.attempts if card else []
    return DocumentNoteView(
        id=note.id,
        question=note.question,
        answer=note.answer,
        card_id=card.id if card else None,
        due_at=utc(card.due_at) if card else None,
        interval_days=card.interval_days if card else None,
        repetitions=card.repetitions if card else 0,
        attempts=len(attempts),
        correct=sum(1 for attempt in attempts if attempt.correct),
    )


def detail(
    document: DocumentRecord,
    job: OutboxJob[dict[str, object]] | None,
) -> DocumentDetail:
    summary_data = summary(document, job)
    return DocumentDetail(
        **summary_data.model_dump(),
        content=document.content,
        note_details=[note_view(note) for note in document.notes],
    )


class ListSummariesUseCase:
    """Return document-level observability for the HTMX dashboard."""

    def __init__(self, factory: Callable[[], UnitOfWork]) -> None:
        self.uow_factory = factory

    def __call__(self) -> list[DocumentSummary]:
        with self.uow_factory() as uow:
            documents = uow.documents.list_with_review_state()
            jobs = {
                document.id: uow.outbox.get_document_job(document.id)
                for document in documents
            }
            summaries = [
                summary(
                    document=document,
                    job=jobs[document.id],
                )
                for document in documents
            ]

        logger.info("Listed document observability documents=%s", len(summaries))
        return summaries


class GetDetailUseCase:
    """Return one document with generated notes and review state."""

    def __init__(self, factory: Callable[[], UnitOfWork]) -> None:
        self.uow_factory = factory

    def __call__(self, document_id: str) -> DocumentDetail | None:
        with self.uow_factory() as uow:
            document = uow.documents.get_with_review_state(document_id)
            if document is None:
                logger.info("Document detail not found document_id=%s", document_id)
                return None

            job = uow.outbox.get_document_job(document_id)
            result = detail(document, job)
            notes = len(document.notes)
            cards = len(cards_for(document))
            attempts = len(attempts_for(document))

        logger.info(
            "Loaded document detail document_id=%s notes=%s cards=%s attempts=%s",
            document_id,
            notes,
            cards,
            attempts,
        )
        return result


class DeleteUseCase:
    """Delete a document and all dependent study state."""

    def __init__(self, factory: Callable[[], UnitOfWork]) -> None:
        self.uow_factory = factory

    def __call__(self, document_id: str) -> DocumentSummary | None:
        with self.uow_factory() as uow:
            document = uow.documents.get_with_review_state(document_id)
            if document is None:
                logger.info(
                    "Document delete skipped; not found document_id=%s", document_id
                )
                return None

            job = uow.outbox.get_document_job(document_id)
            removed = summary(document, job)

            jobs = uow.outbox.remove_document_jobs(document_id)
            uow.documents.remove(document_id)
            uow.commit()

        logger.info(
            "Deleted document document_id=%s notes=%s cards=%s attempts=%s outbox_jobs=%s",
            document_id,
            removed.notes,
            removed.cards,
            removed.attempts,
            jobs,
        )
        return removed
