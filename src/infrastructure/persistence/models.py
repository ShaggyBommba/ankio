from __future__ import annotations

from utils.time import now, utc
from datetime import datetime
from typing import Any
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.entity import AnswerAssessment, Document, Note, OutboxJob, ReviewAttempt, ReviewCard
from domain.value import EventKind, EventTopic, JobStatus
from infrastructure.persistence.database import Base




class OutboxRow(Base):
    """Durable queued work row."""

    __tablename__ = "outbox"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(256),
        unique=True,
        index=True,
    )
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=JobStatus.PENDING.value,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        nullable=False,
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        onupdate=now,
        nullable=False,
    )

    def to_domain(self) -> OutboxJob[dict[str, Any]]:
        """Convert this row into an outbox job."""
        return OutboxJob(
            id=self.id,
            trace_id=self.trace_id,
            idempotency_key=self.idempotency_key,
            topic=EventTopic(self.topic),
            kind=EventKind(self.kind),
            version=self.version,
            payload=self.payload,
            status=JobStatus(self.status),
            attempts=self.attempts,
            max_attempts=self.max_attempts,
            available_at=self.available_at,
            locked_at=self.locked_at,
            done_at=self.done_at,
            last_error=self.last_error,
        )


class DocumentRow(Base):
    """Persisted source document row."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        onupdate=now,
        nullable=False,
    )

    def to_domain(self) -> Document:
        """Convert this row into a document."""
        return Document(
            id=self.id,
            content=self.content,
            created_at=utc(self.created_at),
            updated_at=utc(self.updated_at),
        )


class NoteRow(Base):
    """Persisted note row."""

    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        onupdate=now,
        nullable=False,
    )

    def to_domain(self) -> Note:
        """Convert this row into a note."""
        return Note(
            id=self.id,
            document_id=self.document_id,
            question=self.question,
            answer=self.answer,
            created_at=utc(self.created_at),
            updated_at=utc(self.updated_at),
        )


class ReviewCardRow(Base):
    """Persisted spaced-repetition state for a note."""

    __tablename__ = "review_cards"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    note_id: Mapped[str] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
    )
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        nullable=False,
    )
    interval_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    repetitions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lapses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_reviewed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        onupdate=now,
        nullable=False,
    )

    def to_domain(self) -> ReviewCard:
        """Convert this row into a review card."""
        return ReviewCard(
            id=self.id,
            note_id=self.note_id,
            due_at=utc(self.due_at),
            interval_days=self.interval_days,
            ease_factor=self.ease_factor,
            repetitions=self.repetitions,
            lapses=self.lapses,
            last_reviewed=utc(self.last_reviewed) if self.last_reviewed else None,
            created_at=utc(self.created_at),
            updated_at=utc(self.updated_at),
        )


class ReviewAttemptRow(Base):
    """Persisted assessment for one review attempt."""

    __tablename__ = "review_attempts"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    card_id: Mapped[str] = mapped_column(
        ForeignKey("review_cards.id", ondelete="CASCADE"),
        nullable=False,
    )
    quality: Mapped[int] = mapped_column(Integer, nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
        nullable=False,
    )

    def to_domain(self) -> ReviewAttempt:
        """Convert this row into a review attempt."""
        return ReviewAttempt(
            id=self.id,
            card_id=self.card_id,
            assessment=AnswerAssessment(
                quality=self.quality,
                correct=self.correct,
                feedback=self.feedback,
                confidence=self.confidence,
            ),
            reviewed_at=utc(self.reviewed_at),
        )
