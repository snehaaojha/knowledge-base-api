# Sneha's Interview-Ready Guide: Knowledge Base API

> **Mission:** Crack the job. This guide tells the story of the project so you can explain every decision, every algorithm, and every "why" with confidence.

---

## Chapter 1: The Problem We're Solving (Open with this in interviews)

**The story:** Imagine a company with 10,000 PDFs. A user asks: *"How do we handle refund requests?"* Traditional keyword search looks for "refund" and "handle"—but the policy doc says *"return and exchange procedures"*. No match. The user gives up.

**Our solution:** *Semantic search*. We don't match words—we match *meaning*. "Refund" and "return procedures" are semantically close. The system finds the right doc.

**One-liner for interview:**  
*"We convert text into dense vectors (embeddings), store them in a vector DB, and retrieve by similarity—so users search by meaning, not keywords."*

**Memory trick:** **E-S-R** — Embed → Store → Retrieve.

---

## Chapter 2: The Big Picture (Architecture in 60 seconds)

Think of it like a **library**:

| Layer | What it does | File |
|-------|--------------|------|
| **The Stage** | Starts app, preloads model, handles all exceptions | `main.py` |
| **Reception** | Takes requests, returns responses, validates input | `api.py` |
| **Librarian** | Chops books into chunks, orchestrates everything | `service.py` |
| **Translator** | Turns text into numbers (embeddings) | `embeddings.py` |
| **Warehouse** | Stores vectors, finds similar ones | `db.py` |
| **Rules** | Defines what input looks like, validates doc_id | `schemas.py` |
| **Clipboard** | Tracks each request with X-Request-ID for logs | `middleware.py` |
| **Settings** | Loads env vars, log level, chunk size | `config.py` |

**Project structure:**
```
sneha/
├── app/
│   ├── main.py       # FastAPI app, lifespan, exception handlers
│   ├── api.py        # Routes: ingest, search, health
│   ├── service.py    # Chunking, ingest, search
│   ├── db.py         # Endee client, index, upsert, query
│   ├── embeddings.py # Model load, embed_texts, embed_single
│   ├── schemas.py    # Pydantic models
│   ├── config.py     # Settings from .env
│   └── middleware.py # Request ID
├── scripts/          # setup, setup-eval, run, test, docker-run
├── tests/            # conftest, test_api, test_service
├── requirements.txt  # Full deps
├── requirements-eval.txt  # Light deps for evaluators
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

**Request flow (say this out loud):**
1. Client → Middleware (adds request_id) → API (validates)
2. API → Service (orchestrates)
3. Service → Embeddings (text → vector) + DB (store/query)

**Interview Q: "Walk me through an ingest request."**
> "The request hits the API, which validates via Pydantic. Service receives the text, chunks it into sentence-aware pieces, passes each chunk to the embedding model to get 384-d vectors, then upserts them into Endee with metadata. We return doc_id and chunks_stored."

---

## Chapter 2B: The Supporting Cast (main, middleware, schemas, config)

**The story:** Every request passes through a few helpers before and after the main work. Here's who does what.

### main.py — The Stage Manager

- **Lifespan:** On startup, we preload the embedding model in a thread (`asyncio.to_thread`) so the first health check doesn't block for 30 seconds.
- **Exception handlers:** `RequestValidationError` → 422 with `_json_safe(exc.errors())` so we never return non-serializable stuff (e.g. ValueError in `ctx`). Generic `Exception` → 500 JSON (not HTML). `HTTPException` → pass through with `_safe_detail()` so detail is always JSON-serializable.

**Interview Q: "Why preload the model at startup?"**
> "So the first health check or search doesn't block for 30+ seconds loading the model. Load balancers expect fast health responses."

### middleware.py — The Clipboard

- **Pure ASGI** (no deprecated BaseHTTPMiddleware).
- Reads `X-Request-ID` from headers or generates one.
- Puts it in `scope["state"]` and `ContextVar` for logging.
- Adds `X-Request-ID` to every response.
- Uses `scope.get("type")` to avoid KeyError on malformed scope.

**Interview Q: "Why request_id?"**
> "For tracing. When something fails, we can correlate logs across services. Each request gets a unique ID in the header and in every log line."

### schemas.py — The Rules

- **IngestTextRequest:** `text` (1–1M chars), `doc_id` (optional, max 256, only `a-zA-Z0-9_-`).
- **IngestDocumentRequest:** Same but `content` instead of `text`.
- **SearchRequest:** `query` (1–10k), `top_k` (1–50).
- **doc_id validator:** Rejects slashes, dots, etc. so chunk IDs stay safe for the vector DB.

### config.py — The Settings

- Pydantic Settings from `.env` / `.env.example`.
- `ENDEE_TOKEN`, `ENDEE_BASE_URL`, `LOG_LEVEL`, `chunk_size`, `index_name`, etc.
- `log_level` validator: only DEBUG, INFO, WARNING, ERROR, CRITICAL.

---

## Chapter 3: The Chunking Algorithm (IMP: Core logic)

**Why chunk?** Embedding models have max input length (~256–512 tokens). A 10-page doc won't fit. We split it.

**Our algorithm (sentence-aware chunking):**

```
1. Split by sentence boundaries (. ! ?)
2. Pack sentences into chunks until we hit max_chunk (512 chars)
3. If a single sentence exceeds 512 chars, force-split it
```

**The clever part:** We respect *sentences* first. "Python is great. It is used for data science." stays as one chunk if it fits—not "Python is great. It" + "is used for data science." (which would be weird).

**Code flow:**
- `re.split(r'(?<=[.!?])\s+', text)` — split after . ! ?
- Accumulate sentences until `current_len + len(s) > max_chunk`
- `flush()` writes the chunk; if it's still too long, split by char

**Interview Q: "Why sentence-aware chunking?"**
> "Keyword search breaks mid-sentence. Semantic search works better when each chunk is a complete thought. We also cap at 512 chars to avoid embedding model overflow."

**Memory trick:** **S-P-F** — Split by sentences, Pack until full, Force-split if oversized.

---

## Chapter 4: Embeddings (The Magic Numbers)

**What is an embedding?** Text → list of 384 floats. Similar meaning → similar vectors.

**Model:** `all-MiniLM-L6-v2` (sentence-transformers)
- 384 dimensions
- Fast, good quality
- Runs locally (no API call)

**Key design choices:**
- **Lazy load:** Model loads on first use (or at lifespan startup). Saves memory if only health check runs.
- **Thread-safe singleton:** `threading.Lock` so two concurrent requests don't load the model twice.
- **Single instance:** One model per process—shared across all requests.

**Interview Q: "Why 384 dimensions?"**
> "Trade-off. Higher dims = more expressiveness but slower and more storage. 384 is a sweet spot for semantic search on documents."

**Interview Q: "What if the embedding model fails?"**
> "We catch exceptions, log them, return 500 with a generic message. Health check returns degraded if model load fails."

---

## Chapter 5: Vector Database (Endee)

**Why a vector DB?** Brute-force: compare query vector to every stored vector = O(n). With 1M docs, that's slow. Vector DBs use **HNSW** (Hierarchical Navigable Small World) for approximate nearest-neighbor in sub-linear time.

**Our setup:**
- **Space:** cosine similarity (angle between vectors)
- **Precision:** INT8D (quantized for speed)
- **Index:** created lazily on first use, cached forever

**Data stored per chunk:**
- `id`: `{doc_id}_{chunk_index}_{uuid8}` — unique, traceable
- `vector`: 384 floats
- `meta`: `{text, doc_id, chunk_index}` — so we can return readable text

**Interview Q: "What's cosine similarity?"**
> "Measure of angle between two vectors. 1 = identical direction, 0 = perpendicular, -1 = opposite. We use it because embeddings are often normalized—magnitude doesn't matter, direction (meaning) does."

**Interview Q: "Why INT8D?"**
> "Quantization: store floats as 8-bit integers. Slight precision loss, big speed and storage gain. For semantic search, it's usually fine."

---

## Chapter 6: The Search Flow (Query → Results)

**Step by step:**
1. User sends `{"query": "Python uses", "top_k": 5}`
2. API validates (non-empty, top_k 1–50)
3. Service embeds the query → 384-d vector
4. DB queries Endee: "give me 5 nearest vectors to this"
5. Endee returns `[{id, similarity, meta}, ...]`
6. We sanitize (safe float, safe id, JSON-safe meta) and return

**Why sanitize?** Endee could return `similarity: null` or `id: 123` (int). We handle malformed responses so we never crash.

**Interview Q: "How do you handle malformed DB responses?"**
> "We wrap float parsing in try/except, coerce id to str, and sanitize meta for JSON serialization. We also guard against circular refs and recursion depth in meta."

---

## Chapter 7: Concurrency & Non-Blocking Design

**Problem:** Embedding and DB calls are **blocking**. If we run them in the main event loop, one slow request blocks all others.

**Solution:** `asyncio.to_thread()` — run sync code in a thread pool. Event loop stays free.

**Where we use it:**
- Ingest, Search, Health — all offload sync work to threads

**Thread-safety:**
- `get_embedding_model()` — Lock around lazy load
- `get_endee_client()` — Lock around client creation
- `ensure_index()` — Lock + cache so we don't hammer list_indexes

**Interview Q: "How do you avoid blocking the event loop?"**
> "We use asyncio.to_thread for all sync operations—embedding, DB calls. The API endpoints are async but delegate to a thread pool for CPU/IO-bound work."

---

## Chapter 8: Error Handling & Resilience

| Scenario | What happens |
|----------|--------------|
| Empty text/query | 422, Pydantic validation |
| Invalid doc_id (special chars) | 422, "doc_id must contain only letters, digits, underscore, hyphen" |
| DB down | 500, "Ingestion failed" / "Search failed" |
| Embedding fails | 500, generic message |
| Health check | 200, `degraded` if DB or embedding unhealthy |

**Design choice:** Clients get generic messages. Full errors stay in logs. No leaking internal details.

**Interview Q: "Why generic 500 messages?"**
> "Security. We don't want to expose stack traces or internal paths. We log the full error server-side and return a safe message."

---

## Chapter 9: Important Edge Cases We Handled

1. **Long single sentence:** No `.!?` for 1000 chars → force-split by 512 chars
2. **Circular meta:** Endee returns `{self: ref}` → `_sanitize_meta` detects cycles, returns `"[cyclic]"`
3. **Recursion depth:** Meta nested 20 levels → cap at 10, return `"[max depth]"`
4. **Validation errors with ValueError in ctx:** Pydantic can put non-JSON-serializable stuff in `exc.errors()` → we use `_json_safe()` before returning
5. **Malformed scope:** ASGI scope missing `type` → `scope.get("type")` instead of `scope["type"]`

**Interview Q: "What edge cases did you consider?"**
> "Long chunks exceeding model limits, circular refs in metadata, non-serializable error payloads, and malformed ASGI scope. We added guards for all of these."

---

## Chapter 9B: Setup, Tests & Deployment (The Run Story)

**The story:** How someone (or an evaluator) gets from clone to "it works."

### Scripts

| Script | What it does |
|--------|--------------|
| `setup-eval.bat` / `.sh` | Light setup: venv, `requirements-eval.txt` (no sentence-transformers), .env |
| `setup.bat` / `.sh` | Full setup: venv, `requirements.txt`, .env |
| `test.bat` / `.sh` | Run pytest from project root |
| `run.bat` / `.sh` | Start uvicorn (API on 8000) |
| `docker-run.bat` / `.sh` | Create .env if missing, then `docker-compose up` |

**Evaluator path:** Clone → `setup-eval` → `test`. No Docker, no token. ~1 min.

### Tests

- **conftest.py:** `client` fixture (TestClient), `mock_endee`, `mock_embeddings` (autouse).
- **test_api.py:** Ingest, search, health, validation (empty, too long, invalid doc_id), 500 on failure, request_id.
- **test_service.py:** Chunking (empty, single, long, caps), ingest/search mocked, malformed Endee response, `_sanitize_meta` circular ref.

**Interview Q: "How do you test without Endee?"**
> "We mock `get_endee_client` and `embed_texts` / `embed_single` at the service layer. Tests never hit the real DB or model."

### Docker

- **Dockerfile:** Python 3.11-slim, copy app, copy .env.example as .env, run uvicorn.
- **docker-compose:** Endee (8080) + API (8000). API uses `ENDEE_BASE_URL=http://endee:8080/api/v1`.
- **docker-run:** Ensures .env exists before compose.

### Endee Fork

- **Fork:** snehaaojha/endee_t1.
- **scripts/start-endee-from-fork.bat** / `.sh`: Clone fork, build, run on 8080.
- **Pre-built:** `docker run ... endeeio/endee-server:latest` — simpler.

---

## Chapter 10: Quick Reference — Interview Cheat Sheet

### One-liners
- **Project:** "Semantic search API: embed text, store in vector DB, query by meaning."
- **Chunking:** "Sentence-aware splitting with 512-char cap to fit embedding model."
- **Embeddings:** "all-MiniLM-L6-v2, 384 dims, lazy-loaded, thread-safe singleton."
- **Vector DB:** "Endee, cosine similarity, HNSW for fast ANN search."
- **Async:** "asyncio.to_thread for sync embedding/DB work so we don't block."

### Numbers to remember
- 384 dimensions
- 512 max chunk chars
- 1M chars max ingest, 10k max query
- top_k 1–50

### File → Responsibility
- `main.py` → Lifespan (preload model), exception handlers, root
- `api.py` → Routes (ingest, search, health), offload to thread
- `service.py` → Chunking, ingest, search, _sanitize_meta
- `embeddings.py` → Model load (lazy, thread-safe), embed_texts, embed_single
- `db.py` → Endee client, ensure_index, upsert, query, generate_chunk_id
- `schemas.py` → Pydantic models, doc_id validation
- `config.py` → Settings from .env
- `middleware.py` → Request ID, X-Request-ID header

---

## Chapter 11: "Tell me about a challenge you solved"

**Good answer (chunking):**  
"We had to split long documents for the embedding model. Pure character splitting broke mid-sentence. I implemented sentence-aware chunking: split on . ! ?, pack sentences until 512 chars, and force-split if a single sentence is too long. That kept chunks meaningful and within model limits."

**Good answer (blocking):**  
"Embedding and DB calls were blocking the FastAPI event loop. I moved them to asyncio.to_thread so the event loop stays responsive under load. We also added threading.Lock for the lazy-loaded embedding model to avoid race conditions."

**Good answer (resilience):**  
"We sanitize all data from the vector DB—float parsing can fail, ids can be non-string, meta can have circular refs. We added try/except, type coercion, and a depth-limited sanitizer so we never crash on malformed responses."

**Good answer (exception handling):**  
"Pydantic validation errors can contain non-JSON-serializable values like ValueError in the ctx. We use _json_safe to recursively sanitize before returning. We also have a generic Exception handler that returns JSON 500 instead of HTML, and _safe_detail for HTTPException so we never fail during response serialization."

**Good answer (observability):**  
"We add X-Request-ID to every request and response. The middleware sets it in scope and a ContextVar so all logs include it. If something fails in production, we can trace the full request path across services."

---

## Chapter 12: Last-Minute Checklist

Before the interview, recite:

1. **Problem:** Semantic search—meaning, not keywords.
2. **Flow:** Ingest: chunk → embed → upsert. Search: embed query → query vectors → return top-k.
3. **Chunking:** Sentence-aware, 512 cap, flush when full.
4. **Embeddings:** all-MiniLM-L6-v2, 384d, lazy, thread-safe.
5. **Vector DB:** Endee, cosine, HNSW.
6. **Async:** to_thread for sync work.
7. **Edge cases:** Long chunks, circular meta, malformed responses.
8. **Supporting cast:** main (lifespan, handlers), middleware (request_id), schemas (doc_id rules), config (env).
9. **Tests:** Mock Endee + embeddings; setup-eval for light run.

**You've got this.**
