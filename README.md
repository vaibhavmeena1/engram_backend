# engram-backend

Backend service for agent memory/context POC, built with [Vortex](https://bitbucket.org/tata1mg/vortex) (FastAPI wrapper).

## Quick Start

```bash
# Install dependencies
uv sync

# Run the development server
uv run python -m app.main

# Or with uvicorn directly
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure

```
engram-backend/
├── app/                    # Application package
│   ├── main.py             # Application entry point
│   ├── routers/            # API route definitions
│   ├── services/           # Business logic layer
│   ├── models/             # Database models (Tortoise ORM)
│   ├── schemas/            # Pydantic request/response schemas
│   ├── listeners/          # Application lifecycle listeners
│   └── migrations/         # Application database migrations
├── config.json             # Service configuration (gitignored)
├── config_template.json    # Template for config.json
├── pyproject.toml          # Project metadata & dependencies
├── Dockerfile              # Container image definition
└── tests/                  # Test suite
```

## Configuration

Copy the template and fill in your values:

```bash
cp config_template.json config.json
```

Key configuration sections:
- **Core** — `NAME`, `HOST`, `PORT`, `DEBUG`, `DEV_MODE`
- **SENTRY** — Error tracking DSN and environment
- **REDIS_CACHE_HOSTS** — Redis cache connection pools
- **DATABASE** — PostgreSQL connection pools
- **LANGFUSE** — LLM observability integration
- **OPEN_TELEMETRY** — Distributed tracing

## Health Check

The service exposes a default health check endpoint:

```bash
curl http://localhost:8000/ping
# {"ping":"pong"}
```

## Testing

```bash
uv run pytest
```

## CLI Console

Vortex provides an interactive console with the app pre-loaded:

```bash
uv run vortex console
```