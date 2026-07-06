# Animus

**Animus** is a Python library that extends [pydantic-ai](https://ai.pydantic.dev/) with database-backed persistence, multi-agent orchestration, and structured session management.

It adds a modular, production-ready layer on top of pydantic-ai while remaining fully compatible with its agent, tool, and model APIs. Dependencies are kept at the bleeding edge — we move with the ecosystem.

---

## Features

Everything below is **extra** beyond what pydantic-ai provides out of the box:

| Feature | What it gives you |
|---|---|
| **Persistence layer** | Four pluggable managers (agent, session, history, model-config) backed by Tortoise ORM. Saves agents, sessions, threads, messages, and LLM calls to PostgreSQL or SQLite. |
| **Session + thread tracking** | `AnimusSession` (frozen dataclass) carries `session_id`, `thread_id`, `agent_instance_id`. Returned on every `run()` call. |
| **Thread branching** | `continue_thread=False` forks a new thread that inherits the parent's history but diverges independently. |
| **Session resume** | Pass a reconstructed `AnimusSession` as `source_session=` to resume any stored conversation thread from the DB. |
| **Multi-agent delegation** | `subagents=[...]` wires agents together. An auto-injected `delegate` tool lets the orchestrator's LLM delegate to sub-agents. Each delegation is isolated in its own thread fork. |
| **MessageTemplate** | Pass a template + vars instead of a pre-rendered string. Metadata (template, vars, renderer) is stored in the message JSON for later retrieval. Supports `python_format` and `jinja2`. |
| **CancellationToken** | Cooperative cancellation for long-running agent calls. Sessions/threads created before cancellation are persisted; incomplete LLM calls are not. |
| **AnimusModelConfig + AnimusKeys** | Structured model config with provider, name, temperature, max-tokens — persisted to DB. `AnimusKeys.from_config()` loads provider API keys from a JSON config file. |
| **`from_slug()`** | Class method to reconstruct a live agent from a previously-saved DB record. |
| **`run_stream_events()`** | Event-level streaming that emits structured `AnimusStreamEvent` objects, including `delegation_start`/`delegation_end` events in multi-agent flows. |
| **LLM call audit trail** | Every model invocation writes a row to `animus_llm_calls` with token usage and the exact messages sent. |
| **History compaction** | `get_compaction_processor()` automatically summarizes old messages when token usage exceeds a threshold, keeping long conversations within context limits. |
| **Langfuse integration** | One-call `init_langfuse()` enables full LLM tracing via pydantic-ai's instrumentation layer. |
| **Query services** | Five read-only services (`AgentQueryService`, `SessionQueryService`, `ThreadQueryService`, `AgentInstanceQueryService`, `MessageQueryService`) for analytics and message retrieval. |

---

## Engram Memory Bank Usage

For this backend, Animus should be used primarily for structured LLM workflows around memory processing.

Recommended use cases:

1. **Memory extraction**
   - Convert raw MCP/hook/manual observations into structured memory proposals.
   - Output should be validated by project-owned Pydantic schemas before storage.

2. **Canonicalization and summarization**
   - Rewrite noisy observations into concise memory facts.
   - Produce stable `summary`, `content`, `tags`, and `sensitivity` fields.

3. **Classification**
   - Suggest `scope_type`: `user`, `org`, or `repo`.
   - Suggest whether review is required.
   - Detect likely sensitive content.

4. **Duplicate/update reasoning**
   - Decide whether a new observation creates a new fact, updates an existing fact, or should be ignored.
   - Lexical matching can run first; Animus can reason over shortlisted candidates.

5. **Audit and observability**
   - Use Animus persistence and LLM call tracking for prompt version, model, token usage, and exact LLM input/output audit.
   - This is useful for dashboard review, debugging, and compliance.

Suggested project services:

```text
memory_processing_service.py
- extract_memory_proposal(raw_observation, actor_context)
- classify_memory_sensitivity(content)
- suggest_tags(content, scope_context)
- detect_duplicate_or_update(candidate_fact, existing_candidates)
```

Animus should not own memory persistence. The application database remains the source of truth for memory facts, proposals, versions, scopes, RBAC, and audit logs.

---

## Embeddings in This Project

Animus is the application-facing wrapper for Pydantic AI in this backend. Embedding generation should therefore go through Animus-compatible helpers/classes behind a project-owned `MemoryEmbeddingService`, not through direct `pydantic_ai` imports in memory CRUD, MCP tools, or retrieval code.

Conceptually, the embedding service should provide:

```text
MemoryEmbeddingService
- embed_memory_fact(memory_fact)
- embed_query(query_text)
- get_model_metadata()
```

Implementation rules:

- Use the Animus embedding equivalent for memory facts being indexed.
- Use the Animus embedding equivalent for user/search queries.
- Store model and dimension metadata because changing model/dimensions requires reindexing.
- Keep deterministic fake/test embeddings behind the same `MemoryEmbeddingService` boundary.

Recommended split:

```text
Animus
- structured LLM extraction
- classification
- summarization
- duplicate/update reasoning
- LLM call audit trail
- embedding model access through Animus-compatible helpers/classes

MemoryEmbeddingService
- document embeddings
- query embeddings
- model/dimension metadata
- test/fake embedding support
```

See [Embedding and retrieval design](./embedding-retrieval-design.md) for the full memory-bank embedding plan.

---

## Installation

```bash
uv add "animus @ git+ssh://git@bitbucket.org/tata1mg/animus.git@0.1.2"
```

Requires Python 3.12+.

For SQLite support (local dev / examples):

```bash
uv add aiosqlite
```

---

## Quick Start

### In-memory (no persistence)

```python
import asyncio
from animus import AnimusAgent

agent = AnimusAgent(
    agent_name="assistant",
    model="openai:gpt-4o-mini",
    instructions="You are a helpful assistant.",
)

async def main():
    result, session = await agent.run("What is 2 + 2?")
    print(result.output)   # "4" (or similar)

asyncio.run(main())
```

### With full persistence

```python
import asyncio
from animus import AnimusAgent, AnimusModelConfig, AnimusKeys, init_db, close_db
from animus.persistence.managers import (
    DBAgentManager,
    DBHistoryManager,
    DBModelConfigManager,
    DBSessionManager,
)

keys = AnimusKeys.from_config("config.json")

agent = AnimusAgent(
    agent_name="support",
    model=AnimusModelConfig(model_provider="openai", model_name="gpt-4o-mini", temperature=0.4),
    keys=keys,
    instructions="You are a customer support agent.",
    agent_manager=DBAgentManager(),
    session_manager=DBSessionManager(),
    history_manager=DBHistoryManager(),
    model_config_manager=DBModelConfigManager(),
)

async def main():
    await init_db("postgresql://user:pass@localhost/mydb")

    # Turn 1
    result1, session = await agent.run("Hello, I need help with my order.")
    print(result1.output)

    # Turn 2 — same thread, full history loaded
    result2, session = await agent.run("My order number is 12345.", source_session=session)
    print(result2.output)

    await close_db()

asyncio.run(main())
```

### Resume from stored IDs

```python
from animus import AnimusSession
from uuid import UUID

# Reconstruct from IDs you stored elsewhere
session = AnimusSession(
    session_id=UUID("..."),
    thread_id=UUID("..."),
    agent_instance_id=UUID("..."),
)

result, session = await agent.run("Continue where we left off", source_session=session)
```

### Multi-agent

```python
researcher = AnimusAgent(
    agent_name="researcher",
    model="openai:gpt-4o-mini",
    instructions="You are a research specialist.",
)

writer = AnimusAgent(
    agent_name="writer",
    model="openai:gpt-4o-mini",
    instructions="You are a writing specialist.",
)

orchestrator = AnimusAgent(
    agent_name="orchestrator",
    model="openai:gpt-4o-mini",
    instructions="Coordinate the team to answer the user.",
    subagents=[researcher, writer],
)

result, session = await orchestrator.run("Write a short essay on black holes.")
print(result.output)
```

### MessageTemplate

```python
from animus import MessageTemplate

result, session = await agent.run(
    MessageTemplate(
        template="Summarise the following:\n\n{content}\n\nFocus on: {focus}",
        vars={"content": article_text, "focus": "key takeaways"},
    )
)
```

### Cancellation

```python
import asyncio
from animus import CancellationToken

token = CancellationToken()
asyncio.create_task(cancel_after(token, delay=10.0))

try:
    result, session = await agent.run("Long task…", cancellation_token=token)
except asyncio.CancelledError:
    print(f"Cancelled: {token.get_reason()}")
```

---

## Database Setup

```python
from animus import init_db, close_db

# PostgreSQL
await init_db("postgresql://user:pass@localhost/mydb")

# SQLite (dev/testing)
await init_db("sqlite://path/to/my.db")

# Always clean up
await close_db()
```

`init_db()` auto-creates all tables on first run (idempotent).

---

## API Keys Config

Create a `config.json` at your project root:

```json
{
  "ANIMUS_KEYS": {
    "openai_api_key": "sk-...",
    "anthropic_api_key": "sk-ant-..."
  }
}
```

Load it:

```python
keys = AnimusKeys.from_config("config.json")
```

---

## Examples

| Example | What it covers |
|---|---|
| [01_hello_world.py](examples/01_hello_world.py) | Minimal agent, no persistence |
| [02_with_persistence.py](examples/02_with_persistence.py) | DB-backed sessions, threads, message history |
| [03_streaming.py](examples/03_streaming.py) | `run_stream` and `run_stream_events` |
| [04_tools.py](examples/04_tools.py) | Registering and calling tools |
| [05_multi_agent.py](examples/05_multi_agent.py) | Orchestrator + sub-agent delegation |
| [06_thread_branching.py](examples/06_thread_branching.py) | Forking threads, diverging independently |
| [07_from_slug.py](examples/07_from_slug.py) | Loading agent config from DB via `from_slug` |
| [08_cancellation.py](examples/08_cancellation.py) | CancellationToken cooperative cancellation |
| [09_history_and_templates.py](examples/09_history_and_templates.py) | MessageTemplate with persisted history |

```bash
uv run python examples/01_hello_world.py
```

---

## Documentation

| Doc | Topic |
|---|---|
| [concepts.md](docs/concepts.md) | Core concepts: Session, Thread, Agent Instance, AnimusSession |
| [persistence.md](docs/persistence.md) | Four persistence managers and DB schema |
| [sessions-and-threads.md](docs/sessions-and-threads.md) | AnimusSession, thread branching, session resume |
| [multi-agent.md](docs/multi-agent.md) | Subagents, `delegate` tool, delegation depth |
| [message-template.md](docs/message-template.md) | MessageTemplate, renderers, metadata storage |
| [model-config.md](docs/model-config.md) | AnimusModelConfig, AnimusKeys, build_model |
| [from-slug.md](docs/from-slug.md) | `from_slug()` class method |
| [streaming.md](docs/streaming.md) | `run_stream`, `run_stream_events`, event types |
| [cancellation.md](docs/cancellation.md) | CancellationToken cooperative cancellation |
| [llm-call-tracking.md](docs/llm-call-tracking.md) | `animus_llm_calls` audit trail |
| [history-compaction.md](docs/history-compaction.md) | `get_compaction_processor` automatic summarization |
| [langfuse.md](docs/langfuse.md) | Langfuse observability integration |
| [query-services.md](docs/query-services.md) | Read-only query services for analytics |

---

## Project Structure

```
animus/
├── animus/
│   ├── agents/              # AnimusAgent (base.py) + model_builder
│   ├── config.py            # AnimusKeys
│   ├── history/             # MessageTemplate, get_compaction_processor
│   ├── integrations/        # LangfuseConfig, init_langfuse
│   ├── lifecycle/           # CancellationToken, ToolResponseFallbackConfig
│   ├── models/
│   │   ├── orm/             # Tortoise ORM models
│   │   └── schemas/         # Pydantic DTOs (AgentDTO, SessionDTO, etc.)
│   ├── persistence/
│   │   ├── protocols/       # AgentManager, HistoryManager, SessionManager, ModelConfigManager
│   │   ├── managers/        # DB implementations (DBAgentManager, etc.)
│   │   └── types.py         # AnimusSession, AnimusModelConfig, AgentConfig, AnimusRunDeps
│   ├── query/               # Read-only query services + protocols
│   ├── repository/          # Low-level DB access (Tortoise)
│   ├── streaming/           # StreamBufferManager, event types
│   ├── tools/               # delegation tool
│   └── utils/db/            # init_db, close_db
├── docs/                    # Feature documentation
├── examples/                # 9 runnable examples
└── pyproject.toml
```

---

## Tech Stack

- **Python** 3.12+
- **pydantic-ai** — agent + LLM abstraction layer
- **Tortoise ORM** — async ORM for PostgreSQL / SQLite
- **pydantic** — data validation
- **uv** — package management

---

## Code Quality

```bash
ruff check .          # lint
ruff format .         # format
pre-commit install    # install git hooks
```

<!-- Nothing is true; everything is permitted. -->