# Contributing to Knowledge Base API

Thanks for your interest in contributing. This guide covers setup and how to run tests.

---

## Setup

### Prerequisites

- Python 3.10+
- For full API: Docker (for Endee)

### Quick setup (evaluators / contributors)

1. **Clone the repo**
   ```bash
   git clone https://github.com/snehaaojha/knowledge-base-api.git
   cd knowledge-base-api
   ```

2. **Create virtual environment and install dependencies**
   ```bash
   # Windows
   scripts\setup-eval.bat

   # Linux / Mac
   bash scripts/setup-eval.sh
   ```

3. **Activate the virtual environment**
   ```bash
   # Windows
   venv\Scripts\activate

   # Linux / Mac
   source venv/bin/activate
   ```

### Full setup (API + Endee)

To run the full API (ingest + search) with Endee:

1. Run setup (use `scripts\setup.bat` or `scripts/setup.sh` for the main venv).
2. Start Endee:
   ```bash
   docker run -d -p 8080:8080 -v endee-data:/data --name endee-server endeeio/endee-server:latest
   ```
   Or use `scripts\docker-run.bat` / `scripts/docker-run.sh` to start Endee + API together.
3. Copy `.env.example` to `.env` and set `ENDEE_BASE_URL=http://localhost:8080/api/v1` (empty token for local Endee).

---

## Running Tests

### Unit and API tests (no Endee required)

```bash
# Windows
scripts\test.bat

# Linux / Mac
bash scripts/test.sh

# Or directly
python -m pytest -v
```

These tests mock Endee and embeddings. You should see multiple tests pass (e.g. 25+).

### Excluding integration tests

Integration tests require a real Endee instance. They are skipped when Endee is not reachable. To explicitly exclude them:

```bash
python -m pytest -v -m "not integration"
```

### Running integration tests (with Endee)

1. Start Endee (see Full setup above).
2. Run:
   ```bash
   python -m pytest tests/test_integration.py -v
   ```

If Endee is not running on port 8080, these tests are automatically skipped.

---

## Test Structure

| Location            | Purpose                                           |
|---------------------|---------------------------------------------------|
| `tests/test_api.py` | HTTP endpoint tests; mocks Endee and embeddings   |
| `tests/test_service.py` | Chunking, ingest/search logic; mocked deps   |
| `tests/test_integration.py` | End-to-end with real Endee; skipped if Endee unavailable |

---

## Code Style

- Follow existing patterns in the codebase.
- Use type hints where appropriate.
- Keep error messages generic for clients; log details server-side.

---

## Questions?

Open an issue on GitHub.
