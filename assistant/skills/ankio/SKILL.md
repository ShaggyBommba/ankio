---
name: ankio
description: Use when working with the local Ankio spaced-repetition MCP server to store source documents, generate question and answer notes, fetch due review cards, ask the learner questions, assess answers externally, and record review outcomes.
metadata:
  short-description: Use Ankio notes and reviews
---

# Ankio

Use the Ankio MCP server for local spaced-repetition study workflows.

The application stores documents, notes, review cards, review attempts, and scheduling state. It does not assess learner answers. The agent is responsible for generating notes, asking review questions, and assessing learner answers before recording the result.

## Requirements

The local MCP server should be running through Docker:

```sh
docker run -d \
  --name ankio \
  --restart unless-stopped \
  -p 8004:8004 \
  -v ankio-data:/app/data \
  -e APP_MCP_HOST=0.0.0.0 \
  -e APP_MCP_PORT=8004 \
  -e APP_DATABASE__PROVIDER=sqlite \
  -e APP_DATABASE__DATABASE=data/app \
  ghcr.io/shaggybommba/ankio:latest
```

The streamable HTTP endpoint is:

```text
http://localhost:8004/mcp
```

## Available Tools

- `submit_document`: store source text and return a document id.
- `get_next_document_for_note_generation`: return a stored document that has no notes yet.
- `store_generated_notes`: attach externally generated question and answer notes to a document and create review cards.
- `get_next_review_card`: return the next due review card.
- `record_review_assessment`: store the externally assessed result and update scheduling.
- `get_retention_overview`: read retention and review queue metrics.

## Generating Notes

When the user asks to create notes from content:

1. If the content has not been stored, call `submit_document`.
2. If picking up queued work, call `get_next_document_for_note_generation`.
3. Generate factual notes externally. Each note must have one clear question and one answer supported by the source document.
4. Call `store_generated_notes` with the `document_id` and generated notes.
5. Report how many notes were stored.

Do not invent unsupported facts. If the document does not support a note, skip it.

## Review Session

When the user asks to review:

1. Call `get_next_review_card`.
2. If `card` is null, say there are no due cards.
3. Ask the learner only the returned `question`.
4. Do not reveal `answer` until after the learner responds.
5. Compare the learner response to the returned `answer`.
6. Record the result with `record_review_assessment`.

Use this quality scale:

- `5`: perfect recall
- `4`: correct after hesitation or with minor missing detail
- `3`: correct but difficult or incomplete
- `2`: incorrect, but the expected answer seems easy after seeing it
- `1`: incorrect, but the expected answer feels familiar
- `0`: complete blackout or unrelated answer

Set `correct` to true only when the learner's answer captures the expected meaning. Set `confidence` to a value from `0.0` to `1.0` based on assessment certainty. Keep `feedback` short and specific.

## Metrics

When the user asks about progress, retention, due cards, or review stats, call `get_retention_overview` and summarize the returned metrics.
