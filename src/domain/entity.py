from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from domain.event import Event, REGISTRY
from domain.value import EventKind, EventTopic, JobStatus
from uuid import uuid4

PayloadT = TypeVar("PayloadT")


class DomainModel(BaseModel):
    """Base class for immutable domain models."""

    model_config = ConfigDict(frozen=True)


class OutboxJob(DomainModel, Generic[PayloadT]):
    """Durable queued work item loaded from the outbox."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    trace_id: str
    idempotency_key: str | None = None
    topic: EventTopic
    kind: EventKind
    payload: PayloadT
    max_attempts: int
    version: int = 1
    status: JobStatus = JobStatus.PENDING
    attempts: int = 0
    available_at: datetime | None = None
    locked_at: datetime | None = None
    done_at: datetime | None = None
    last_error: str | None = None

    @classmethod
    def from_event(
        cls,
        event: Event[PayloadT],
        *,
        max_attempts: int = 3,
        available_at: datetime | None = None,
        idempotency_key: str | None = None,
    ) -> OutboxJob[PayloadT]:
        return cls(
            id=event.id,
            trace_id=event.trace_id,
            idempotency_key=idempotency_key,
            topic=event.topic,
            kind=event.kind,
            version=event.version,
            payload=event.payload,
            max_attempts=max_attempts,
            available_at=available_at,
        )

    def to_event(self) -> Event[PayloadT]:
        """Convert this job back into an event."""
        key = (self.topic, self.kind, self.version)
        cls = REGISTRY.get(key)
        if cls is None:
            raise ValueError(f"No event class registered for {key}")
        return cls(payload=self.payload, id=self.id, trace_id=self.trace_id)


class Document(DomainModel):
    """Represents a document in the system."""

    model_config = ConfigDict(extra="forbid")

    content: str
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Note(DomainModel):
    """Represents a note of a document."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(..., description="ID of the linked document")
    question: str = Field(..., description="The question asked about the document")
    answer: str = Field(..., description="The answer generated for the question")
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ReviewCard(DomainModel):
    note_id: str = Field(..., description="ID of the linked note")

    due_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the card is due for review",
    )
    interval_days: int = Field(default=0, description="Days until next review")
    ease_factor: float = Field(default=2.5, description="Ease factor for scheduling")
    repetitions: int = Field(
        default=0, description="Number of times the card has been reviewed"
    )
    lapses: int = Field(
        default=0, description="Number of times the card has been marked as difficult"
    )
    last_attempted_at: datetime | None = Field(
        default=None, description="Timestamp of the last review"
    )

    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class AnswerAssessment(DomainModel):
    quality: int = Field(ge=0, le=5, description="Quality of the answer")
    correct: bool = Field(..., description="Whether the answer is correct")
    feedback: str = Field(..., description="Feedback provided for the answer")
    confidence: float = Field(ge=0, le=1, description="Confidence level of the answer")


class ReviewAttempt(DomainModel):
    card_id: str = Field(..., description="ID of the reviewed card")
    assessment: AnswerAssessment = Field(
        ..., description="Assessment of the review attempt"
    )
    attempted_at: datetime = Field(default_factory=datetime.now)

    id: str = Field(default_factory=lambda: str(uuid4()))
