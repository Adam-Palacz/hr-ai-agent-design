# First run — guide for non-technical users (EN)

This guide is for you if you **do not code every day** but want to **run the Recruitment AI
app on your own computer** and try AI-generated candidate feedback.

**Estimated time:** about 30–60 minutes (first time).  
**OS:** step-by-step for **Windows 10/11**; a short Mac section at the end.

---

## What you will (and will not) do

| In this guide | Later (separate docs) |
|---------------|------------------------|
| Install Python | Email setup (SMTP/IMAP) |
| Download the project | Running with Docker |
| Create an OpenAI API key | Optional: knowledge base (RAG) — same key as chat |
| Run the app in your browser | Full [technical quickstart](QUICKSTART_EN.md) |

You **intentionally skip** in this guide: app email (SMTP), Zoho, app passwords, Docker, and Azure — this is an **AI demo**, not full recruitment.

> **Important:** in normal use the system **emails personalized feedback to the candidate**.
> Without SMTP you can see generated text in the app (admin panel), but the **candidate
> receives nothing**. Full mail setup: [Email setup](EMAIL_SETUP_EN.md).

---

## Checklist

- [ ] Python 3.11+ installed (“Add Python to PATH” ticked)
- [ ] Project folder on disk (ZIP or `git clone`)
- [ ] OpenAI account at platform.openai.com + payment method
- [ ] Copied API key (starts with `sk-`)
- [ ] `.env` file with key and `EMAIL_MONITOR_ENABLED=false`
- [ ] App works at http://localhost:5000
- [ ] Added a candidate with PDF and generated feedback (AI test)

---

## Mini glossary

| Term | Plain language |
|------|----------------|
| **Terminal / PowerShell** | A text window where you type commands instead of clicking in an app. |
| **Project folder** | The `hr-ai-agent-design` directory containing the app files. |
| **`.env` file** | A text file with secrets and settings (API key). **Do not** share it. |
| **API key** | A “password” for OpenAI — the app uses it to generate text. |
| **localhost:5000** | The app address **on your computer** (not public on the internet). |

---

## Step 1 — Install Python (Windows)

1. Go to [python.org/downloads](https://www.python.org/downloads/).
2. Download **Python 3.11** or newer.
3. Run the installer.
4. **Important:** on the first screen tick **“Add python.exe to PATH”**.
5. Click **Install Now** and finish.
6. Check:
   - Press Windows key, type `PowerShell`, open **Windows PowerShell**.
   - Type and press Enter:

     ```powershell
     python --version
     ```

   - You should see something like `Python 3.11.x` or `3.12.x`.

If you get “not recognized”, reinstall Python with PATH enabled.

---

## Step 2 — Download the project

### Option A — no Git (easiest)

1. Open: **https://github.com/Adam-Palacz/hr-ai-agent-design**
2. Click green **Code** → **Download ZIP**.
3. Extract the ZIP.
4. Note the folder path, e.g. `C:\Users\YourName\hr-ai-agent-design`.

### Option B — with Git

```powershell
cd $HOME\Documents
git clone https://github.com/Adam-Palacz/hr-ai-agent-design.git
cd hr-ai-agent-design
```

Do the following steps **inside the project folder** (where `app.py` lives).

**Open PowerShell in that folder (Windows 11):**  
In File Explorer, click the address bar, type `powershell`, press Enter.

---

## Step 3 — OpenAI account and API key

1. Go to [platform.openai.com](https://platform.openai.com/) and sign up or log in.
2. You may need to add a **payment method** — usage is billed per request (set spending limits in billing settings).
3. Open [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
4. Click **Create new secret key**.
5. Name it e.g. `recruitment-ai-test` and confirm.
6. **Copy the key immediately** (starts with `sk-`) into Notepad — you will not see the full key again.

> **Security:** treat the key like a password. Do not email it or paste it in public chats.

---

## Step 4 — Create the `.env` file

The `.env` file tells the app which AI key to use. **In this guide email is turned off.**

### 4.1. Copy the template

In PowerShell (project folder):

```powershell
Copy-Item .env.example .env
```

### 4.2. Open `.env` in Notepad

```powershell
notepad .env
```

### 4.3. Set at least these lines

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=paste-your-sk-key-here
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
EMAIL_MONITOR_ENABLED=false
```

- Paste your real key into `OPENAI_API_KEY` (no quotes, one line).
- Keep `gpt-4o-mini` unless you know another model name from OpenAI’s docs.
- `EMAIL_MONITOR_ENABLED=false` — the app will **not** watch an inbox.

Save and close Notepad.

> If Notepad saves `.env.txt`, rename to `.env` only (enable “File name extensions” in Explorer).

### What you can skip for now

- `EMAIL_*`, `SMTP_*`, `IMAP_*` — see [Email setup](EMAIL_SETUP_EN.md).
- `AZURE_OPENAI_*` — production deployments only ([full quickstart](QUICKSTART_EN.md)); OpenAI is enough for testing.

### Optional: knowledge base (RAG) with the same OpenAI key

If you already have `LLM_PROVIDER=openai` and `OPENAI_API_KEY`:

1. Put `.txt` files in `knowledge_base/`.
2. Stop the app (`Ctrl+C` in PowerShell).
3. Run: `python knowledge_base/load_to_qdrant.py`
4. Start the app again.

> **Production:** for personal data we recommend `LLM_PROVIDER=azure` and an EU Azure region —
> see the table in [Quickstart](QUICKSTART_EN.md).

---

## Step 5 — Start the app (Windows)

### Easier — `quickstart.ps1`

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\quickstart.ps1
```

- **First run:** may install libraries and ask you to edit `.env` — do step 4, then run the script **again**.
- **Second run:** server should start; **leave PowerShell open**.

When you see `http://localhost:5000`, go to step 6.

### Manual fallback

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

---

## Step 6 — Open the app in your browser

1. Open Chrome or Edge.
2. Go to **http://localhost:5000**
3. You should see the Recruitment AI interface.

**Stop the app:** focus PowerShell and press `Ctrl+C`.

---

## Step 7 — First AI test (5 minutes)

1. Add a **position** (e.g. “Sales specialist”).
2. **Add a candidate** with name, email, position, and a **PDF CV**.
3. Open candidate details → add a short **HR note**.
4. Choose **Rejected** / reject with feedback (per UI labels).
5. Wait — the system generates feedback via OpenAI.

Without SMTP, **no email reaches the candidate** — this only tests the AI generator.
After generation, open the app’s **admin panel**:

1. Open **http://localhost:5000/admin** in your browser.
2. Find the **“Sent feedback emails”** section.
3. In the **email content** column you will see the prepared feedback.

The section name says “sent”, but without SMTP this means the email was **prepared and
saved in the app**, not delivered to the candidate. For real use, configure mail per
[Email setup](EMAIL_SETUP_EN.md).

---

## Common problems

### “python is not recognized”

Reinstall Python with **Add python.exe to PATH** (step 1).

### PowerShell blocks `quickstart.ps1`

Run once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Feedback errors (401, 403, “API key”)

- Check `OPENAI_API_KEY` in `.env` (full `sk-...` key, no quotes).
- Check `LLM_PROVIDER=openai`.
- On OpenAI: active billing and usage limits.

### localhost does not open

- Is PowerShell still running without a red error?
- Use `http://` not `https://`.
- Restart: `Ctrl+C`, then `python app.py` or `.\quickstart.ps1`.

### I want real email sending/monitoring

See [Email setup (SMTP/IMAP)](EMAIL_SETUP_EN.md) — separate mailboxes required.

---

## Mac (short)

```bash
cp .env.example .env
# edit .env with the same values as step 4
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Browser: http://localhost:5000 — or `./quickstart.sh` if available.

---

## What’s next?

| Topic | Document |
|-------|----------|
| Full setup (Azure, Docker, RAG) | [Quickstart (EN)](QUICKSTART_EN.md) |
| Non-technical overview | [System overview](OVERVIEW_EN.md) |
| Email | [Email setup](EMAIL_SETUP_EN.md) |
| Docker | [Docker guide](DOCKER_EN.md) |

---

For the first run, **15 minutes with IT** help (Python, PowerShell, `.env`) is normal. Later runs are usually just step 5 and 6.
