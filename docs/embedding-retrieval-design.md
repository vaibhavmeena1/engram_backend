# Embedding and Retrieval Design

## Decision

Use PostgreSQL as the source of truth and Qdrant as a rebuildable vector index for approved memory facts.

Use one shared Qdrant deployment, with multiple collections for isolation by environment and, if needed later, organization or embedding model version.

For embedding generation, use Animus-compatible embedding helpers/classes through an internal service abstraction. Animus is the application-facing wrapper around Pydantic AI in this backend, so memory services should not import or call Pydantic AI directly.

This keeps memory CRUD, MCP tools, and dashboard APIs independent from concrete embedding setup while still using the model ecosystem through Animus.

---

## Recommendation

For this memory-bank use case:

1. **Phase 1/2:** implement lexical retrieval only, but keep the config and schema ready for embeddings.
2. **Phase 3:** use Animus for LLM processing: extraction, tagging, sensitivity detection, summarization, and duplicate/update suggestions.
3. **Phase 4:** add embeddings through Animus-compatible embedding helpers/classes behind a `MemoryEmbeddingService` interface.
4. **Use the document-embedding path when indexing memory facts.**
5. **Use the query-embedding path when searching.** Some models optimize query and document embeddings differently.
6. **Store embedding model metadata with each indexed vector.** Model changes require re-embedding and reindexing.
7. **Always re-check Qdrant matches against PostgreSQL status, scope, and RBAC before returning content.**
8. **Use one Qdrant instance with multiple collections.** Start with one collection per environment; split further only when isolation or model migration requires it.

---

## Why Use an Internal Embedding Service

Do not call Pydantic AI directly from memory CRUD, retrieval, dashboard, or MCP tool code.

Use a small service boundary:

```text
MemoryEmbeddingService
- embed_memory_fact(memory_fact) -> EmbeddingVector
- embed_query(query_text) -> EmbeddingVector
- get_model_metadata() -> EmbeddingModelMetadata
```

Benefits:

- hides Animus/model setup
- centralizes dimensions/model validation
- makes tests easy with deterministic embeddings
- supports later caching, batching, retry, and rate limiting
- supports future model migration without touching MCP tools or dashboard APIs

---

## Model Strategy

Animus should provide the application-facing path to the embedding model ecosystem.

Recommended starting options:

| Option | When to use | Notes |
|---|---|---|
| `openai:text-embedding-3-large` | Preferred semantic-search default | Higher retrieval quality; 3072 dimensions by default and higher cost/storage. |
| `google:gemini-embedding-2` | Fallback if OpenAI embeddings are unavailable or unsuitable | Supports dimension control; task conditioning may matter for retrieval. |
| `google:gemini-embedding-001` | Older Gemini fallback if required by provider availability | Supports dimension control. |
| `openai:text-embedding-3-small` | Cost-saving fallback only | Good quality and lower cost, but not the selected default. |

Use config to select the model. Do not hardcode alternate embedding-provider wiring in memory services. Local/private embeddings are out of scope for this rollout.

### OpenAI Embedding Reference Notes

For OpenAI v3 embedding models:

| Model | Default dimensions | Max input | Notes |
|---|---:|---:|---|
| `openai:text-embedding-3-large` | 3072 | 8192 tokens | Selected default; higher retrieval quality, larger vectors, higher cost/storage. |
| `openai:text-embedding-3-small` | 1536 | 8192 tokens | Cost-saving fallback only. |

Relevant behavior for this project:

- Requests are billed by input tokens, so embedding raw noisy observations repeatedly should be avoided.
- Both `text-embedding-3-small` and `text-embedding-3-large` support dimension reduction through the `dimensions` setting.
- If dimensions are reduced, the Qdrant collection must be created with the reduced vector size.
- OpenAI embeddings are normalized to length 1, so cosine similarity and dot product produce the same ranking. Keep cosine as the default distance metric for this rollout.
- For OpenAI token pre-checks, `cl100k_base` is the relevant tokenizer family for third-generation embedding models. Prefer Animus-provided token counting helpers when available; otherwise use model-specific token counting where needed.
- Embedding models are not used as factual knowledge sources. They only encode the text we provide, so recency limitations matter less than they do for generation models.

---

## Qdrant Deployment and Collection Strategy

Decision: run **one Qdrant service** and create **multiple collections**.

Recommended initial collection:

```text
engram_memories_<environment>
```

Examples:

```text
engram_memories_dev
engram_memories_stage
engram_memories_prod
```

Future collection split options:

| Strategy | Collection pattern | When to use |
|---|---|---|
| Environment-only | `engram_memories_<environment>` | Best POC/default; one collection per env. |
| Environment + org | `engram_memories_<environment>_<org_slug>` | Use if org-level isolation becomes required. |
| Environment + model version | `engram_memories_<environment>_<embedding_model_slug>_<dimensions>` | Use during model/dimension migration or A/B testing. |

Do not mix vectors with different dimensions in the same unnamed-vector collection.

---

## Dimension Strategy

Qdrant collection vector size must match the embedding output dimension.

Rules:

1. Decide `MODEL` and `DIMENSIONS` before creating a shared index.
2. Create the Qdrant collection with exactly that vector size.
3. Store `embedding_model`, embedding implementation metadata, and `embedding_dimensions` in vector payload or metadata.
4. If the model or dimensions change, run a full re-embed and reindex job.
5. Do not mix vectors from different models or dimensions in one collection unless using explicitly named vectors.

For the POC, keep one model and one vector dimension per collection.

---

## Indexing Granularity

Start with **one vector per approved memory fact**.

Embed a canonical text built from stable fields:

```text
{summary}

{content}

Tags: {tag_slugs}
Scope: {scope_type}
Repository: {repo_slug_if_any}
```

Do not embed raw unreviewed observations by default. Raw observations may contain sensitive data, noise, or incorrect statements.

Future improvement: if a memory fact becomes long, split it into chunks and store multiple vectors per `memory_fact_id` with `chunk_index` and `chunk_text` metadata.

---

## Index Lifecycle

### On memory approval

```text
memory_proposal approved
        |
        v
memory_facts row inserted/updated in PostgreSQL
        |
        v
memory_fact_versions row inserted
        |
        v
MemoryEmbeddingService.embed_memory_fact(...)
        |
        v
Qdrant upsert with approved memory payload
```

### On approved edit

```text
memory_fact updated
        |
        v
new memory_fact_versions row
        |
        v
re-embed canonical text
        |
        v
upsert same Qdrant point id
```

### On delete/archive/rejection

```text
memory_fact status changed to deleted/archived/rejected
        |
        v
remove Qdrant point or mark payload status inactive
```

Recommendation: delete inactive points from Qdrant and rely on PostgreSQL for audit/history.

---

## Qdrant Point Design

Use a stable point id derived from the memory fact id.

```text
point_id = memory_fact_id
```

Payload:

```json
{
  "memory_fact_id": "uuid",
  "org_id": "uuid",
  "scope_type": "repo",
  "scope_id": "uuid",
  "repo_id": "uuid-or-null",
  "owner_user_id": "uuid-or-null",
  "status": "approved",
  "visibility": "repo",
  "tag_slugs": ["testing", "architecture"],
  "embedding_source": "animus",
  "embedding_model": "text-embedding-3-large",
  "embedding_dimensions": 3072,
  "content_hash": "sha256",
  "updated_at": "2026-07-03T00:00:00Z"
}
```

Only store metadata needed for filtering/debugging in Qdrant. Do not rely on Qdrant as the canonical store for memory content.

---

## Search Flow

### Semantic search

```text
search_memories(query, actor_context, filters)
        |
        v
MemoryEmbeddingService.embed_query(query)
        |
        v
Qdrant search using org/scope/status filters
        |
        v
fetch candidate memory_fact_ids from PostgreSQL
        |
        v
apply status + RBAC + scope filtering
        |
        v
return approved memories with scores and audit log
```

### Hybrid search

```text
lexical candidates from PostgreSQL
        +
semantic candidates from Qdrant
        |
        v
merge and normalize scores
        |
        v
RBAC/status filtering in PostgreSQL
        |
        v
optional rerank
        |
        v
return top_k
```

Start without reranking. Add reranking only if search quality is not good enough.

---

## Animus-Compatible Embedding Service Usage

Example shape for the embedding service:

```python
class MemoryEmbeddingService:
    def __init__(self, model: str, dimensions: int | None = None) -> None:
        # Construct the embedding client through Animus-compatible helpers/classes.
        self._model = model
        self._dimensions = dimensions

    async def embed_memory_documents(self, documents: list[str]) -> list[list[float]]:
        # Use the Animus equivalent of document embedding here.
        raise NotImplementedError

    async def embed_search_query(self, query: str) -> list[float]:
        # Use the Animus equivalent of query embedding here.
        raise NotImplementedError
```

Testing should use a deterministic fake implementation behind the same service interface.

---

## Config Shape

```json
{
  "EMBEDDINGS": {
    "ENABLED": false,
    "MODEL": "openai:text-embedding-3-large",
    "DIMENSIONS": null,
    "BATCH_SIZE": 64,
    "INSTRUMENT": true
  },
  "QDRANT": {
    "ENABLED": false,
    "URL": "http://localhost:6333",
    "API_KEY": "",
    "COLLECTION_STRATEGY": "per_environment",
    "COLLECTION_PREFIX": "engram_memories",
    "COLLECTION": "engram_memories_dev"
  },
  "MEMORY_RETRIEVAL": {
    "MODE": "lexical",
    "DEFAULT_LIMIT": 20,
    "MAX_LIMIT": 100,
    "ENABLE_RERANKING": false
  }
}
```

`EMBEDDINGS.ENABLED` and `QDRANT.ENABLED` should both be true before semantic retrieval is used.

---

## Animus Responsibilities

Use Animus for LLM tasks where its persistence, session tracking, model config, and LLM audit trail are valuable:

- memory extraction from raw observations
- memory summarization/canonicalization
- tag/category suggestion
- sensitivity classification
- duplicate/update proposal reasoning
- optional reranking later, if implemented as an LLM judgment

Do not force embeddings into conversational Animus sessions if they are simple vector API calls. Still construct and execute embedding calls through Animus-compatible helpers/classes behind `MemoryEmbeddingService`, so application code does not directly depend on Pydantic AI.

---

## Resolved Clarification

Animus is the application-facing abstraction for model access in this backend.

Because Animus wraps Pydantic AI and can override/extend its behavior, the backend should use:

```text
Animus for structured LLM processing
Animus-compatible helpers/classes for embeddings
MemoryEmbeddingService as the app-owned boundary
```

Only `MemoryEmbeddingService` should know the concrete Animus embedding API. MCP tools, CRUD services, and dashboard APIs should not call Pydantic AI directly.