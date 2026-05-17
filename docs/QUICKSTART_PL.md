## Szybki start – uruchomienie projektu (PL)

Ten przewodnik prowadzi krok po kroku osobę,
która **nigdy wcześniej nie uruchamiała tego projektu**.

> **Nietechniczny start (~30 min, bez poczty i Dockera):**
> [Pierwsze uruchomienie – przewodnik nietechniczny](QUICKSTART_NONTECH_PL.md)

---

## 1. Wymagania wstępne

- **Python 3.11+**
  Sprawdź wersję:

  ```bash
  python --version
  ```

- **Git** – do sklonowania repozytorium.
- **Konto LLM (wybierz jedno):**
  - **OpenAI API**: najprostsze do demo lokalnego; klucz API (`OPENAI_API_KEY`) i nazwa modelu (`OPENAI_CHAT_MODEL`),
  - **Azure OpenAI**: zalecane dla produkcji; endpoint, klucz API, nazwy deploymentów GPT/embedding w wybranym regionie Azure, najlepiej w UE.
- **(Opcjonalnie) poczta ze SMTP + IMAP** – patrz [Konfiguracja e‑mail](EMAIL_SETUP_PL.md):
  - **SMTP** = wysyłka; **IMAP** = odczyt monitorowanej skrzynki.
  - Do demo potrzebujesz **co najmniej trzech różnych adresów** (bot, HR, IOD).
  - **Nigdy** nie ustawiaj `HR_EMAIL` ani `IOD_EMAIL` na ten sam adres co `EMAIL_USERNAME`
    (ryzyko nieskończonej pętli). W przykładach jest Zoho, bo łatwo założyć kilka skrzynek
    w jednej domenie; możesz użyć dowolnego dostawcy z wieloma skrzynkami.

> **Poczta a sens aplikacji:** główny scenariusz to **wysłanie spersonalizowanego
> feedbacku mailem do kandydata** — do tego potrzebujesz SMTP (`EMAIL_USERNAME`,
> `EMAIL_PASSWORD`, hosty). Bez poczty aplikacja **się uruchomi** i **wygeneruje**
> treść feedbacku (AI), ale **nie dostarczy** jej kandydatowi — zobaczysz ją tylko
> w panelu (np. administracja). Ten przewodnik techniczny zakłada pełną konfigurację;
> sam test UI/AI bez wysyłki: [przewodnik nietechniczny](QUICKSTART_NONTECH_PL.md).

### Skąd wziąć klucze API i dane do modeli?

- **Azure OpenAI:**
  1. Wejdź do Azure AI Foundry / Azure Portal i otwórz zasób Azure OpenAI.
  2. Skopiuj **endpoint** i **API key**.
  3. Sprawdź nazwy deploymentów modeli (chat + embedding) i wpisz je do `.env`
     jako `AZURE_OPENAI_GPT_DEPLOYMENT` oraz `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`.
- **OpenAI API:**
  1. Wejdź na platformę OpenAI i wygeneruj **API key**.
  2. Wpisz go do `.env` jako `OPENAI_API_KEY`.
  3. Ustaw `OPENAI_CHAT_MODEL` (np. `gpt-4o-mini`) i `LLM_PROVIDER=openai`.

> Jeśli robisz lokalne demo, zacznij od OpenAI API (`LLM_PROVIDER=openai`).
> Jeśli planujesz pracę z prawdziwymi danymi kandydatów, użyj Azure OpenAI
> w regionie UE ze względu na kontrolę lokalizacji przetwarzania danych.

### Oficjalne źródła / dokumentacja

**LLM (co konfigurujesz):**

- [Przegląd platformy OpenAI](https://platform.openai.com/docs/overview) — czym jest API,
  modele i rozliczenia.
- [Klucze API OpenAI](https://platform.openai.com/api-keys) — sekret do `OPENAI_API_KEY`
  (jak hasło; nie commituj go do repozytorium).
- [Azure OpenAI – Microsoft Learn](https://learn.microsoft.com/azure/ai-services/openai/) —
  zasoby, deploymenty i limity dla zmiennych `AZURE_OPENAI_*`.
- [Azure AI Foundry](https://ai.azure.com/) — portal: endpoint, klucz, nazwy deploymentów.

**Poczta (tylko przy włączonym monitorze):** pełna instrukcja w
[Konfiguracja e‑mail (SMTP/IMAP)](EMAIL_SETUP_PL.md) — SMTP/IMAP, osobne skrzynki, Zoho/Gmail.

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

1. **OpenAI API** (`LLM_PROVIDER=openai`) — najprostsze dla demo lokalnego.
2. **Azure OpenAI** (`LLM_PROVIDER=azure`) — zalecane dla produkcji i danych osobowych.

### Wariant A: OpenAI API (demo lokalne)

| Zmienna              | Opis                                            |
|----------------------|-------------------------------------------------|
| `LLM_PROVIDER`       | `openai`                                        |
| `OPENAI_API_KEY`     | Klucz API OpenAI                                |
| `OPENAI_CHAT_MODEL`  | Model czatu (np. `gpt-4o-mini`)                 |
| `OPENAI_EMBEDDING_MODEL` | Model embeddingów / RAG (np. `text-embedding-3-small`) |
| `OPENAI_BASE_URL`    | Opcjonalnie, domyślnie `https://api.openai.com/v1` |

### Wariant B: Azure OpenAI (produkcja)

| Zmienna                          | Opis                                       |
|----------------------------------|--------------------------------------------|
| `LLM_PROVIDER`                   | `azure`                                    |
| `AZURE_OPENAI_API_KEY`          | Klucz API Azure OpenAI                     |
| `AZURE_OPENAI_ENDPOINT`         | Endpoint Azure OpenAI                      |
| `AZURE_OPENAI_GPT_DEPLOYMENT`   | Nazwa deploymentu modelu GPT (np. `gpt-4o-mini`) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Nazwa deploymentu embeddingu (np. `text-embedding-3-small`) |

W produkcji wybierz region Azure zgodny z wymaganiami organizacji; dla danych
kandydatów rekomendowany jest region w UE.

### Który provider wybrać?

| Środowisko | `LLM_PROVIDER` | Dlaczego |
|------------|----------------|----------|
| **Test / dev lokalny** | `openai` | Wystarczy jeden klucz `OPENAI_API_KEY` do czatu, feedbacku **i** Qdrant (RAG). |
| **Produkcja / dane osobowe** | `azure` | Zalecane: region Azure w UE, kontrola rezydencji danych i polityki firmowej. |

Przy `LLM_PROVIDER=openai` embeddingi używają `OPENAI_EMBEDDING_MODEL` (domyślnie
`text-embedding-3-small`). Przy `azure` — `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`.

**Opcjonalne – wysyłka maili i monitoring:**

- `EMAIL_USERNAME`, `EMAIL_PASSWORD` — login do **IMAP (nasłuch)** i **SMTP (wysyłka)**.
- `SMTP_*`, `IMAP_*` — hosty i porty od dostawcy poczty.
- `EMAIL_MONITOR_ENABLED`, `EMAIL_CHECK_INTERVAL` — cykliczne sprawdzanie skrzynki.
- `IOD_EMAIL`, `HR_EMAIL` — **inne** skrzynki na przekazania (muszą różnić się od `EMAIL_USERNAME`).

> Dobra praktyka: najpierw uruchom system tylko z jednym providerem LLM (Azure albo OpenAI),
> a dopiero potem dodaj pocztę. Przed włączeniem monitora przeczytaj
> [osobne skrzynki – unikaj pętli](EMAIL_SETUP_PL.md#zanim-zaczniesz).

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

Jeżeli SMTP jest skonfigurowane, mail trafia do kandydata.
Bez SMTP — treść jest zapisana w bazie i widać ją w panelu administracyjnym
(**http://localhost:5000/admin**, sekcja **„Wysłane emaile z feedbackiem”**,
kolumna **„Treść emaila”**), ale **to nie zastępuje** realnej wysyłki w rekrutacji.

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
  - przy `LLM_PROVIDER=openai`: czy masz `OPENAI_API_KEY` bez cudzysłowów i aktywne rozliczenia OpenAI,
  - przy `LLM_PROVIDER=azure`: czy masz `AZURE_OPENAI_API_KEY` bez cudzysłowów,
  - czy endpoint (`AZURE_OPENAI_ENDPOINT`) jest poprawny dla Azure,
  - czy deploymenty GPT/embedding istnieją w Azure, jeśli używasz Azure.

### 7.2. Błędy SMTP/IMAP i zapętlenie maili

- **Objawy:**
  - „Authentication failed”,
  - brak możliwości wysyłki maili,
  - logi z IMAP z informacją o błędnym loginie/haśle,
  - te same wiadomości przetwarzane w kółko.
- **Sprawdź:**
  - czy używasz **app password**, jeśli dostawca tego wymaga (Gmail, Zoho),
  - czy host/port są poprawne (patrz dokumentacja dostawcy),
  - czy IMAP/SMTP jest włączone na koncie (np. w ustawieniach Gmail/Zoho),
  - czy `EMAIL_USERNAME` i `EMAIL_PASSWORD` są prawidłowe,
  - czy `HR_EMAIL` i `IOD_EMAIL` **nie są** takie same jak `EMAIL_USERNAME`
    ([szczegóły](EMAIL_SETUP_PL.md#zanim-zaczniesz)).

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
