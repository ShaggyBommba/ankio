from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from domain.entity import ReviewAttempt, ReviewCard
from infrastructure.persistence.models import ReviewAttemptRow, ReviewCardRow


class ReviewCardRepo:
    """SQL-backed review card repository."""

    def __init__(self, session: Session) -> None:
        self.session: Session = session

    def add(self, entity: ReviewCard) -> ReviewCard:
        row = ReviewCardRow(
            id=entity.id,
            note_id=entity.note_id,
            due_at=entity.due_at,
            interval_days=entity.interval_days,
            ease_factor=entity.ease_factor,
            repetitions=entity.repetitions,
            lapses=entity.lapses,
            last_reviewed=entity.last_reviewed,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self.session.add(row)
        return row.to_domain()

    def get(self, entity_id: str) -> ReviewCard | None:
        row = self.session.get(ReviewCardRow, entity_id)
        if row is None:
            return None
        return row.to_domain()

    def list(self) -> list[ReviewCard]:
        rows = self.session.execute(select(ReviewCardRow))
        return [row.to_domain() for row in rows.scalars().all()]

    def next_due(self, due_at: datetime) -> ReviewCard | None:
        row = self.session.execute(
            select(ReviewCardRow)
            .where(ReviewCardRow.due_at <= due_at)
            .order_by(ReviewCardRow.due_at.asc())
            .limit(1)
        ).scalar_one_or_none()
        if row is None:
            return None
        return row.to_domain()

    def update(self, entity: ReviewCard) -> ReviewCard:
        row = self.session.get(ReviewCardRow, entity.id)
        if row is None:
            raise ValueError(f"ReviewCard not found: {entity.id}")

        row.note_id = entity.note_id
        row.due_at = entity.due_at
        row.interval_days = entity.interval_days
        row.ease_factor = entity.ease_factor
        row.repetitions = entity.repetitions
        row.lapses = entity.lapses
        row.last_reviewed = entity.last_reviewed
        row.created_at = entity.created_at
        row.updated_at = entity.updated_at
        return row.to_domain()

    def remove(self, entity_id: str) -> ReviewCard | None:
        row = self.session.get(ReviewCardRow, entity_id)
        if row is None:
            return None
        self.session.delete(row)
        return row.to_domain()


class ReviewAttemptRepo:
    """SQL-backed review attempt repository."""

    def __init__(self, session: Session) -> None:
        self.session: Session = session

    def add(self, entity: ReviewAttempt) -> ReviewAttempt:
        row = ReviewAttemptRow(
            id=entity.id,
            card_id=entity.card_id,
            quality=entity.assessment.quality,
            correct=entity.assessment.correct,
            feedback=entity.assessment.feedback,
            confidence=entity.assessment.confidence,
            reviewed_at=entity.reviewed_at,
        )
        self.session.add(row)
        return row.to_domain()

    def get(self, entity_id: str) -> ReviewAttempt | None:
        row = self.session.get(ReviewAttemptRow, entity_id)
        if row is None:
            return None
        return row.to_domain()

    def list(self, card_id: str | None = None) -> list[ReviewAttempt]:
        query = select(ReviewAttemptRow)
        if card_id is not None:
            query = query.where(ReviewAttemptRow.card_id == card_id)
        rows = self.session.execute(query)
        return [row.to_domain() for row in rows.scalars().all()]

    def remove(self, entity_id: str) -> ReviewAttempt | None:
        row = self.session.get(ReviewAttemptRow, entity_id)
        if row is None:
            return None
        self.session.delete(row)
        return row.to_domain()
