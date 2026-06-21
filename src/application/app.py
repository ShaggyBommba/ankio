from __future__ import annotations

from functools import lru_cache
from logging import getLogger

from infrastructure.persistence.uow import SqlUnitOfWork
from infrastructure.config import Settings, get_settings
from infrastructure.observability.logger import LoggingService
from infrastructure.persistence.database import SqlDatabase
from application.dto import (
    DocumentDetail,
    DocumentSummary,
    GeneratedNote,
    RetentionOverview,
    ReviewAssessmentResult,
    ReviewPrompt,
)
from application.services.documents import (
    DeleteUseCase,
    GetDetailUseCase,
    ListSummariesUseCase,
)
from application.services.outbox import EventDispatcher, OutboxRunner
from application.services.notes import (
    CreateDocumentUseCase,
    GenerateNotesHandler,
    NoteGenerator,
    StoreGeneratedNotesUseCase,
)
from application.services.reviews import (
    OverviewUseCase,
    RecordAssessmentUseCase,
    ScheduleCardUseCase,
    StartSessionUseCase,
)
from domain.entity import AnswerAssessment, Document, Note
from domain.event import DocumentCreated
from asyncio import sleep

logger = getLogger(__name__)


class App:
    """Application facade used by entrypoints."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        logger.info(
            "Initializing application name=%s version=%s env=%s",
            settings.name,
            settings.version,
            settings.env,
        )
        self.database = SqlDatabase(settings.database)
        self.database.create_all()
        self.uow_factory = lambda: SqlUnitOfWork(
            self.database.sessions(),
            self.settings.outbox,
        )
        self.create_document_use_case = CreateDocumentUseCase(
            factory=self.uow_factory,
        )
        self.store_generated_notes_use_case = StoreGeneratedNotesUseCase(
            factory=self.uow_factory,
        )
        self.list_documents_use_case = ListSummariesUseCase(factory=self.uow_factory)
        self.get_document_use_case = GetDetailUseCase(factory=self.uow_factory)
        self.delete_document_use_case = DeleteUseCase(factory=self.uow_factory)
        self.generate_notes_handler = GenerateNotesHandler(
            factory=self.uow_factory,
            generator=NoteGenerator(model="gpt-5.4-mini"),
        )
        self.start_review_session_use_case = StartSessionUseCase(
            factory=self.uow_factory,
        )
        self.record_review_assessment_use_case = RecordAssessmentUseCase(
            factory=self.uow_factory,
            scheduler=ScheduleCardUseCase(),
        )
        self.review_overview_use_case = OverviewUseCase(factory=self.uow_factory)

        self.dispatcher = EventDispatcher()
        self.dispatcher.register(DocumentCreated, self.generate_notes_handler)
        self.runner = OutboxRunner(
            dispatcher=self.dispatcher,
            events=(DocumentCreated,),
            limit=self.settings.worker_batch_limit,
            factory=self.uow_factory,
        )
        logger.info(
            "Application initialized database_provider=%s worker_batch_limit=%s",
            settings.database.provider,
            settings.worker_batch_limit,
        )

    @property
    def name(self) -> str:
        return self.settings.name

    @property
    def version(self) -> str:
        return self.settings.version

    @property
    def healthy(self) -> bool:
        return True

    def start(self) -> None:
        """Start the application."""
        logger.info(f"Starting {self.name} v{self.version}...")

    def close(self) -> None:
        """Close the application."""
        logger.info(f"Closing {self.name}...")

    def create(self, content: str) -> Document:
        """Store a document and queue note generation."""
        logger.info("Create document request received content_length=%s", len(content))
        return self.create_document_use_case(content)

    def store_generated_notes(
        self,
        document_id: str,
        generated_notes: list[GeneratedNote],
    ) -> list[Note]:
        """Store generated notes and create review cards for a document."""
        logger.info(
            "Store generated notes request received document_id=%s notes=%s",
            document_id,
            len(generated_notes),
        )
        return self.store_generated_notes_use_case(document_id, generated_notes)

    def documents(self) -> list[DocumentSummary]:
        """Return document-level observability summaries."""
        logger.debug("Document list request received")
        return self.list_documents_use_case()

    def document(self, document_id: str) -> DocumentDetail | None:
        """Return one document with generated notes and review state."""
        logger.debug("Document detail request received document_id=%s", document_id)
        return self.get_document_use_case(document_id)

    def delete_document(self, document_id: str) -> DocumentSummary | None:
        """Delete a document and all dependent study state."""
        logger.info("Delete document request received document_id=%s", document_id)
        return self.delete_document_use_case(document_id)

    def start_review_session(self) -> ReviewPrompt | None:
        """Start a review session with the next due card."""
        logger.info("Start review session request received")
        return self.start_review_session_use_case()

    def record_review_assessment(
        self,
        card_id: str,
        assessment: AnswerAssessment,
    ) -> ReviewAssessmentResult:
        """Record an external review assessment and update scheduling."""
        logger.info(
            "Record review assessment request received card_id=%s quality=%s correct=%s",
            card_id,
            assessment.quality,
            assessment.correct,
        )
        return self.record_review_assessment_use_case(card_id, assessment)

    def review_overview(self) -> RetentionOverview:
        """Return review retention and queue metrics."""
        logger.debug("Review overview request received")
        return self.review_overview_use_case()

    async def daemon(self) -> None:
        """Run background tasks."""
        while True:
            logger.debug("Polling runner for background tasks...")
            await self.runner.poll()
            await sleep(self.settings.worker_poll_interval)


@lru_cache(maxsize=1)
def get_app() -> App:
    """Build the application from concrete infrastructure adapters."""
    settings = get_settings()
    LoggingService.setup(settings.logging)
    return App(settings=settings)
