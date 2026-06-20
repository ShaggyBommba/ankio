from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.entity import Note
from infrastructure.persistence.models import NoteRow


class NoteRepo:
    """SQL-backed Note repository."""

    def __init__(self, session: Session) -> None:
        self.session: Session = session

    def add(self, entity: Note) -> Note:
        row = NoteRow(
            id=entity.id,
            document_id=entity.document_id,
            question=entity.question,
            answer=entity.answer,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self.session.add(row)
        return row.to_domain()

    def get(self, entity_id: str) -> Note | None:
        row = self.session.get(NoteRow, entity_id)
        if row is None:
            return None
        return row.to_domain()

    def list(self, document_id: str | None = None) -> list[Note]:
        query = select(NoteRow)
        if document_id is not None:
            query = query.where(NoteRow.document_id == document_id)
        rows = self.session.execute(query)
        return [row.to_domain() for row in rows.scalars().all()]

    def remove(self, entity_id: str) -> Note | None:
        row = self.session.get(NoteRow, entity_id)
        if row is None:
            return None
        self.session.delete(row)
        return row.to_domain()
