from __future__ import annotations

from datetime import datetime
from types import TracebackType
from typing import Any, Protocol, TypeVar, runtime_checkable
from domain.event import Event
from domain.entity import Document, Note, OutboxJob, ReviewAttempt, ReviewCard
from domain.value import EventKind, EventTopic, JobStatus

EntityT = TypeVar("EntityT")
SearchEntityT = TypeVar("SearchEntityT", contravariant=True)
SearchResultT = TypeVar("SearchResultT")


@runtime_checkable
class CrudRepo(Protocol[EntityT]):
    """Persists domain entities with basic CRUD operations."""

    def add(self, entity: EntityT, /) -> EntityT:
        """Insert an entity."""
        ...

    def get(self, entity_id: str, /) -> EntityT | None:
        """Read one entity by id."""
        ...

    def list(self, *args, **kwargs: Any) -> list[EntityT]:
        """Read all entities."""
        ...

    def remove(self, entity_id: str, /) -> EntityT | None:
        """Remove one entity by id. Return the removed entity or None if not found."""
        ...


@runtime_checkable
class OutboxRepo(Protocol):
    """Persists durable queued work."""

    def append(
        self,
        topic: EventTopic,
        kind: EventKind,
        payload: dict[str, Any] | object,
        version: int = 1,
        max_attempts: int | None = None,
        idempotency_key: str | None = None,
    ) -> OutboxJob:
        """Insert or revive one idempotent outbox job."""
        ...

    def due(
        self, topic: EventTopic, kind: EventKind, version: int, limit: int
    ) -> list[OutboxJob]:
        """Read ready pending jobs without claiming them."""
        ...

    def claim(
        self, topic: EventTopic, kind: EventKind, version: int, limit: int
    ) -> list[OutboxJob]:
        """Claim ready pending jobs for processing."""
        ...

    def mark(
        self,
        job_id: str,
        status: JobStatus,
        error: str | None = None,
        retry: bool = True,
    ) -> None:
        """Move one claimed job to its next durable state."""
        ...


@runtime_checkable
class ReviewCardRepo(CrudRepo[ReviewCard], Protocol):
    """Persists review cards and reads due cards."""

    def next_due(self, due_at: datetime, /) -> ReviewCard | None:
        """Read the earliest review card due at or before a timestamp."""
        ...

    def update(self, entity: ReviewCard, /) -> ReviewCard:
        """Persist changed review-card scheduling state."""
        ...


@runtime_checkable
class UnitOfWork(Protocol):
    """Coordinates repositories that share one transactional session."""

    documents: CrudRepo[Document]
    notes: CrudRepo[Note]
    review_cards: ReviewCardRepo
    review_attempts: CrudRepo[ReviewAttempt]
    outbox: OutboxRepo

    def __enter__(self) -> UnitOfWork:
        """Open one transactional session and expose repositories."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Rollback uncommitted work and close the session."""
        ...

    def commit(self) -> None:
        """Commit all staged repository changes atomically."""
        ...

    def rollback(self) -> None:
        """Rollback all staged repository changes."""
        ...


@runtime_checkable
class Handler[PayloadT](Protocol):
    async def __call__(self, event: Event[PayloadT]) -> None: ...


@runtime_checkable
class Dispatcher(Protocol):
    def register[PayloadT](
        self,
        cls: type[Event[PayloadT]],
        handler: Handler[PayloadT],
    ) -> None: ...

    async def dispatch(self, event: Event[Any]) -> None: ...


@runtime_checkable
class Runner(Protocol):
    async def poll(self) -> None: ...
