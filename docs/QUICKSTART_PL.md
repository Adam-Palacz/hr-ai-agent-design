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
- **Konto LLM (wybierz jedno):**
  - **Azure OpenAI**: endpoint, klucz API, nazwy deploymentów GPT/embedding,
  - **albo OpenAI API**: klucz API (`OPENAI_API_KEY`) i nazwa modelu (`OPENAI_CHAT_MODEL`).
- **(Opcjonalnie) konto e‑mail ze wsparciem SMTP/IMAP** – np. Zoho, Gmail:
  - SMTP/IMAP login i hasło (często tzw. „app password”),
  - host i port SMTP/IMAP (np. `smtp.zoho.eu:587`, `imap.zoho.eu:993`).

> Nie musisz konfigurować e‑maili na start – aplikacja nadal się uruchomi,
> ale wysyłka maili i monitorowanie skrzynki będą nieaktywne.

### Skąd wziąć klucze API i dane do modeli?

- **Azure OpenAI:**
  1. Wejdź do Azure AI Foundry / Azure Portal i otwórz zasób Azure OpenAI.
  2. Skopiuj **endpoint** i **API key**.
  3. Sprawdź nazwy deploymentów modeli (chat + embedding) i wpisz je do `.env`
     jako `AZURE_OPENAI_GPT_DEPLOYMENT` oraz `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`.
- **OpenAI API:**
  1. Wejdź na platformę OpenAI i wygeneruj **API key**.
  2. Wpisz go do `.env` jako `OPENAI_API_KEY`.
  3. Ustaw `OPENAI_CHAT_MODEL` (np. `gpt-4.1-nano`) i `LLM_PROVIDER=openai`.

> Jeśli nie masz pewności, który wariant wybrać: zacznij od Azure (domyślny),
> a później przetestuj OpenAI zmieniając tylko `LLM_PROVIDER` i zmienne `OPENAI_*`.

### Oficjalne źródła / dokumentacja

- OpenAI API – przegląd platformy i dokumentacja: <https://platform.openai.com/docs/overview>
- OpenAI API keys: <https://platform.openai.com/api-keys>
- Azure OpenAI Service – dokumentacja Microsoft Learn: <https://learn.microsoft.com/azure/ai-services/openai/>
- Azure AI Foundry – portal: <https://ai.azure.com/>

- Gmail SMTP/IMAP (oficjalna pomoc Google): <https://support.google.com/mail/answer/7126229>
- Zoho Mail IMAP/SMTP (oficjalna dokumentacja): <https://www.zoho.com/mail/help/imap-access.html>
- Microsoft 365 SMTP AUTH / IMAP (Microsoft Learn): <https://learn.microsoft.com/exchange/clients-and-mobile-in-exchange-online/authenticated-client-smtp-submission>

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
cd hr-ai-agent-design

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

Aplikacja obsługuje **dwa providery LLM**:

1. **Azure OpenAI** (`LLM_PROVIDER=azure`, domyślnie)
2. **OpenAI API** (`LLM_PROVIDER=openai`)

### Wariant A: Azure OpenAI (domyślny)

| Zmienna                          | Opis                                       |
|----------------------------------|--------------------------------------------|
| `LLM_PROVIDER`                   | `azure`                                    |
| `AZURE_OPENAI_API_KEY`          | Klucz API Azure OpenAI                     |
| `AZURE_OPENAI_ENDPOINT`         | Endpoint Azure OpenAI                      |
| `AZURE_OPENAI_GPT_DEPLOYMENT`   | Nazwa deploymentu modelu GPT (np. `gpt-4.1-nano`) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Nazwa deploymentu embeddingu (np. `text-embedding-3-small`) |

### Wariant B: OpenAI API

| Zmienna              | Opis                                            |
|----------------------|-------------------------------------------------|
| `LLM_PROVIDER`       | `openai`                                        |
| `OPENAI_API_KEY`     | Klucz API OpenAI                                |
| `OPENAI_CHAT_MODEL`  | Model czatu (np. `gpt-4.1-nano`)                |
| `OPENAI_BASE_URL`    | Opcjonalnie, domyślnie `https://api.openai.com/v1` |

> Uwaga: nawet przy `LLM_PROVIDER=openai` część funkcji pomocniczych może nadal
> korzystać z ustawień Azure, jeśli zostaną jawnie wymuszone w kodzie.
> Dla typowego uruchomienia aplikacji wystarczy poprawna konfiguracja wybranego providera.

**Opcjonalne – wysyłka maili i monitoring:**

- `EMAIL_USERNAME`, `EMAIL_PASSWORD`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS`
- `IMAP_HOST`, `IMAP_PORT`
- `EMAIL_MONITOR_ENABLED` (`true`/`false`)
- `IOD_EMAIL`, `HR_EMAIL`, `EMAIL_CHECK_INTERVAL`

Pełna instrukcja konfiguracji skrzynek (Zoho/Gmail/Office 365) jest tutaj:
- [Konfiguracja e‑mail (SMTP/IMAP)](EMAIL_SETUP_PL.md)

> Dobra praktyka: najpierw uruchom system tylko z jednym providerem LLM (Azure albo OpenAI),
> a dopiero potem dodaj konfigurację e‑maili.

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
   - wygeneruje feedback z użyciem wybranego providera LLM (Azure OpenAI albo OpenAI API),
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
