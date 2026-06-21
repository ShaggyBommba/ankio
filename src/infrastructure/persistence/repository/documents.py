from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from domain.entity import Document
from infrastructure.persistence.models import DocumentRow, NoteRow, ReviewCardRow


class DocumentRepo:
    """SQL-backed document repository."""

    def __init__(self, session: Session) -> None:
        self.session: Session = session

    def add(self, entity: Document) -> Document:
        row = DocumentRow(
            id=entity.id,
            content=entity.content,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self.session.add(row)
        return row.to_domain()

    def get(self, entity_id: str) -> Document | None:
        row = self.session.get(DocumentRow, entity_id)
        if row is None:
            return None
        return row.to_domain()

    def list(self) -> list[Document]:
        rows = self.session.execute(select(DocumentRow))
        return [row.to_domain() for row in rows.scalars().all()]

    def get_with_review_state(self, entity_id: str) -> DocumentRow | None:
        return self.session.scalars(
            select(DocumentRow)
            .where(DocumentRow.id == entity_id)
            .options(
                selectinload(DocumentRow.notes)
                .selectinload(NoteRow.cards)
                .selectinload(ReviewCardRow.attempts)
            )
        ).one_or_none()

    def list_with_review_state(self) -> list[DocumentRow]:
        rows = self.session.scalars(
            select(DocumentRow)
            .options(
                selectinload(DocumentRow.notes)
                .selectinload(NoteRow.cards)
                .selectinload(ReviewCardRow.attempts)
            )
            .order_by(DocumentRow.created_at.desc())
        )
        return list(rows.all())

    def remove(self, entity_id: str) -> Document | None:
        row = self.get_with_review_state(entity_id)
        if row is None:
            return None
        document = row.to_domain()
        self.session.delete(row)
        return document
