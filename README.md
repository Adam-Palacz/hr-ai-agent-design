# Recruitment AI – HR Assistant

Web application for HR teams to manage recruitment: review CVs, track candidates through stages, and send AI-generated feedback emails. Includes optional email monitoring (IMAP) with automatic routing and RAG-based answers to candidate inquiries.

## Features

- **Candidate management** – Add/edit candidates, upload PDF CVs, track status and recruitment stage (initial screening → HR interview → technical assessment → final interview → offer).
- **AI-powered feedback** – On rejection, the system generates personalized, constructive feedback using Azure OpenAI (CV parsing, validation, and correction agents).
- **Email sending** – Send feedback emails via SMTP (Zoho, Gmail, etc.) with consent messages and privacy policy links.
- **Email monitoring (optional)** – IMAP inbox monitoring; incoming emails are classified and either answered by AI (using basic knowledge or RAG), forwarded to HR, or handled as IOD (e.g. consent changes).
- **RAG knowledge base** – Qdrant vector store for company documents (policies, GDPR/RODO, recruitment info). Used to answer candidate questions and to load context for feedback.
- **Positions & tickets** – Manage job positions and support tickets (e.g. IOD-related).
- **Admin panel** – View candidates, sent emails, tickets, and model response details.

## Tech stack

- **Backend:** Python 3.11, Flask
- **AI:** Azure OpenAI (GPT, embeddings)
- **Vector DB:** Qdrant
- **Database:** SQLite
- **Email:** SMTP (sending), IMAP (monitoring)

## Prerequisites

- Python 3.11+
- Azure OpenAI endpoint and API key (with GPT and embedding deployments)
- (Optional) SMTP/IMAP credentials for email sending and monitoring

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

Required for AI and basic run:

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_GPT_DEPLOYMENT` | GPT model deployment name (e.g. `gpt-4.1`) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding model (e.g. `text-embedding-3-small`) |

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

Other optional: `PRIVACY_POLICY_URL`, `COMPANY_WEBSITE`, `LOG_LEVEL`, `VERBOSE`, `QDRANT_HOST`, `QDRANT_PORT` (when using external Qdrant).

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
│   ├── cv_parser_agent.py
│   ├── feedback_agent.py
│   ├── validation_agent.py
│   ├── correction_agent.py
│   ├── query_classifier_agent.py
│   └── query_responder_agent.py
├── services/
│   ├── cv_service.py
│   ├── feedback_service.py
│   ├── qdrant_service.py
│   ├── email_monitor.py
│   ├── email_router.py
│   └── email_listener.py
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
