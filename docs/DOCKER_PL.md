## Uruchomienie w Dockerze (PL)

Ten dokument opisuje, jak uruchomić aplikację w kontenerach Docker,
bez konieczności lokalnej instalacji Pythona i zależności.

---

## 1. Wymagania

- **Docker** zainstalowany na maszynie.
- **Docker Compose** – osobno lub w pakiecie z Docker Desktop.

W większości nowoczesnych instalacji dostępne jest polecenie:

```bash
docker compose ...
```

Jeżeli używasz starszej wersji, możesz mieć polecenie:

```bash
docker-compose ...
```

Oba warianty działają z tym samym plikiem `docker-compose.yml`.

### Jak zainstalować Docker i Docker Compose (skrótowo)

- **Docker Desktop (Windows/macOS):** pobierz z [docker.com/get-started](https://www.docker.com/get-started)
  i zainstaluj z ustawieniami domyślnymi (zawiera Docker Engine i Compose).
- **Linux:** skorzystaj z oficjalnej instrukcji instalacji Docker Engine
  dla swojej dystrybucji w dokumentacji [docs.docker.com](https://docs.docker.com/engine/install/).
  Compose V2 jest częścią CLI (`docker compose`).

---

## 2. Przygotowanie pliku `.env`

Przed uruchomieniem kontenerów ustaw zmienne środowiskowe
tak samo, jak dla uruchomienia lokalnego:

```bash
cp .env.example .env
```

**Minimalnie wymagane dla AI:**

- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_GPT_DEPLOYMENT`
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`

**Dla Dockera** szczególnie ważne są:

- `QDRANT_HOST=qdrant`
- `QDRANT_PORT=6333`

(to wartości domyślne używane w `docker-compose.yml`, które kierują
aplikację na kontener `qdrant`).

---

## 3. Uruchomienie aplikacji i Qdrant

Plik `docker-compose.yml` definiuje dwa główne serwisy:

- `app` – aplikacja Flask (`recruitment-ai:latest`),
- `qdrant` – baza wektorowa Qdrant.

Uruchom:

```bash
docker compose up -d
# lub, jeśli masz starszą wersję:
docker-compose up -d
```

Po kilku chwilach:

- aplikacja będzie dostępna pod adresem
  `http://localhost:5000`
- Qdrant pod adresem (API)
  `http://localhost:6333`

W tle zostaną podłączone wolumeny:

- `./data` → `/app/data` – dane aplikacji,
- `./uploads` → `/app/uploads` – wgrywane CV,
- `./qdrant_db` → `/app/qdrant_db` – lokalna baza Qdrant (jeśli używana),
- `qdrant_storage` – named volume dla Qdrant.

---

## 4. Ładowanie bazy wiedzy (RAG) w Dockerze

Aby załadować dokumenty do Qdrant, możesz:

1. Uruchomić loader **w środku kontenera aplikacji**:

   ```bash
   docker compose exec app python knowledge_base/load_to_qdrant.py
   # lub:
   # docker-compose exec app python knowledge_base/load_to_qdrant.py
   ```

   Upewnij się, że pliki `.txt` znajdują się w katalogu `knowledge_base/`
   w repozytorium (są kopiowane do obrazu).

2. Lub uruchomić loader lokalnie, wskazując Qdrant z Dockera:

   ```bash
   export QDRANT_HOST=localhost
   export QDRANT_PORT=6333
   python knowledge_base/load_to_qdrant.py
   ```

---

## 5. Uruchamianie testów w kontenerze

Plik `docker-compose.yml` zawiera dodatkowy serwis:

- `app-test` – używany do uruchamiania testów:

```bash
docker compose --profile test run --rm app-test
# lub:
docker-compose --profile test run --rm app-test
```

Serwis ten buduje ten sam obraz, ustawia testowe zmienne
środowiskowe Azure OpenAI i uruchamia:

- `pytest tests/ -v --cov=... --cov-fail-under=40`

---

## 6. Rozwiązywanie problemów (Troubleshooting)

### 6.1. Kontener natychmiast się wyłącza

- **Objaw:** `docker compose ps` pokazuje status „Exited”.
- **Sprawdź:**
  - logi aplikacji:

    ```bash
    docker compose logs app
    ```

  - czy `.env` zawiera poprawne `AZURE_OPENAI_API_KEY` i inne wymagane
    zmienne,
  - czy nie ma błędów importu (np. brakujący moduł – wtedy warto
    zbudować obraz od nowa).

### 6.2. Brak połączenia z Qdrant

- **Objaw:** błędy „connection refused” albo komunikaty, że nie można
  połączyć się z Qdrant.
- **Sprawdź:**
  - czy serwis `qdrant` działa (`docker compose ps`),
  - czy porty 6333/6334 nie są zajęte przez inny proces,
  - czy w `.env` masz `QDRANT_HOST=qdrant` i `QDRANT_PORT=6333`.

### 6.3. Dane nie są zapisywane między restartami

- Upewnij się, że katalogi `./data`, `./uploads`, `./qdrant_db`
  istnieją i nie są przypadkowo czyszczone,
- sprawdź, czy w `docker-compose.yml` wolumeny są poprawnie podpięte.

---

## 7. Zatrzymywanie i sprzątanie

- Zatrzymanie kontenerów:

  ```bash
  docker compose down
  # lub:
  docker-compose down
  ```

- Zatrzymanie + usunięcie wolumenów (uwaga: stracisz dane!):

  ```bash
  docker compose down -v
  ```
