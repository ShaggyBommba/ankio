from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from math import ceil
from typing import Callable

from application.adapters.core import UnitOfWork
from application.dto import RetentionOverview, RetentionPoint, ReviewAssessmentResult, ReviewPrompt
from domain.entity import AnswerAssessment, ReviewAttempt, ReviewCard
from utils.time import now, utc

logger = logging.getLogger(__name__)


class StartReviewSessionUseCase:
    """Load the next due card prompt without exposing the answer."""

    def __init__(self, factory: Callable[[], UnitOfWork]) -> None:
        self.uow_factory = factory

    def __call__(self) -> ReviewPrompt | None:
        with self.uow_factory() as uow:
            card = uow.review_cards.next_due(now())
            if card is None:
                logger.info("No due review cards available")
                return None

            note = uow.notes.get(card.note_id)
            if note is None:
                logger.warning(
                    "Due review card references missing note card_id=%s note_id=%s",
                    card.id,
                    card.note_id,
                )
                return None

            logger.info(
                "Loaded due review prompt card_id=%s note_id=%s",
                card.id,
                note.id,
            )
            return ReviewPrompt(
                card_id=card.id,
                note_id=note.id,
                question=note.question,
                answer=note.answer,
            )


class RecordReviewAssessmentUseCase:
    """Record an external assessment and update review scheduling."""

    def __init__(
        self,
        factory: Callable[[], UnitOfWork],
        scheduler: ReviewUseCase,
    ) -> None:
        self.uow_factory = factory
        self.scheduler = scheduler

    def __call__(
        self,
        card_id: str,
        assessment: AnswerAssessment,
    ) -> ReviewAssessmentResult:
        reviewed_at = now()
        with self.uow_factory() as uow:
            card = uow.review_cards.get(card_id)
            if card is None:
                logger.warning(
                    "Review assessment rejected because card was not found card_id=%s",
                    card_id,
                )
                raise ValueError(f"ReviewCard not found: {card_id}")

            note = uow.notes.get(card.note_id)
            if note is None:
                logger.warning(
                    "Review assessment rejected because note was not found card_id=%s note_id=%s",
                    card.id,
                    card.note_id,
                )
                raise ValueError(f"Note not found: {card.note_id}")

            updated_card = self.scheduler(card, assessment, reviewed_at)
            uow.review_attempts.add(
                ReviewAttempt(
                    card_id=card.id,
                    assessment=assessment,
                    reviewed_at=reviewed_at,
                )
            )
            uow.review_cards.update(updated_card)
            uow.commit()
            logger.info(
                "Recorded review assessment card_id=%s note_id=%s quality=%s correct=%s interval_days=%s due_at=%s",
                updated_card.id,
                note.id,
                assessment.quality,
                assessment.correct,
                updated_card.interval_days,
                updated_card.due_at.isoformat(),
            )

            return ReviewAssessmentResult(
                card_id=updated_card.id,
                note_id=note.id,
                assessment=assessment,
                due_at=updated_card.due_at,
                interval_days=updated_card.interval_days,
                ease_factor=updated_card.ease_factor,
            )


class ReviewUseCase:
    """Calculate the next spaced-repetition state for a reviewed card."""

    def __call__(
        self,
        card: ReviewCard,
        assessment: AnswerAssessment,
        reviewed_at: datetime | None = None,
    ) -> ReviewCard:
        reviewed_at = reviewed_at or now()
        quality = assessment.quality
        if assessment.correct:
            quality = max(3, quality)
        else:
            quality = min(2, quality)

        ease_factor = card.ease_factor + (
            0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        )
        ease_factor = max(1.3, ease_factor)

        if quality < 3:
            repetitions = 0
            interval_days = 1
            lapses = card.lapses + 1
        else:
            repetitions = card.repetitions + 1
            lapses = card.lapses

            if repetitions == 1:
                interval_days = 1
            elif repetitions == 2:
                interval_days = 6
            else:
                interval_days = ceil(card.interval_days * ease_factor)

        due_at = reviewed_at + timedelta(days=interval_days)
        logger.debug(
            "Scheduled review card_id=%s quality=%s normalized_quality=%s interval_days=%s ease_factor=%s due_at=%s",
            card.id,
            assessment.quality,
            quality,
            interval_days,
            ease_factor,
            due_at.isoformat(),
        )
        return card.model_copy(
            update={
                "due_at": due_at,
                "interval_days": interval_days,
                "ease_factor": ease_factor,
                "repetitions": repetitions,
                "lapses": lapses,
                "last_reviewed": reviewed_at,
                "updated_at": reviewed_at,
            }
        )


class ReviewOverviewUseCase:
    """Summarize stored review state for dashboard display."""

    def __init__(self, factory: Callable[[], UnitOfWork]) -> None:
        self.uow_factory = factory

    def __call__(self) -> RetentionOverview:
        current = now()
        with self.uow_factory() as uow:
            documents = uow.documents.list()
            notes = uow.notes.list()
            cards = uow.review_cards.list()
            attempts = uow.review_attempts.list()

        due_cards = sum(1 for card in cards if utc(card.due_at) <= current)
        new_cards = sum(1 for card in cards if card.repetitions == 0)
        reviewed_cards = sum(
            1 for card in cards if card.repetitions > 0 or card.last_reviewed is not None
        )
        correct_attempts = sum(1 for attempt in attempts if attempt.assessment.correct)
        retention_percent = (
            round((correct_attempts / len(attempts)) * 100, 1) if attempts else 0.0
        )
        average_interval_days = (
            round(sum(card.interval_days for card in cards) / len(cards), 1)
            if cards
            else 0.0
        )
        average_ease_factor = (
            round(sum(card.ease_factor for card in cards) / len(cards), 2)
            if cards
            else 0.0
        )

        by_day: dict[str, dict[str, int]] = defaultdict(
            lambda: {"attempts": 0, "correct": 0}
        )
        for attempt in attempts:
            day = utc(attempt.reviewed_at).date().isoformat()
            by_day[day]["attempts"] += 1
            if attempt.assessment.correct:
                by_day[day]["correct"] += 1

        retention_over_time = [
            RetentionPoint(
                date=day,
                attempts=values["attempts"],
                correct=values["correct"],
                retention_percent=round(
                    (values["correct"] / values["attempts"]) * 100,
                    1,
                ),
            )
            for day, values in sorted(by_day.items())
        ]

        overview = RetentionOverview(
            documents=len(documents),
            notes=len(notes),
            review_cards=len(cards),
            due_cards=due_cards,
            new_cards=new_cards,
            reviewed_cards=reviewed_cards,
            attempts=len(attempts),
            correct_attempts=correct_attempts,
            retention_percent=retention_percent,
            average_interval_days=average_interval_days,
            average_ease_factor=average_ease_factor,
            retention_over_time=retention_over_time,
        )
        logger.info(
            "Built retention overview documents=%s notes=%s cards=%s due=%s attempts=%s retention=%s",
            overview.documents,
            overview.notes,
            overview.review_cards,
            overview.due_cards,
            overview.attempts,
            overview.retention_percent,
        )
        return overview
