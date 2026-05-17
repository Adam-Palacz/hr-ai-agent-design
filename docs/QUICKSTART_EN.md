## Quickstart – running the project (EN)

This guide walks a **new user** through running the project
for the first time.

> **Non-technical first run (~30 min, no email or Docker):**
> [First run – non-technical guide](QUICKSTART_NONTECH_EN.md)

---

## 1. Prerequisites

- **Python 3.11+**
  Check your version:

  ```bash
  python --version
  ```

- **Git** – to clone the repository.
- **LLM account (choose one):**
  - **OpenAI API**: simplest for a local demo; API key (`OPENAI_API_KEY`) and model name (`OPENAI_CHAT_MODEL`),
  - **Azure OpenAI**: recommended for production; endpoint URL, API key, GPT/embedding deployment names in your selected Azure region, preferably in the EU.
- **(Optional) Email with SMTP + IMAP** – see [Email setup](EMAIL_SETUP_EN.md):
  - **SMTP** = sending mail; **IMAP** = reading the monitored inbox.
  - You need **at least three different addresses** for demos (bot inbox, HR, IOD).
  - **Never** set `HR_EMAIL` or `IOD_EMAIL` to the same address as `EMAIL_USERNAME`
    (infinite processing loop). Zoho is used in examples because it allows several
    mailboxes on one domain; any provider with multiple inboxes works too.

> **Email and the product goal:** the main flow is **sending personalized feedback by
> email to the candidate** — that requires SMTP (`EMAIL_USERNAME`, `EMAIL_PASSWORD`,
> hosts). Without mail, the app **starts** and **generates** feedback text (AI), but
> **does not deliver** it to the candidate — you only see it in the admin UI. This
> guide assumes full setup; UI/AI-only trial without sending:
> [non-technical guide](QUICKSTART_NONTECH_EN.md).

### Where to get API keys and model settings?

- **Azure OpenAI:**
  1. Open Azure AI Foundry / Azure Portal and select your Azure OpenAI resource.
  2. Copy the **endpoint** and **API key**.
  3. Check deployment names (chat + embedding) and set
     `AZURE_OPENAI_GPT_DEPLOYMENT` and `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`.
- **OpenAI API:**
  1. Open OpenAI platform and create an **API key**.
  2. Put it in `.env` as `OPENAI_API_KEY`.
  3. Set `OPENAI_CHAT_MODEL` and `LLM_PROVIDER=openai`.

### Official sources / docs

**LLM (what you are configuring):**

- [OpenAI platform overview](https://platform.openai.com/docs/overview) — what the API is
  and how billing/models work.
- [OpenAI API keys](https://platform.openai.com/api-keys) — create the secret you put in
  `OPENAI_API_KEY` (treat it like a password; do not commit it).
- [Azure OpenAI on Microsoft Learn](https://learn.microsoft.com/azure/ai-services/openai/) —
  resources, deployments, and quotas for `AZURE_OPENAI_*` variables.
- [Azure AI Foundry](https://ai.azure.com/) — portal to copy endpoint, key, and deployment names.

**Email (only if you enable monitoring):** full walkthrough in
[Email setup (SMTP/IMAP)](EMAIL_SETUP_EN.md) — SMTP/IMAP basics, separate mailboxes, Zoho/Gmail steps.

### Installing Python and Git (short version)

- **Python:** go to [python.org/downloads](https://www.python.org/downloads/),
  download the installer for your OS and during installation tick
  “Add Python to PATH”.
  On Linux/macOS you can also use your package manager (`apt`, `dnf`, `brew`, etc.).
- **Git:** download the installer from [git-scm.com](https://git-scm.com/downloads)
  and install with default options. On Linux/macOS Git is usually available
  via the system package manager.

---

## 2. Clone the repo and install dependencies

```bash
git clone <REPO_URL>
cd hr-ai-agent-design

python -m venv venv

# Windows (PowerShell):
venv\Scripts\activate

# Linux/macOS (Bash):
# source venv/bin/activate

pip install -r requirements.txt
```

If `pip` is missing, make sure you are using the same Python
that created the virtual environment.

---

## 3. `.env` file – environment configuration

Copy the example file and fill in values:

```bash
cp .env.example .env
```

The app supports **two LLM providers**:

1. **OpenAI API** (`LLM_PROVIDER=openai`) — simplest for a local demo.
2. **Azure OpenAI** (`LLM_PROVIDER=azure`) — recommended for production and personal data.

### Option A: OpenAI API (local demo)

| Variable           | Description                                        |
|--------------------|----------------------------------------------------|
| `LLM_PROVIDER`     | `openai`                                           |
| `OPENAI_API_KEY`   | OpenAI API key                                     |
| `OPENAI_CHAT_MODEL`| Chat model name (e.g. `gpt-4o-mini`)              |
| `OPENAI_EMBEDDING_MODEL` | Embedding / RAG model (e.g. `text-embedding-3-small`) |
| `OPENAI_BASE_URL`  | Optional, default `https://api.openai.com/v1`     |

### Option B: Azure OpenAI (production)

| Variable                          | Description                                      |
|-----------------------------------|--------------------------------------------------|
| `LLM_PROVIDER`                    | `azure`                                          |
| `AZURE_OPENAI_API_KEY`           | Azure OpenAI API key                             |
| `AZURE_OPENAI_ENDPOINT`          | Azure OpenAI endpoint URL                        |
| `AZURE_OPENAI_GPT_DEPLOYMENT`    | GPT deployment name (e.g. `gpt-4o-mini`)         |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding deployment (e.g. `text-embedding-3-small`) |

For production, choose an Azure region that matches your organization’s
requirements; for candidate data, an EU region is recommended.

### Which provider to choose?

| Environment | `LLM_PROVIDER` | Why |
|-------------|----------------|-----|
| **Local test / dev** | `openai` | One `OPENAI_API_KEY` for chat, feedback, **and** Qdrant (RAG). |
| **Production / personal data** | `azure` | Recommended: EU Azure region, data residency and enterprise policy. |

With `LLM_PROVIDER=openai`, embeddings use `OPENAI_EMBEDDING_MODEL` (default
`text-embedding-3-small`). With `azure`, use `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`.

**Optional – email sending and monitoring:**

- `EMAIL_USERNAME`, `EMAIL_PASSWORD` — login for **IMAP (listen)** and **SMTP (send)**.
- `SMTP_*`, `IMAP_*` — server hostnames/ports from your provider.
- `EMAIL_MONITOR_ENABLED`, `EMAIL_CHECK_INTERVAL` — background inbox polling.
- `IOD_EMAIL`, `HR_EMAIL` — **other** mailboxes for forwards (must differ from `EMAIL_USERNAME`).

> Recommended: start with one LLM provider only (Azure or OpenAI), then configure email
> once the basic app works. Before enabling the monitor, read
> [Email setup – separate mailboxes](EMAIL_SETUP_EN.md#critical-separate-mailboxes-avoid-infinite-loops).

---

## 4. First run

With the virtual environment active, run:

```bash
python app.py
```

By default the app will start on:

- `http://localhost:5000`

On the first run, the app will create a SQLite database and may seed
example data.

---

## 5. First steps in the UI

1. Open `http://localhost:5000` in your browser.
2. **Add a position** (menu “Positions”), e.g. “Software Engineer”.
3. **Add a candidate**:
   - first name, last name, email,
   - assign a position,
   - upload a CV (PDF file).
4. **Open candidate details** and check that the CV preview works.
5. **Add an HR note and choose a decision** (via the “Process”/“Reject with feedback” flow):
   - write a meaningful note (what matched, what did not),
   - choose “Rejected”.
6. The system will:
   - parse the CV,
   - generate feedback using the selected LLM provider (Azure OpenAI or OpenAI API),
   - validate and optionally correct the email,
   - prepare the email to be sent.

If SMTP is configured, the email is delivered to the candidate.
Without SMTP, content is stored and visible in the admin panel (sent emails section),
at **http://localhost:5000/admin**, in the **“Sent feedback emails”** section,
but that **does not replace** real recruitment communication.

---

## 6. Optional: company knowledge base (RAG)

If you want the system to answer questions based on company documents:

1. Put `.txt` files into the `knowledge_base/` directory.
2. Run the loader:

   ```bash
   python knowledge_base/load_to_qdrant.py
   ```

3. Make sure Qdrant is running:
   - either as a local file‑based DB (`./qdrant_db`),
   - or via Docker (see `DOCKER_EN.md`).

---

## 7. Common issues

### 7.1. Missing or invalid API key

- **Symptoms:**
  - errors at startup,
  - errors when generating feedback (401/403 from Azure).
- **Check:**
  - with `LLM_PROVIDER=openai`: `OPENAI_API_KEY` is set without quotes and OpenAI billing is active,
  - with `LLM_PROVIDER=azure`: `AZURE_OPENAI_API_KEY` is set without quotes,
  - `AZURE_OPENAI_ENDPOINT` is correct for Azure,
  - GPT and embedding deployments exist in Azure if you use Azure.

### 7.2. SMTP/IMAP errors

- **Symptoms:**
  - “Authentication failed”,
  - unable to send emails,
  - IMAP logs mentioning invalid credentials,
  - the same messages processed again and again.
- **Check:**
  - whether you use an **app password** if required (Gmail, Zoho),
  - host/port values against your provider’s docs,
  - IMAP/SMTP are enabled for the account,
  - `EMAIL_USERNAME` and `EMAIL_PASSWORD` are correct,
  - `HR_EMAIL` and `IOD_EMAIL` are **not** the same as `EMAIL_USERNAME`
    ([details](EMAIL_SETUP_EN.md#critical-separate-mailboxes-avoid-infinite-loops)).

### 7.3. Qdrant not starting / “connection refused”

- **Symptoms:**
  - connection errors when running the loader or using RAG,
  - “connection refused” or “database locked” messages.
- **Check:**
  - that Qdrant is running:
    - locally (`./qdrant_db`),
    - or as a Docker container on port `6333`,
  - `QDRANT_HOST` / `QDRANT_PORT` in `.env` match the actual location,
  - you don’t run two processes using the same file‑based DB
    (`qdrant_db`) at the same time.

### 7.4. `ModuleNotFoundError` or missing dependencies

- **Symptoms:** module import errors.
- **Fix:**

  ```bash
  # Ensure venv is active, then:
  pip install -r requirements.txt
  ```

---

## 8. Where next?

- High‑level overview for non‑technical readers:
  - [System overview](OVERVIEW_EN.md)
- Docker‑based run (no local Python install):
  - [Docker guide](DOCKER_EN.md)
