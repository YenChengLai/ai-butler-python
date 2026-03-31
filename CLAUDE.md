# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Butler is a LINE Bot personal assistant deployed on GCP Cloud Functions (Gen 2). It uses multiple AI providers (Google Gemini and Anthropic Claude) to manage calendars, track expenses, and maintain a learning memory system via RAG (Retrieval Augmented Generation).

## Commands

### Local Development
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
functions-framework --target=webhook --debug
```

### Lint and Test
```bash
flake8 --count --select=E9,F63,F7,F82 --show-source --statistics .
flake8 --count --max-complexity=10 --max-line-length=127 --statistics .
pytest
```

### Deploy to GCP
```bash
gcloud functions deploy line-bot-function \
  --gen2 --runtime=python311 --region=asia-east1 \
  --source=. --entry-point=webhook --trigger-http \
  --allow-unauthenticated \
  --set-env-vars="LLM_PROVIDER=gemini,..."
```

## Architecture

### Router-Agent-Skill Pattern

```
webhook (main.py)
  → [parallel] EmbeddingService + RouterLLM (intent classification)
  → [parallel] Firestore vector search for memories
  → Agent dispatch: CalendarAgent | ExpenseAgent | ChatAgent
      → Agent LLM parses intent → JSON args
      → Skill layer executes deterministic logic (GCal, Sheets APIs)
      → Flex message templates for LINE rich UI
  → [background] MemoryParser saves interaction to Firestore
```

**Three layers are strictly separated:**
1. **Agents** (`src/agents/`): LLM-powered parsers — intent extraction and argument normalization
2. **Skills** (`src/skills/`): Pure Python business logic — no AI dependencies
3. **Services** (`src/services/`): External API drivers (Google Calendar, Firestore, Sheets)

### Multi-Provider LLM

`LLM_PROVIDER` env var (`gemini` or `claude`) switches all AI calls. Two roles are used:
- **router**: Fast/cheap model for intent classification (`gemini-2.0-flash` / `claude-haiku`)
- **agent**: Stronger model for parsing (`gemini-2.5-pro` / `claude-sonnet`)

Factory: `src/services/llm/factory.py` → `create_llm_provider(role="router"|"agent")`

**Embeddings are always Gemini** (`gemini-embedding-001`, 768-dim) regardless of `LLM_PROVIDER`, to maintain a consistent embedding space in Firestore.

### Async Threading Model

The app runs under WSGI (Gunicorn/Cloud Functions), which is synchronous. A dedicated background event loop runs in a daemon thread (`src/utils/async_helper.py`). The webhook handler submits async work to this loop via `run_coroutine_threadsafe()`.

### Memory System (RAG)

Memories are stored in Firestore with vector embeddings. Retrieval uses cosine similarity with time-decay weighting:
```python
half_lives = {"technical_log": 180, "personal_fact": 99999, "task_note": 7, "daily_log": 30}
score = similarity * (0.5 ** (days_old / half_life))
```

### Scheduled Reports

GitHub Actions workflows trigger daily (`daily_notify.yml`) and weekly (`weekly_notify.yml`) Python scripts that send LINE messages with upcoming schedule summaries.

## Key Configuration

- `src/config.py`: All model names and generation parameters
- `src/prompts/`: System prompts for each agent role
- Environment variables: `LLM_PROVIDER`, `LINE_CHANNEL_SECRET`, `LINE_CHANNEL_ACCESS_TOKEN`, `GOOGLE_APPLICATION_CREDENTIALS_JSON`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `GCAL_CALENDAR_ID`, `SPREADSHEET_ID`, `FIRESTORE_PROJECT_ID`

## Important Conventions

- Async methods on classes are prefixed with `a` (e.g., `agenerate`, `aparse_json_response`)
- Agent `_normalize_args()` methods handle LLM hallucinations (e.g., `summary` → `title` key fixup)
- LINE responses are capped at 5 messages (API limit); agents must respect this
- JSON responses from LLMs are cleaned with Markdown block stripping before `json.loads()`
