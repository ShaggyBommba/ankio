---
name: ankio-feedback
description: Give short teaching feedback for Ankio quiz answers. Use when a learner answers a spaced-repetition card, especially when the answer is wrong, incomplete, misspelled, uncertain, or the learner says they do not know, so Codex should explain the correction and help the learner remember without revealing future answers.
---

# Ankio Feedback

## Overview

Turn an Ankio review assessment into useful learner feedback. The goal is to correct the answer, explain the mismatch, and give a small memory aid while keeping the review moving.

## Feedback Shape

For incorrect or incomplete answers, use this structure:

1. State the result: `Incorrect`, `Incomplete`, or `Missed`.
2. Give the expected answer in one sentence.
3. Explain the contrast with the learner answer when it helps.
4. Add one brief memory cue, distinction, or association.
5. Ask the next due card only after feedback is complete.

Keep user-facing feedback to 2-4 short sentences. Do not lecture, add unrelated facts, or turn feedback into a long explanation.

## Common Cases

- **Wrong but related:** Name the confusion directly. Example: `The Thames is associated with London; Paris is on the Seine.`
- **Partially correct:** Credit the correct part, then name what is missing. Example: `Eiffel Tower is correct, but the card asked for three landmarks.`
- **Spelling or typo:** Accept the answer if the intended meaning is clear. Example: `louvren` can count as `Louvre` when the card only needs that museum.
- **"I don't know":** Treat as missed. Give the expected answer and a simple cue, not criticism.
- **Overbroad answer:** Say why it does not satisfy the card. Example: `restaurants` is food-related, but it does not answer what Montmartre is known for.

## Recording Feedback

Use the `record_review_assessment.feedback` field for a concise assessment, not a full lesson. Put the extra teaching cue in the chat response if needed.

Good stored feedback:

- `Incorrect. The expected answer was the River Seine; the Thames is associated with London.`
- `Incomplete. Eiffel Tower is correct, but the card asked for three landmarks.`
- `Missed. The expected answer was boutiques and historic buildings.`

Avoid vague stored feedback:

- `Wrong.`
- `Try harder next time.`
- `Not quite, but close.`

## Tone

Be direct, calm, and specific. Do not shame the learner. Prefer concrete contrasts and memory hooks over encouragement.
