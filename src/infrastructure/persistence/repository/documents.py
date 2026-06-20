from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.entity import Document
from infrastructure.persistence.models import DocumentRow


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

    def remove(self, entity_id: str) -> Document | None:
        row = self.session.get(DocumentRow, entity_id)
        if row is None:
            return None
        self.session.delete(row)
        return row.to_domain()
