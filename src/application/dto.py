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
    assessment: AnswerAssessment = Field(..., description="Assessment of the learner answer")
    due_at: datetime = Field(..., description="Timestamp when the card is next due")
    interval_days: int = Field(..., description="Days until the next review")
    ease_factor: float = Field(..., description="Updated ease factor")


class RetentionPoint(ApplicationDto):
    date: str
    attempts: int
    correct: int
    retention_percent: float


class RetentionOverview(ApplicationDto):
    documents: int
    notes: int
    review_cards: int
    due_cards: int
    new_cards: int
    reviewed_cards: int
    attempts: int
    correct_attempts: int
    retention_percent: float
    average_interval_days: float
    average_ease_factor: float
    retention_over_time: list[RetentionPoint]
