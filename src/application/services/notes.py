from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from application.adapters.core import UnitOfWork
from application.dto import GeneratedNote, GeneratedNotes
from domain.entity import Document, Note, ReviewCard
from domain.event import DocumentCreated
from utils.time import now

logger = logging.getLogger(__name__)


PROMPT = """
Create study notes from the document below.

Each note must contain:
- one clear question
- one factual answer
- no information that is not supported by the document

Document:
{content}
"""


class NoteGenerator:
    def __init__(self, model: str) -> None:
        self.model = model

    def __call__(self, content: str) -> GeneratedNotes:
        logger.info(
            "Generating notes with model=%s content_length=%s",
            self.model,
            len(content),
        )
        schema = GeneratedNotes.model_json_schema()
        with tempfile.TemporaryDirectory() as tmp:
            schema_path = Path(tmp) / "notes.schema.json"
            output_path = Path(tmp) / "output.jsonl"

            schema_path.write_text(json.dumps(schema))

            cmd = [
                "codex",
                "exec",
                PROMPT.format(content=content),
                "--output-schema",
                str(schema_path),
                "-o",
                str(output_path),
                "--model",
                self.model,
            ]

            result = subprocess.run(
                cmd,
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                logger.error(
                    "Note generation failed model=%s exit_code=%s",
                    self.model,
                    result.returncode,
                )
                raise RuntimeError(
                    f"Codex failed with exit code {result.returncode}:\n"
                    f"STDOUT:\n{result.stdout}\n\n"
                    f"STDERR:\n{result.stderr}"
                )

            raw = output_path.read_text(encoding="utf-8")
            generated = GeneratedNotes.model_validate_json(raw)
            logger.info(
                "Generated %s note(s) with model=%s",
                len(generated.notes),
                self.model,
            )
            return generated


class CreateDocumentUseCase:
    def __init__(
        self,
        factory: Callable[[], UnitOfWork],
    ) -> None:
        self.uow_factory = factory

    def __call__(self, content: str) -> Document:
        with self.uow_factory() as uow:
            document = Document(content=content)
            uow.documents.add(document)
            uow.outbox.append(
                DocumentCreated.topic,
                DocumentCreated.kind,
                {"document_id": document.id},
                version=DocumentCreated.version,
                idempotency_key=f"document:{document.id}:notes",
            )
            uow.commit()
            logger.info(
                "Stored document and queued note generation document_id=%s content_length=%s",
                document.id,
                len(content),
            )
            return document


class StoreGeneratedNotesUseCase:
    """Persist externally or internally generated notes for a document."""

    def __init__(
        self,
        factory: Callable[[], UnitOfWork],
    ) -> None:
        self.uow_factory = factory

    def __call__(
        self,
        document_id: str,
        generated_notes: list[GeneratedNote],
    ) -> list[Note]:
        if not generated_notes:
            logger.warning(
                "Generated notes rejected because the note list was empty document_id=%s",
                document_id,
            )
            raise ValueError("At least one generated note is required.")

        with self.uow_factory() as uow:
            document = uow.documents.get(document_id)
            if document is None:
                logger.warning(
                    "Generated notes rejected because document was not found document_id=%s",
                    document_id,
                )
                raise ValueError(f"Document not found: {document_id}")

            existing_notes = uow.notes.list(document_id=document_id)
            if existing_notes:
                logger.info(
                    "Skipping generated note persistence because notes already exist document_id=%s notes=%s",
                    document_id,
                    len(existing_notes),
                )
                uow.commit()
                return existing_notes

            notes = [
                Note(
                    document_id=document.id,
                    question=generated.question,
                    answer=generated.answer,
                )
                for generated in generated_notes
            ]

            for note in notes:
                uow.notes.add(note)
                created_at = now()
                uow.cards.add(
                    ReviewCard(
                        note_id=note.id,
                        due_at=created_at,
                        created_at=created_at,
                        updated_at=created_at,
                    )
                )

            uow.commit()
            logger.info(
                "Persisted generated notes document_id=%s notes=%s cards=%s",
                document_id,
                len(notes),
                len(notes),
            )
            return notes


class GenerateNotesHandler:
    """Generate notes for a stored document."""

    def __init__(
        self,
        factory: Callable[[], UnitOfWork],
        generator: NoteGenerator,
    ) -> None:
        self.uow_factory = factory
        self.generator = generator
        self.store_generated_notes = StoreGeneratedNotesUseCase(factory)

    async def __call__(self, event: DocumentCreated) -> None:
        document_id = event.payload["document_id"]
        logger.info(
            "Handling document-created event event_id=%s document_id=%s",
            event.id,
            document_id,
        )
        with self.uow_factory() as uow:
            document = uow.documents.get(document_id)
            if document is None:
                logger.warning(
                    "Document not found for note generation document_id=%s",
                    document_id,
                )
                raise ValueError(f"Document not found: {document_id}")

        result = self.generator(content=document.content)

        self.store_generated_notes(document_id, result.notes)
