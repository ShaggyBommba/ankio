from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from domain.entity import AnswerAssessment


class ApplicationDto(BaseModel):
    """Base class for application-level data transfer objects."""

    model_config = ConfigDict(extra="forbid")


class GeneratedNote(ApplicationDto):
    question: str
    answer: str


class GeneratedNotes(ApplicationDto):
    notes: list[GeneratedNote]


class DocumentNoteView(ApplicationDto):
    id: str
    question: str
    answer: str
    card_id: str | None = None
    due_at: datetime | None = None
    interval_days: int | None = None
    repetitions: int = 0
    attempts: int = 0
    correct: int = 0


class DocumentSummary(ApplicationDto):
    id: str
    content_preview: str
    content_length: int
    created_at: datetime
    updated_at: datetime
    notes: int
    cards: int
    due: int
    attempts: int
    generation_status: str


class DocumentDetail(DocumentSummary):
    content: str
    note_details: list[DocumentNoteView]


class ReviewPrompt(ApplicationDto):
    card_id: str = Field(..., description="ID of the review card")
    note_id: str = Field(..., description="ID of the note being reviewed")
    question: str = Field(..., description="Question to ask the learner")
    answer: str = Field(..., description="Expected answer for assessment")


class ReviewAssessmentRequest(ApplicationDto):
    quality: int = Field(ge=0, le=5, description="Externally assessed answer quality")
    correct: bool = Field(..., description="Whether the answer was correct")
    feedback: str = Field(..., description="External feedback for the attempt")
    confidence: float = Field(ge=0, le=1, description="Assessment confidence")


class ReviewAssessmentResult(ApplicationDto):
    card_id: str = Field(..., description="ID of the reviewed card")
    note_id: str = Field(..., description="ID of the reviewed note")
    assessment: AnswerAssessment = Field(
        ..., description="Assessment of the learner answer"
    )
    due_at: datetime = Field(..., description="Timestamp when the card is next due")
    interval_days: int = Field(..., description="Days until the next review")
    ease_factor: float = Field(..., description="Updated ease factor")


class RetentionPoint(ApplicationDto):
    date: str
    attempts: int
    correct: int
    percent: float


class RetentionOverview(ApplicationDto):
    documents: int
    notes: int
    cards: int
    due: int
    new: int
    reviewed: int
    attempts: int
    correct: int
    retention: float
    interval: float
    ease: float
    timeline: list[RetentionPoint]
