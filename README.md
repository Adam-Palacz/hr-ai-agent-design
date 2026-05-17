# Recruitment AI – HR Assistant

Web application for HR teams to manage recruitment: review CVs, track candidates through stages, and send AI-generated feedback emails. Includes optional email monitoring (IMAP) with automatic routing and RAG-based answers to candidate inquiries.

## Companion publication

**PL:** To repozytorium jest **materiałem technicznym** (architektura i kod źródłowy) do **case study** omawianego w części technicznej książki Wydawnictwa Difin: *Gotowy plan wdrożenia systemu AI w MŚP. Praktyczna dokumentacja prawna, informatyczna i ocena biznesowa projektu* (ISBN **978-83-8270-509-6**, 2026; autorzy: Damian Dziuba, Joanna Guzik-Jankowska, Adam Palacz, Magdalena Wolańska). Publikacja prowadzi przez wdrożenie AI w MŚP (m.in. regulacje, dokumentacja, biznes); **tu** znajduje się implementacja referencyjna agenta HR — **nie zastępuje** treści merytorycznej książki.

**EN:** This repository is the **technical companion** for the case study in the Difin book *Gotowy plan wdrożenia systemu AI w MŚP…* (ISBN **978-83-8270-509-6**, 2026). The book covers legal, organisational, and business aspects of AI adoption in SMEs; **this repo** provides architecture diagrams and source code for readers who want to inspect a reference implementation — it is **not** a substitute for the book.

## Documentation

- **Online docs (GitHub Pages):**
  - https://adam-palacz.github.io/hr-ai-agent-design/
- **High‑level overview (non‑technical):**
  - Polish: `docs/OVERVIEW_PL.md`
  - English: `docs/OVERVIEW_EN.md`
- **Quickstart guides (from scratch):**
  - Polish (non-technical): `docs/QUICKSTART_NONTECH_PL.md`
  - English (non-technical): `docs/QUICKSTART_NONTECH_EN.md`
  - Polish (full): `docs/QUICKSTART_PL.md`
  - English (full): `docs/QUICKSTART_EN.md`
- **Running with Docker:**
  - Polish: `docs/DOCKER_PL.md`
  - English: `docs/DOCKER_EN.md`
- **Using the app after startup:**
  - Polish: `docs/USER_GUIDE_PL.md`
  - English: `docs/USER_GUIDE_EN.md`
- **Generated API reference (MkDocs + mkdocstrings):**
  - Build and serve locally:

    ```bash
    pip install -r requirements-docs.txt
    mkdocs serve
    ```

    Then open `http://127.0.0.1:8000/` in your browser.

## Features

- **Candidate management** – Add/edit candidates, upload PDF CVs, track status and recruitment stage (initial screening → HR interview → technical assessment → final interview → offer).
- **AI-powered feedback** – On rejection, the system generates personalized, constructive feedback using OpenAI API for local demos or Azure OpenAI for production (CV parsing, validation, and correction agents).
- **Email sending** – Send feedback emails via SMTP (Zoho, Gmail, etc.) with consent messages and privacy policy links.
- **Email monitoring (optional)** – IMAP inbox monitoring; incoming emails are classified and either answered by AI (using basic knowledge or RAG), forwarded to HR, or handled as IOD (e.g. consent changes).
- **RAG knowledge base** – Qdrant vector store for company documents (policies, GDPR/RODO, recruitment info). Used to answer candidate questions and to load context for feedback.
- **Positions & tickets** – Manage job positions and support tickets (e.g. IOD-related).
- **Admin panel** – View candidates, sent emails, tickets, and model response details.

## Tech stack

- **Backend:** Python 3.11, Flask
- **AI:** Azure OpenAI (recommended for production) or OpenAI API (api.openai.com) for local/test — one `LLM_PROVIDER` drives chat and embeddings
- **Vector DB:** Qdrant
- **Database:** SQLite
- **Email:** SMTP (sending), IMAP (monitoring)

## Prerequisites

- Python 3.11+
- Azure OpenAI **or** OpenAI API key (see `LLM_PROVIDER` below)
- SMTP credentials for **sending feedback to candidates** (required for the main workflow); IMAP only if you enable inbox monitoring

## Quick start

**One-command run (after cloning):**

- **Windows (PowerShell):** `.\quickstart.ps1`
- **Linux/macOS (Bash):** `./quickstart.sh` (or `bash quickstart.sh`)

These scripts create a virtual environment (if missing), install dependencies, copy `.env.example` to `.env` on first run (then you edit `.env` and run again), and start the app.

---

### Manual setup

#### 1. Clone and install

```bash
git clone <repository-url>
cd BOOK
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Required for AI and basic run, choose one provider:

**Local/demo with OpenAI API:**

| Variable | Description |
|----------|-------------|
| `LLM_PROVIDER` | Set to `openai` |
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_CHAT_MODEL` | Chat model (e.g. `gpt-4o-mini`) |
| `OPENAI_EMBEDDING_MODEL` | Embedding model for RAG/Qdrant (e.g. `text-embedding-3-small`) |

**Production with Azure OpenAI:**

| Variable | Description |
|----------|-------------|
| `LLM_PROVIDER` | Set to `azure` |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_GPT_DEPLOYMENT` | GPT model deployment name (e.g. `gpt-4.1-nano`) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding model (e.g. `text-embedding-3-small`) |

For production with candidate data, Azure OpenAI is recommended because you can choose
an EU Azure region and better control the data processing location.

Optional – email sending and monitoring:

| Variable | Description |
|----------|-------------|
| `EMAIL_USERNAME` | SMTP/IMAP login |
| `EMAIL_PASSWORD` | SMTP/IMAP password (or app password) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS` | SMTP server (e.g. `smtp.zoho.eu`, `587`, `true`) |
| `IMAP_HOST`, `IMAP_PORT` | IMAP server (e.g. `imap.zoho.eu`, `993`) |
| `EMAIL_MONITOR_ENABLED` | Set to `true` to enable inbox monitoring |
| `IOD_EMAIL` | Email for IOD (e.g. consent) handling |
| `HR_EMAIL` | HR inbox for forwarded queries |
| `EMAIL_CHECK_INTERVAL` | Seconds between IMAP checks (default `60`) |

> The app works with any SMTP/IMAP provider compatible with the configured
> host/port/TLS (Zoho, Gmail, Office 365, etc.). Zoho hostnames in examples
> are just defaults and can be replaced with your provider’s settings.
> For concrete setup examples, see `docs/EMAIL_SETUP_PL.md` (PL) or
> `docs/EMAIL_SETUP_EN.md` (EN).

Other optional: `PRIVACY_POLICY_URL`, `COMPANY_WEBSITE`, `LOG_LEVEL`, `VERBOSE`, `QDRANT_HOST`, `QDRANT_PORT` (when using external Qdrant).

### LLM provider (Azure / OpenAI)

`LLM_PROVIDER` selects the backend for **chat, feedback, and Qdrant embeddings** (RAG):

| `LLM_PROVIDER` | Use case |
|----------------|----------|
| `openai` | **Local / demo** — single `OPENAI_API_KEY` for chat + embeddings; data processed per OpenAI policy. |
| `azure` | **Production** — choose an EU Azure region for data residency and enterprise controls. |

**When `LLM_PROVIDER=azure`:**

- Set `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, GPT and embedding deployment names.

**When `LLM_PROVIDER=openai`:**

- `OPENAI_API_KEY` (required)
- `OPENAI_CHAT_MODEL` (e.g. `gpt-4o-mini`)
- `OPENAI_EMBEDDING_MODEL` (e.g. `text-embedding-3-small`) for RAG / Qdrant
- `OPENAI_BASE_URL` — optional, default `https://api.openai.com/v1`

Restart the app after changing `.env`.

### 3. Database and seed data

The app creates SQLite DB and can seed example data on first run:

```bash
python app.py
```

DB file is created in the project directory (or under `data/` when using Docker).

### 4. Load knowledge base into Qdrant (optional)

If you use RAG for answering candidate emails or for feedback context, put `.txt` files in `knowledge_base/` and run:

```bash
python knowledge_base/load_to_qdrant.py
```

Without `QDRANT_HOST`/`QDRANT_PORT`, the script uses a local Qdrant storage under `./qdrant_db`. If the app is running and using the same path, stop the app first (or use a Qdrant server to avoid lock).

### 5. Run the application

```bash
python app.py
```

Open **http://localhost:5000**. You can:

- Add candidates and upload CVs
- Manage positions and tickets
- Use **Process** (accept/reject) to move candidates and trigger AI feedback emails
- Open **Admin** for full candidate list, sent emails, and tickets

Health check: **http://localhost:5000/health**.

---

## Docker

### Build and run with Docker Compose

Runs the Flask app and Qdrant in separate containers:

```bash
docker-compose up -d
```

- App: **http://localhost:5000**
- Qdrant: **http://localhost:6333** (API), **6334** (gRPC)

Volumes:

- `./data` – app data
- `./uploads` – uploaded CVs
- `./qdrant_db` – local Qdrant data (if not using Qdrant container only for API)
- `qdrant_storage` – named volume for Qdrant persistence

Set all required env vars in `.env` (see **Environment variables** above). For Docker, `QDRANT_HOST=qdrant` and `QDRANT_PORT=6333` are passed by default so the app talks to the Qdrant container.

### Load knowledge base when using Docker

Either:

1. Run the loader **inside** the app container after startup:

   ```bash
   docker-compose exec app python knowledge_base/load_to_qdrant.py
   ```

2. Or run it locally with `QDRANT_HOST=localhost` and `QDRANT_PORT=6333` so it uses the Qdrant from Docker.

---

## Project structure (overview)

```
BOOK/
├── app.py                 # Flask app, routes, email sending, process (accept/reject)
├── config/
│   ├── settings.py        # Pydantic settings from .env
│   └── job_config.py      # Job/position config
├── agents/
│   ├── base_agent.py
│   ├── cv_parser_agent.py
│   ├── feedback_agent.py
│   ├── validation_agent.py
│   ├── correction_agent.py
│   ├── email_classifier_agent.py
│   ├── query_classifier_agent.py
│   ├── query_responder_agent.py
│   └── rag_response_validator_agent.py
├── services/
│   ├── cv_service.py
│   ├── feedback_service.py
│   ├── qdrant_service.py
│   ├── email_sender.py
│   ├── email_monitor.py
│   ├── email_router.py
│   ├── email_listener.py
│   └── metrics_service.py
├── database/
│   ├── models.py          # SQLite schema, CRUD
│   └── seed_data.py
├── knowledge_base/        # .txt files for RAG
│   └── load_to_qdrant.py
├── templates/
├── utils/
├── Dockerfile
├── docker-compose.yml
├── .pre-commit-config.yaml
├── requirements.txt
└── .env.example
```

---

## Testing

Tests use **pytest** and a temporary database (no impact on your real data).

```bash
pip install -r requirements.txt   # includes pytest, pytest-cov
pytest
```

Run with coverage (minimum 40% line coverage; raise over time):

```bash
pytest tests/ --cov=app --cov=config --cov=agents --cov=services --cov=routes --cov=database --cov-report=term-missing --cov-fail-under=40
```

Or from project root: `python -m pytest tests/ -v`

- **Integration tests** (`pytest -m integration`): full feedback pipeline with mocked LLM, including validation-exhaustion path.
- **AI agent tests** (`tests/test_email_classifier_agent.py`, `tests/test_query_classifier_agent.py`): routing/classification logic with mocked LLM.
- **LLM evaluation** (`tests/evaluation_criteria.py` + `tests/test_llm_evaluation.py`):
  - Default `pytest` runs criteria checks and mocked pipelines (no API cost).
  - Real model check: `RUN_LLM_EVAL=1 pytest tests/test_llm_evaluation.py -m evaluation -v` (requires `OPENAI_API_KEY` or Azure credentials per `LLM_PROVIDER`).
  - Live SMTP/E2E (uses `.env`, may send real mail): `LIVE_TEST=1 pytest tests/test_live_integration.py -v -s`
  - Criteria include: valid HTML, length, no PII leak, rejection tone, position mention, no discriminatory phrasing.

**Run tests inside Docker** (same image as production, no Qdrant needed):

```bash
docker-compose --profile test run --rm app-test
```

---

## Pre-commit (optional)

To run Black, Ruff, and general hooks before each commit:

```bash
pip install pre-commit
pre-commit install
```

After that, `git commit` will run the hooks. To run them manually: `pre-commit run --all-files`.

---

## License

See repository license if applicable.
