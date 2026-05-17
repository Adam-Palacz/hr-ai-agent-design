## Running with Docker (EN)

This document explains how to run the application in Docker
without installing Python and dependencies locally.

---

## 1. Prerequisites

- **Docker** installed on your machine.
- **Docker Compose** – either standalone or via Docker Desktop.

On most modern systems you have:

```bash
docker compose ...
```

On older setups you may have:

```bash
docker-compose ...
```

Both variants work with the same `docker-compose.yml` file.

### Installing Docker and Docker Compose (short version)

- **Docker Desktop (Windows/macOS):** download from [docker.com/get-started](https://www.docker.com/get-started)
  and install with default settings (includes Docker Engine and Compose).
- **Linux:** follow the official Docker Engine install guide for your
  distribution in the docs at [docs.docker.com](https://docs.docker.com/engine/install/).
  Compose V2 is part of the CLI (`docker compose`).

---

## 2. Prepare the `.env` file

Before starting containers, configure environment variables
just like for local runs:

```bash
cp .env.example .env
```

**Minimum required for a local OpenAI demo:**

- `LLM_PROVIDER=openai`
- `OPENAI_API_KEY`
- `OPENAI_CHAT_MODEL` (for example `gpt-4o-mini`)
- `OPENAI_EMBEDDING_MODEL` (for example `text-embedding-3-small`, used by RAG/Qdrant)

This is the simplest demo path: one OpenAI key is enough for feedback generation
and embeddings.

**Recommended for production: Azure OpenAI**

For candidate data and production use, Azure OpenAI is recommended because you can
choose an EU Azure region and better control the data processing location. Set:

- `LLM_PROVIDER=azure`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_GPT_DEPLOYMENT`
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`

**For Docker** it is especially important that:

- `QDRANT_HOST=qdrant`
- `QDRANT_PORT=6333`

These are the defaults used in `docker-compose.yml` so the app
talks to the `qdrant` service.

---

## 3. Start the app and Qdrant

The `docker-compose.yml` file defines two main services:

- `app` – the Flask application (`recruitment-ai:latest`),
- `qdrant` – the Qdrant vector database.

Start them with:

```bash
docker compose up -d
# or, on older setups:
docker-compose up -d
```

After a short while:

- the app will be available at
  `http://localhost:5000`
- Qdrant will be available at (API)
  `http://localhost:6333`

Volumes:

- `./data` → `/app/data` – app data,
- `./uploads` → `/app/uploads` – uploaded CVs,
- `./qdrant_db` → `/app/qdrant_db` – local Qdrant DB (if used),
- `qdrant_storage` – named volume for Qdrant persistence.

---

## 4. Loading the knowledge base (RAG) in Docker

To load documents into Qdrant you can:

1. Run the loader **inside the app container**:

   ```bash
   docker compose exec app python knowledge_base/load_to_qdrant.py
   # or:
   # docker-compose exec app python knowledge_base/load_to_qdrant.py
   ```

   Make sure `.txt` files are present in the `knowledge_base/` folder
   in the repository (they are copied into the image).

2. Or run the loader locally pointing to Qdrant in Docker:

   ```bash
   export QDRANT_HOST=localhost
   export QDRANT_PORT=6333
   python knowledge_base/load_to_qdrant.py
   ```

---

## 5. Running tests inside the container

`docker-compose.yml` defines an additional service:

- `app-test` – used to run tests:

```bash
docker compose --profile test run --rm app-test
# or:
docker-compose --profile test run --rm app-test
```

This service builds the same image, sets test‑friendly Azure OpenAI
environment variables and runs:

- `pytest tests/ -v --cov=... --cov-fail-under=40`

---

## 6. Troubleshooting

### 6.1. Container exits immediately

- **Symptom:** `docker compose ps` shows status “Exited”.
- **Check:**
  - app logs:

    ```bash
    docker compose logs app
    ```

  - whether `.env` contains a valid `OPENAI_API_KEY` with `LLM_PROVIDER=openai`,
    or valid `AZURE_OPENAI_*` variables with `LLM_PROVIDER=azure`,
  - whether there are import errors (missing modules – in that case
    rebuild the image).

### 6.2. Cannot connect to Qdrant

- **Symptom:** “connection refused” or similar errors.
- **Check:**
  - that the `qdrant` service is running (`docker compose ps`),
  - ports 6333/6334 are free,
  - `.env` has `QDRANT_HOST=qdrant` and `QDRANT_PORT=6333`.

### 6.3. Data is not persisted between restarts

- Make sure directories `./data`, `./uploads`, `./qdrant_db`
  exist and are not cleaned between runs,
- check that volumes are correctly mounted in `docker-compose.yml`.

---

## 7. Stopping and cleaning up

- Stop containers:

  ```bash
  docker compose down
  # or:
  docker-compose down
  ```

- Stop and remove volumes (warning: this deletes data!):

  ```bash
  docker compose down -v
  ```
