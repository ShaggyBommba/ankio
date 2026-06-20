---
name: ankio-ingest
description: Store material in Ankio and create spaced-repetition question/answer notes. Use when the user says they want to remember, memorize, save, study, add to Ankio, make flashcards, create review cards, or otherwise retain the current text, previous assistant answer, pasted content, file excerpt, or referenced learning material.
---

# Ankio Ingest

## Overview

Turn source material into Ankio documents, notes, and review cards through the Ankio MCP server.

## Workflow

1. Identify the source content.
   - If the user says "remember this" after an assistant explanation, use the immediately preceding assistant explanation as the source.
   - If the user pasted text, use the pasted text.
   - If the user references a local file, read only the relevant content before ingesting.
   - If the source is unclear, ask one concise clarification question.

2. Call the Ankio MCP `submit_document` tool with the source text.
   - In Codex, this is usually exposed as `mcp__ankio.submit_document`.
   - If the Ankio MCP tools are not visible, use `tool_search` to search for Ankio tools before falling back.
   - Do not write directly to SQLite or repository files.

3. Generate notes externally from the submitted source.
   - Create one clear factual question and one concise answer per note.
   - Use only claims supported by the source.
   - Prefer durable concepts, definitions, distinctions, workflows, constraints, risks, and examples.
   - Split compound facts into separate cards.
   - Avoid duplicate cards and trivia that does not help retention.

4. Call the Ankio MCP `store_generated_notes` tool with the returned `document_id` and generated notes.
   - In Codex, this is usually exposed as `mcp__ankio.store_generated_notes`.
   - Do not rely only on queued background note generation when the user asked to remember the material now.
   - If the operation returns existing notes, report that the document already had cards.

5. Report the result.
   - Include the number of notes/cards stored.
   - Keep the summary short unless the user asks to see the cards.

## Note Quality

Good notes ask about a single recall target:

- "What is the core idea of clean design?"
- "Why should dependencies point inward in clean design?"
- "What is the main risk of over-applying clean design?"

Weak notes are vague, unsupported, or overloaded:

- "Explain clean design."
- "What are all related patterns and all benefits?"
- "What should every app always use?"
