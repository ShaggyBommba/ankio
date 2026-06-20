---
name: ankio-quiz
description: Run Ankio spaced-repetition reviews. Use when the user says quiz me, review me, test me, start a review, ask me Ankio cards, continue the quiz, or when the conversation is in an active Ankio review and the user answers the current review question so the answer must be assessed and recorded.
---

# Ankio Quiz

## Overview

Run an Ankio review session one card at a time while keeping answers hidden until the learner responds.

## Start Or Continue

If there is no active card waiting for an answer:

1. Call the Ankio MCP `get_next_review_card` tool.
2. If `card` is null, say there are no due cards.
3. Ask only the returned `question`.
4. Keep the returned `answer`, `card_id`, and relevant metadata private in conversation context for assessment.
5. Do not reveal or hint at the answer before the learner responds.

If the user is answering an active card:

1. Compare the learner response to the hidden expected answer.
2. Call the Ankio MCP `record_review_assessment` tool with `card_id`, `quality`, `correct`, `feedback`, and `confidence`.
   - In Codex, this is usually exposed as `mcp__ankio.record_review_assessment`.
3. Briefly show whether the answer was correct, the expected answer, and specific feedback.
4. If the user asked for a session or continuation, immediately call the Ankio MCP `get_next_review_card` tool and ask the next question. If no cards remain, say the review is complete.

If the Ankio MCP tools are not visible, use `tool_search` to search for Ankio tools before falling back. Do not write directly to SQLite or repository files.

## Scoring

Use this quality scale:

- `5`: perfect recall
- `4`: correct after hesitation or with minor missing detail
- `3`: correct but difficult or incomplete
- `2`: incorrect, but the expected answer seems easy after seeing it
- `1`: incorrect, but the expected answer feels familiar
- `0`: complete blackout or unrelated answer

Set `correct` to true only when the learner captures the expected meaning, not merely related keywords.

Set `confidence` from `0.0` to `1.0` based on assessment certainty:

- Use `0.9` to `1.0` when the learner response clearly matches or clearly misses.
- Use `0.6` to `0.8` when the response is ambiguous or partially correct.
- Use below `0.6` only when the question or expected answer is itself unclear.

Keep feedback short and actionable.

## Interaction Rules

- Ask one review question at a time.
- Do not include multiple-choice options unless they are part of the stored question.
- Do not answer the card for the learner.
- Stop when the user says stop, pause, or enough.
