## Quickstart – running the project (EN)

This guide walks a **new user** through running the project
for the first time.

---

## 1. Prerequisites

- **Python 3.11+**
  Check your version:

  ```bash
  python --version
  ```

- **Git** – to clone the repository.
- **Azure account with Azure OpenAI** – you need:
  - the endpoint URL (e.g. `https://...openai.azure.com`),
  - an API key,
  - deployment names for the GPT model and the embedding model.
- **(Optional) Email account with SMTP/IMAP** – e.g. Zoho, Gmail:
  - SMTP/IMAP login and password (often an app password),
  - SMTP/IMAP host and port (e.g. `smtp.zoho.eu:587`, `imap.zoho.eu:993`).

> You do **not** need email configured to start;
> the app will still run, but sending/monitoring emails will be disabled.

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
cd BOOK

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

**Minimum required** for AI to work:

| Variable                          | Description                                      |
|-----------------------------------|--------------------------------------------------|
| `AZURE_OPENAI_API_KEY`           | Azure OpenAI API key                             |
| `AZURE_OPENAI_ENDPOINT`          | Azure OpenAI endpoint URL                        |
| `AZURE_OPENAI_GPT_DEPLOYMENT`    | GPT deployment name (e.g. `gpt-4.1-nano`)        |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding deployment (e.g. `text-embedding-3-small`) |

**Optional – email sending and monitoring:**

- `EMAIL_USERNAME`, `EMAIL_PASSWORD`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS`
- `IMAP_HOST`, `IMAP_PORT`
- `EMAIL_MONITOR_ENABLED`
- `IOD_EMAIL`, `HR_EMAIL`, `EMAIL_CHECK_INTERVAL`

> Recommended: start with Azure OpenAI only, then configure email
> once the basic app works.

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
   - generate feedback using Azure OpenAI,
   - validate and optionally correct the email,
   - prepare the email to be sent.

If SMTP is configured, the email will be sent;
otherwise you can still inspect the generated content.

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
  - `AZURE_OPENAI_API_KEY` is set in `.env` without quotes,
  - `AZURE_OPENAI_ENDPOINT` is correct,
  - GPT and embedding deployments exist in Azure.

### 7.2. SMTP/IMAP errors

- **Symptoms:**
  - “Authentication failed”,
  - unable to send emails,
  - IMAP logs mentioning invalid credentials.
- **Check:**
  - whether you use an **app password** if required (Gmail, Zoho),
  - host/port values against your provider’s docs,
  - IMAP/SMTP are enabled for the account,
  - `EMAIL_USERNAME` and `EMAIL_PASSWORD` are correct.

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
