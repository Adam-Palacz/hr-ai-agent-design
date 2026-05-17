# Pierwsze uruchomienie — przewodnik dla osób nietechnicznych (PL)

Ten dokument jest dla Ciebie, jeśli **nie programujesz na co dzień**, ale chcesz
**samodzielnie** zobaczyć aplikację Recruitment AI na swoim komputerze i przetestować
generowanie opinii o kandydacie (AI).

**Szacowany czas:** ok. 30–60 minut (pierwszy raz).  
**System:** instrukcje krok po kroku pod **Windows 10/11**; na końcu krótka wzmianka o Macu.

---

## Co zrobisz (i czego nie)

| W tym przewodniku | Później (osobne dokumenty) |
|-------------------|----------------------------|
| Zainstalujesz Pythona | Konfiguracja poczty (SMTP/IMAP) |
| Pobierzesz projekt | Uruchomienie w Dockerze |
| Utworzysz klucz API OpenAI | Opcjonalnie: baza wiedzy (RAG) — ten sam klucz co do czatu |
| Uruchomisz aplikację w przeglądarce | Pełny [Szybki start techniczny](QUICKSTART_PL.md) |

**W tym przewodniku celowo pomijasz:** pocztę aplikacji (SMTP), Zoho, hasła aplikacji,
Dockera i Azure — to **demo AI**, nie pełna rekrutacja.

> **Ważne:** w normalnej pracy system **wysyła feedback e-mailem do kandydata**.
> Bez SMTP zobaczysz wygenerowany tekst w aplikacji (panel administracyjny), ale
> **kandydat nic nie dostanie**. Pełna poczta: [Konfiguracja e‑mail](EMAIL_SETUP_PL.md).

---

## Checklist — odhaczaj po kolei

- [ ] Python 3.11+ zainstalowany (zaznaczone „Add Python to PATH”)
- [ ] Folder projektu na dysku (ZIP lub `git clone`)
- [ ] Konto na platform.openai.com + metoda płatności
- [ ] Skopiowany klucz API OpenAI (zaczyna się od `sk-`)
- [ ] Plik `.env` w folderze projektu z kluczem i `EMAIL_MONITOR_ENABLED=false`
- [ ] Aplikacja działa pod adresem http://localhost:5000
- [ ] Dodany kandydat z PDF i wygenerowany feedback (test AI)

---

## Słowniczek (2 minuty)

| Słowo | Co to znaczy „po ludzku” |
|-------|---------------------------|
| **Terminal / PowerShell** | Czarne okno, w którym wpisujesz polecenia tekstowe zamiast klikać w programie. |
| **Folder projektu** | Katalog `hr-ai-agent-design` z plikami aplikacji. |
| **Plik `.env`** | Zwykły plik tekstowy z hasłami i ustawieniami (klucz API). **Nie** udostępniaj go nikomu. |
| **Klucz API** | „Hasło” do usługi OpenAI — aplikacja używa go do generowania tekstu. |
| **localhost:5000** | Adres aplikacji **na Twoim komputerze** (nie w internecie dla innych osób). |

---

## Krok 1 — Zainstaluj Pythona (Windows)

1. Wejdź na [python.org/downloads](https://www.python.org/downloads/).
2. Pobierz **Python 3.11** lub nowszy (przycisk „Download”).
3. Uruchom instalator.
4. **Ważne:** na pierwszym ekranie zaznacz **„Add python.exe to PATH”** (na dole).
5. Kliknij **Install Now** i dokończ instalację.
6. Sprawdzenie:
   - Naciśnij klawisz Windows, wpisz `PowerShell`, otwórz **Windows PowerShell**.
   - Wpisz i zatwierdź Enterem:

     ```powershell
     python --version
     ```

   - Powinno pojawić się coś w stylu `Python 3.11.x` lub `3.12.x`.

Jeśli zamiast wersji widzisz błąd „nie rozpoznano” — zainstaluj Pythona ponownie z zaznaczonym PATH.

---

## Krok 2 — Pobierz projekt na dysk

### Opcja A — bez Gita (najprostsza)

1. Otwórz w przeglądarce:  
   **https://github.com/Adam-Palacz/hr-ai-agent-design**
2. Kliknij zielony przycisk **Code** → **Download ZIP**.
3. Rozpakuj ZIP (Prawy przycisk → **Wyodrębnij wszystko**).
4. Zapamiętaj folder, np. `C:\Users\TwojeImie\hr-ai-agent-design`.

### Opcja B — z Gitem (jeśli masz Git)

W PowerShellu:

```powershell
cd $HOME\Documents
git clone https://github.com/Adam-Palacz/hr-ai-agent-design.git
cd hr-ai-agent-design
```

Dalsze kroki wykonuj **w folderze projektu** (tam jest plik `app.py`).

**Jak otworzyć PowerShell w tym folderze (Windows 11):**  
Wejdź w folder w Eksploratorze plików → kliknij pasek adresu → wpisz `powershell` → Enter.

---

## Krok 3 — Konto OpenAI i klucz API

1. Wejdź na [platform.openai.com](https://platform.openai.com/) i **zaloguj się** lub **załóż konto**.
2. Platforma może poprosić o **dodanie metody płatności** (karta) — usługa jest płatna za użycie
   (kilka zapytań testowych to zwykle niewielka kwota; ustaw limity w ustawieniach rozliczeń).
3. Otwórz stronę kluczy: [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
4. Kliknij **Create new secret key** (Utwórz nowy klucz tajny).
5. Nadaj nazwę, np. `recruitment-ai-test`, i potwierdź.
6. **Skopiuj klucz od razu** (zaczyna się od `sk-`) i wklej do Notatnika — **później nie zobaczysz go ponownie w całości**.

> **Bezpieczeństwo:** traktuj klucz jak hasło. Nie wysyłaj go mailem, nie wklejaj na czacie publicznym.

---

## Krok 4 — Utwórz plik `.env`

Plik `.env` mówi aplikacji, skąd brać klucz AI. **W tym przewodniku wyłączamy też pocztę.**

### 4.1. Skopiuj szablon

W PowerShellu (w folderze projektu):

```powershell
Copy-Item .env.example .env
```

### 4.2. Otwórz `.env` w Notatniku

```powershell
notepad .env
```

### 4.3. Zostaw / ustaw tylko te linie (resztę możesz zostawić — nie szkodzi na start)

Znajdź i **popraw** (bez cudzysłowów wokół wartości):

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=wklej-tutaj-swoj-klucz-sk-...
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
EMAIL_MONITOR_ENABLED=false
```

- W `OPENAI_API_KEY` wklej **swój** klucz z kroku 3 (jedna linia, bez spacji na końcu).
- `gpt-4o-mini` to popularny, tani model — możesz go zostawić.
- `EMAIL_MONITOR_ENABLED=false` — aplikacja **nie** będzie nasłuchiwać skrzynki pocztowej.

Zapisz plik: **Plik → Zapisz** i zamknij Notatnik.

> **Uwaga:** jeśli Notatnik zapisze plik jako `.env.txt`, usuń `.txt` z nazwy w Eksploratorze
> (Widok → Pokaż rozszerzenia nazw plików musi być włączone).

### Czego **nie** musisz teraz wypełniać

- `EMAIL_USERNAME`, `EMAIL_PASSWORD`, `SMTP_*`, `IMAP_*` — poczta: [Konfiguracja e‑mail](EMAIL_SETUP_PL.md).
- `AZURE_OPENAI_*` — tylko przy wdrożeniu produkcyjnym ([Szybki start](QUICKSTART_PL.md)); do testów wystarczy OpenAI.

### Opcjonalnie: baza wiedzy (RAG) z tym samym kluczem OpenAI

Jeśli masz już `LLM_PROVIDER=openai` i `OPENAI_API_KEY`:

1. Umieść pliki `.txt` w folderze `knowledge_base/`.
2. Zatrzymaj aplikację (`Ctrl+C` w PowerShell).
3. Uruchom: `python knowledge_base/load_to_qdrant.py`
4. Uruchom aplikację ponownie.

> **Produkcja:** dla danych osobowych zalecamy `LLM_PROVIDER=azure` i region Azure w UE —
> patrz tabela w [Szybki start](QUICKSTART_PL.md).

---

## Krok 5 — Uruchom aplikację (Windows)

### Sposób łatwiejszy — skrypt `quickstart.ps1`

W PowerShellu w folderze projektu:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\quickstart.ps1
```

- **Pierwsze uruchomienie:** skrypt może zainstalować biblioteki i zakończyć się komunikatem
  o edycji `.env` — wtedy wróć do **kroku 4**, zapisz `.env` i uruchom skrypt **drugi raz**.
- **Drugie uruchomienie:** powinien wystartować serwer; zostaw okno PowerShell **otwarte**.

Gdy zobaczysz komunikat o `http://localhost:5000` — przejdź do kroku 6.

### Sposób ręczny (gdy skrypt nie działa)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

---

## Krok 6 — Otwórz aplikację w przeglądarce

1. Otwórz Chrome lub Edge.
2. W pasku adresu wpisz dokładnie: **http://localhost:5000** i Enter.
3. Powinieneś zobaczyć interfejs Recruitment AI.

**Zatrzymanie aplikacji:** wróć do okna PowerShell i naciśnij `Ctrl+C`.

---

## Krok 7 — Pierwszy test AI (5 minut)

1. W menu dodaj **stanowisko** (np. „Specjalista ds. sprzedaży”).
2. **Dodaj kandydata**: imię, nazwisko, e-mail, przypisz stanowisko, **załaduj PDF** z CV.
3. Wejdź w szczegóły kandydata → dodaj krótką **notatkę HR** (co było OK, co nie).
4. Wybierz decyzję **Odrzucony** / odrzucenie z feedbackiem (zgodnie z etykietą w UI).
5. Poczekaj chwilę — system wygeneruje tekst feedbacku (używa OpenAI).

Bez SMTP **mail nie trafi do kandydata** — to tylko test generatora AI.
Po wygenerowaniu wejdź w **panel administracyjny** aplikacji:

1. Otwórz w przeglądarce: **http://localhost:5000/admin**.
2. Znajdź sekcję **„Wysłane emaile z feedbackiem”**.
3. W kolumnie **„Treść emaila”** zobaczysz przygotowany feedback.

Nazwa sekcji mówi „wysłane”, ale przy braku SMTP jest to mail **przygotowany i zapisany
w aplikacji**, nie dostarczony do kandydata. Do realnej rekrutacji skonfiguruj pocztę
według [Konfiguracja e‑mail](EMAIL_SETUP_PL.md).

---

## Najczęstsze problemy

### „python nie jest rozpoznawany”

Python nie jest w PATH — przeinstaluj z zaznaczonym **Add python.exe to PATH** (krok 1).

### PowerShell nie chce uruchomić `quickstart.ps1`

Uruchom raz:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Błąd przy generowaniu feedbacku (401, 403, „API key”)

- Sprawdź `OPENAI_API_KEY` w `.env` (pełny klucz `sk-...`, bez cudzysłowów).
- Sprawdź `LLM_PROVIDER=openai`.
- Na koncie OpenAI: czy jest **aktywna płatność** i **limit** nie wyczerpany.

### Strona localhost nie otwiera się

- Czy PowerShell nadal działa i nie ma czerwonego błędu?
- Czy wpisujesz `http://localhost:5000` (nie `https`)?
- Spróbuj zamknąć aplikację (`Ctrl+C`) i uruchomić ponownie `python app.py` lub `.\quickstart.ps1`.

### Chcę włączyć wysyłkę i odbiór maili

To osobny, trudniejszy temat (3 skrzynki, hasła aplikacji, brak pętli).  
Zacznij od: [Konfiguracja e‑mail (SMTP/IMAP)](EMAIL_SETUP_PL.md).

---

## Mac (skrót)

1. Zainstaluj Pythona z [python.org](https://www.python.org/downloads/) lub `brew install python@3.11`.
2. Pobierz projekt (ZIP lub `git clone`).
3. W **Terminalu** w folderze projektu:

   ```bash
   cp .env.example .env
   nano .env   # lub otwórz w edytorze tekstu — te same wartości co w kroku 4
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python app.py
   ```

4. Przeglądarka: http://localhost:5000

Możesz też użyć `./quickstart.sh` jeśli jest w repozytorium.

---

## Co dalej?

| Temat | Dokument |
|-------|----------|
| Pełna konfiguracja (Azure, Docker, RAG) | [Szybki start (PL)](QUICKSTART_PL.md) |
| Opis systemu bez żargonu | [Przegląd systemu](OVERVIEW_PL.md) |
| Poczta (Zoho, Gmail, pętle) | [Konfiguracja e‑mail](EMAIL_SETUP_PL.md) |
| Docker | [Uruchomienie w Dockerze](DOCKER_PL.md) |

---

**Potrzebujesz pomocy?** Przy pierwszym uruchomieniu warto poprosić osobę z IT o **15 minut**
— głównie przy Pythonie, PowerShellu i pliku `.env`. Potem kolejne uruchomienia to zwykle
powtórzenie kroku 5 i 6.
