## Szybki start – uruchomienie projektu (PL)

Ten przewodnik prowadzi krok po kroku osobę,
która **nigdy wcześniej nie uruchamiała tego projektu**.

---

## 1. Wymagania wstępne

- **Python 3.11+**
  Sprawdź wersję:

  ```bash
  python --version
  ```

- **Git** – do sklonowania repozytorium.
- **Konto Azure z usługą Azure OpenAI** – potrzebujesz:
  - endpointu (URL, np. `https://...openai.azure.com`),
  - klucza API,
  - nazw deploymentów dla modelu GPT i embeddingu.
- **(Opcjonalnie) konto e‑mail ze wsparciem SMTP/IMAP** – np. Zoho, Gmail:
  - SMTP/IMAP login i hasło (często tzw. „app password”),
  - host i port SMTP/IMAP (np. `smtp.zoho.eu:587`, `imap.zoho.eu:993`).

> Nie musisz konfigurować e‑maili na start – aplikacja nadal się uruchomi,
> ale wysyłka maili i monitorowanie skrzynki będą nieaktywne.

### Jak zainstalować Python i Git (skrótowo)

- **Python:** wejdź na stronę [python.org/downloads](https://www.python.org/downloads/),
  pobierz instalator dla swojego systemu i podczas instalacji zaznacz
  opcję „Add Python to PATH”.
  Na Linux/macOS możesz też użyć menedżera pakietów (`apt`, `dnf`, `brew`, itp.).
- **Git:** pobierz instalator z [git-scm.com](https://git-scm.com/downloads)
  i zainstaluj z ustawieniami domyślnymi. W systemach Linux/macOS
  Git jest zwykle dostępny z menedżera pakietów.

---

## 2. Klonowanie repozytorium i instalacja zależności

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

Jeśli nie masz `pip` w PATH – upewnij się, że używasz tego samego Pythona,
którym tworzyłeś wirtualne środowisko.

---

## 3. Plik `.env` – konfiguracja środowiska

Skopiuj plik przykładowy i wypełnij wartości:

```bash
cp .env.example .env
```

**Minimalnie wymagane**, aby AI działało:

| Zmienna                          | Opis                                       |
|----------------------------------|--------------------------------------------|
| `AZURE_OPENAI_API_KEY`          | Klucz API Azure OpenAI                     |
| `AZURE_OPENAI_ENDPOINT`         | Endpoint Azure OpenAI                      |
| `AZURE_OPENAI_GPT_DEPLOYMENT`   | Nazwa deploymentu modelu GPT (np. `gpt-4.1-nano`) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Nazwa deploymentu embeddingu (np. `text-embedding-3-small`) |

**Opcjonalne – wysyłka maili i monitoring:**

- `EMAIL_USERNAME`, `EMAIL_PASSWORD`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS`
- `IMAP_HOST`, `IMAP_PORT`
- `EMAIL_MONITOR_ENABLED` (`true`/`false`)
- `IOD_EMAIL`, `HR_EMAIL`, `EMAIL_CHECK_INTERVAL`

> Dobra praktyka: najpierw uruchom system tylko z Azure OpenAI, a dopiero
> potem dodaj konfigurację e‑maili.

---

## 4. Pierwsze uruchomienie aplikacji

Upewnij się, że wirtualne środowisko jest aktywne (`venv`),
potem uruchom:

```bash
python app.py
```

Domyślnie aplikacja startuje na:

- `http://localhost:5000`

Przy pierwszym uruchomieniu zostanie utworzona baza SQLite
i (opcjonalnie) załadowane dane przykładowe.

---

## 5. Pierwsze kroki w UI

1. **Wejdź na** `http://localhost:5000`.
2. **Dodaj stanowisko** (menu „Positions”), np. „Software Engineer”.
3. **Dodaj kandydata**:
   - imię, nazwisko, e‑mail,
   - przypisz do stanowiska,
   - załaduj plik CV (PDF).
4. **Otwórz szczegóły kandydata**, sprawdź czy CV jest widoczne.
5. **Dodaj notatkę HR i wybierz decyzję** (w widoku „Process”/„Reject with feedback”):
   - wpisz sensowną notatkę (co było dobre, co nie pasowało),
   - wybierz „Odrzucony”.
6. System:
   - przetworzy CV,
   - wygeneruje feedback z użyciem Azure OpenAI,
   - zwaliduje go i ewentualnie poprawi,
   - przygotuje maila do wysłania.

Jeżeli SMTP jest skonfigurowane, mail zostanie wysłany;
w przeciwnym razie możesz przynajmniej podejrzeć wygenerowaną treść.

---

## 6. Opcjonalnie: wiedza firmy (RAG)

Jeśli chcesz, żeby system odpowiadał na pytania na podstawie
dokumentów firmy:

1. Umieść pliki `.txt` w katalogu `knowledge_base/`.
2. Uruchom loader:

   ```bash
   python knowledge_base/load_to_qdrant.py
   ```

3. Upewnij się, że Qdrant działa lokalnie (domyślna ścieżka `./qdrant_db`)
   albo przez Docker (patrz `DOCKER_PL.md`).

---

## 7. Najczęstsze problemy (Common issues)

### 7.1. Brak lub błędny klucz API

- **Objawy:**
  - błąd przy starcie aplikacji,
  - błędy przy generowaniu feedbacku (np. 401 / 403 z Azure).
- **Sprawdź:**
  - czy w `.env` masz `AZURE_OPENAI_API_KEY` bez cudzysłowów,
  - czy endpoint (`AZURE_OPENAI_ENDPOINT`) jest poprawny,
  - czy deploymenty GPT/embedding istnieją w Azure.

### 7.2. Błędy SMTP/IMAP (logowanie do poczty)

- **Objawy:**
  - „Authentication failed”,
  - brak możliwości wysyłki maili,
  - logi z IMAP z informacją o błędnym loginie/haśle.
- **Sprawdź:**
  - czy używasz **app password**, jeśli dostawca tego wymaga (Gmail, Zoho),
  - czy host/port są poprawne (patrz dokumentacja dostawcy),
  - czy IMAP/SMTP jest włączone na koncie (np. w ustawieniach Gmail/Zoho),
  - czy `EMAIL_USERNAME` i `EMAIL_PASSWORD` są prawidłowe.

### 7.3. Qdrant nie startuje / „connection refused”

- **Objawy:**
  - błędy połączenia przy uruchamianiu loadera lub korzystaniu z RAG,
  - logi typu „connection refused” lub „database locked”.
- **Sprawdź:**
  - czy Qdrant działa:
    - lokalnie (folder `./qdrant_db`),
    - lub jako kontener Docker (port `6333`),
  - czy `QDRANT_HOST`/`QDRANT_PORT` w `.env` są zgodne z tym,
    gdzie faktycznie działa Qdrant,
  - czy nie masz dwóch procesów korzystających z tej samej bazy plikowej
    (`qdrant_db`) jednocześnie.

### 7.4. `ModuleNotFoundError` lub problemy z zależnościami

- **Objawy:** brak modułu przy imporcie.
- **Rozwiązanie:**
  - upewnij się, że aktywowałeś wirtualne środowisko (`venv`),
  - uruchom ponownie:

    ```bash
    pip install -r requirements.txt
    ```

---

## 8. Gdzie dalej?

- Krótki, nie‑techniczny opis systemu:
  - [Przegląd systemu](OVERVIEW_PL.md)
- Szczegóły uruchomienia w Dockerze:
  - [Uruchomienie w Dockerze](DOCKER_PL.md)
