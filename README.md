# Ankio

Ankio is a local spaced-repetition note service for agents.

The application stores source documents, generated notes, review cards, review
attempts, and scheduling state. It does not judge whether a learner's answer is
correct. Your agent, for example Codex or Claude, asks the question, compares the
learner answer to the stored expected answer, and records the review result back
through Ankio's MCP server.

## Install With Docker

The published image is expected to be available from:

```sh
ghcr.io/shaggybommba/ankio:latest
```

Pull the image:

```sh
docker pull ghcr.io/shaggybommba/ankio:latest
```

Create a persistent volume for the SQLite database:

```sh
docker volume create ankio-data
```

Run the MCP server:

```sh
docker run -d \
  --name ankio \
  --restart unless-stopped \
  -p 8004:8004 \
  -v ankio-data:/app/data \
  -e APP_NAME=ankio \
  -e APP_MCP_HOST=0.0.0.0 \
  -e APP_MCP_PORT=8004 \
  -e APP_DATABASE__PROVIDER=sqlite \
  -e APP_DATABASE__DATABASE=data/app \
  ghcr.io/shaggybommba/ankio:latest
```

The MCP endpoint is then available at:

```text
http://localhost:8004/mcp
```

Check that the container is running:

```sh
docker logs -f ankio
```

Stop and remove it:

```sh
docker stop ankio
docker rm ankio
```

The stored notes and reviews remain in the `ankio-data` Docker volume.

## Automated Local Setup

Set up directly from the repository with `uvx`:

```sh
uvx --from git+https://github.com/username/repo-name setup --target claude
```

Or, from a cloned checkout:

```sh
uv run setup --target all
```

Targets:

```sh
uv run setup --target claude
uv run setup --target codex
uv run setup --target all
```

The setup command:

- recreates the `ankio` Docker container from `ghcr.io/shaggybommba/ankio:latest`
- copies bundled skills from `assistant/skills` into the selected harness skills directory
- registers `http://localhost:8004/mcp` as an MCP server using `claude mcp` and/or `codex mcp`

It assumes Docker and the selected harness CLI are installed.

Preview changes without writing files or running Docker:

```sh
uv run setup --target all --dry-run
```

Remove the local setup:

```sh
uv run teardown --target all
```

The teardown command:

- removes the `ankio` MCP server registration from Claude and/or Codex
- removes the copied `ankio` skill directory from Claude and/or Codex
- removes the `ankio` Docker container
- removes the `ankio-data` Docker volume
- removes the pulled `ghcr.io/shaggybommba/ankio:latest` image when Docker allows it

Preview teardown without changing files or Docker:

```sh
uv run teardown --target all --dry-run
```

## Docker Compose

Alternatively, create a `compose.yml`:

```yaml
services:
  ankio:
    image: ghcr.io/shaggybommba/ankio:latest
    container_name: ankio
    restart: unless-stopped
    ports:
      - "8004:8004"
    environment:
      APP_NAME: ankio
      APP_MCP_HOST: 0.0.0.0
      APP_MCP_PORT: 8004
      APP_DATABASE__PROVIDER: sqlite
      APP_DATABASE__DATABASE: data/app
    volumes:
      - ankio-data:/app/data

volumes:
  ankio-data:
```

Start it:

```sh
docker compose up -d
```

## Configure Your Agent

Ankio has two install layers:

1. The Docker container runs the MCP server and stores data.
2. Your agent uses the MCP config and skill instructions from this repo.

The MCP URL for the local Docker setup is:

```text
http://localhost:8004/mcp
```

The assistant-facing files live in:

```text
assistant/
├── mcp.json
└── skills/
    ├── ankio-ingest/
    │   ├── SKILL.md
    │   └── agents/openai.yaml
    └── ankio-quiz/
        ├── SKILL.md
        └── agents/openai.yaml
```

Use `assistant/mcp.json` as the MCP server config when your harness accepts
JSON MCP configuration. Use the skills under `assistant/skills` as the agent
instructions for ingesting study material and running review sessions.

If your harness has its own MCP config format, copy the URL from
`assistant/mcp.json` and configure a streamable HTTP MCP server named `ankio`.

## MCP Tools

The MCP server exposes these tools:

- `submit_document`: store source text and return a document id.
- `get_next_document_for_note_generation`: return a stored document that has no notes yet.
- `store_generated_notes`: attach externally generated question and answer notes to a document and create review cards.
- `get_next_review_card`: return the next due review card.
- `record_review_assessment`: store the externally assessed result and update scheduling.
- `get_retention_overview`: read retention and review queue metrics.

## Agent Workflow

For note generation:

1. Store a document with `submit_document`, or fetch queued work with `get_next_document_for_note_generation`.
2. Generate factual question and answer notes externally.
3. Store those notes with `store_generated_notes`.

For review:

1. Fetch the next due card with `get_next_review_card`.
2. Ask the learner the returned question without revealing the answer.
3. Compare the learner's response to the expected answer.
4. Record the assessment with `record_review_assessment`.

Use this quality scale when recording reviews:

- `5`: perfect recall
- `4`: correct after hesitation or with minor missing detail
- `3`: correct but difficult or incomplete
- `2`: incorrect, but the expected answer seems easy after seeing it
- `1`: incorrect, but the expected answer feels familiar
- `0`: complete blackout or unrelated answer

## Configuration

Common environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `APP_MCP_HOST` | `localhost` | MCP bind host. Use `0.0.0.0` in Docker. |
| `APP_MCP_PORT` | `8004` | MCP port. |
| `APP_DATABASE__PROVIDER` | `sqlite` | Database provider. |
| `APP_DATABASE__DATABASE` | `app` | SQLite database name, resolved under the app directory with `.db` appended. |
| `APP_LOGGING__LEVEL` | `INFO` | Logging level. |

For Docker persistence, use `APP_DATABASE__DATABASE=data/app` with a volume
mounted at `/app/data`; the database file will be `/app/data/app.db`.

## Build And Publish

Build locally:

```sh
docker build -t ghcr.io/shaggybommba/ankio:latest .
```

Push to the registry:

```sh
docker push ghcr.io/shaggybommba/ankio:latest
```
