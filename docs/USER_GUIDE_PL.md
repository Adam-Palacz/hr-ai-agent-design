# Obsługa aplikacji – przewodnik użytkownika

Ten przewodnik pokazuje, co zrobić **po uruchomieniu aplikacji** pod adresem
`http://localhost:5000`.

Jeśli aplikacja nie jest jeszcze uruchomiona, zacznij od:
[Pierwsze uruchomienie – przewodnik nietechniczny](QUICKSTART_NONTECH_PL.md).

---

## 1. Główne ekrany

| Ekran | Adres | Do czego służy |
|-------|-------|----------------|
| Lista kandydatów | `http://localhost:5000` | Dodawanie i przegląd kandydatów. |
| Panel admina | `http://localhost:5000/admin` | Podgląd kandydatów, notatek, wygenerowanych feedbacków, ticketów i odpowiedzi modeli. |
| Zdrowie aplikacji | `http://localhost:5000/health` | Prosty test, czy aplikacja działa. |

---

## 2. Dodaj stanowisko

Przed dodaniem kandydata warto dodać stanowisko, na które aplikuje.

1. Wejdź do sekcji **Positions / Stanowiska**.
2. Dodaj nazwę stanowiska, firmę i opis.
3. Zapisz stanowisko.

Opis stanowiska pomaga AI przygotować bardziej trafny feedback.

---

## 3. Dodaj kandydata

1. Na stronie głównej kliknij dodanie kandydata.
2. Wpisz imię, nazwisko i adres e-mail.
3. Wybierz stanowisko.
4. Wgraj CV w formacie PDF.
5. Ustaw zgodę dotyczącą rozważenia kandydata do innych stanowisk.
6. Zapisz kandydata.

Po zapisie kandydat pojawi się na liście.

---

## 4. Przejrzyj CV i dodaj notatkę HR

1. Kliknij kandydata na liście.
2. Sprawdź podgląd CV.
3. Wpisz notatkę HR, np. mocne strony, braki, powód odrzucenia albo decyzję z rozmowy.

Notatka HR jest ważna: AI używa jej do przygotowania feedbacku. Im bardziej konkretna
notatka, tym lepsza odpowiedź.

---

## 5. Wygeneruj feedback

Na ekranie kandydata wybierz decyzję:

- **Zaakceptuj** – kandydat przechodzi dalej w procesie.
- **Odrzuć** – aplikacja generuje feedback dla kandydata.

Po kliknięciu odrzucenia aplikacja wykonuje pracę w tle:

1. czyta CV,
2. generuje feedback,
3. waliduje treść,
4. zapisuje przygotowany mail w bazie,
5. wysyła go tylko wtedy, gdy SMTP jest skonfigurowane.

Generowanie może potrwać kilkanaście lub kilkadziesiąt sekund.

---

## 6. Gdzie znaleźć feedback bez skonfigurowanej poczty

Jeśli nie ustawiono SMTP, kandydat **nie dostanie maila**, ale feedback nadal jest
zapisany w aplikacji.

1. Otwórz: `http://localhost:5000/admin`.
2. Przejdź do sekcji **„Wysłane emaile z feedbackiem”**.
3. Znajdź właściwego kandydata.
4. W kolumnie **„Treść emaila”** zobaczysz przygotowany feedback.

Nazwa sekcji mówi „wysłane”, ale w trybie bez SMTP oznacza to: **wygenerowane i zapisane
w aplikacji**. Do realnej wysyłki trzeba skonfigurować pocztę według
[Konfiguracja e-mail](EMAIL_SETUP_PL.md).

---

## 7. Panel admina

Panel admina (`/admin`) pokazuje:

- kandydatów,
- stanowiska,
- notatki HR,
- wygenerowane feedbacki,
- tickety,
- odpowiedzi modeli AI.

To najlepsze miejsce do sprawdzenia, czy aplikacja coś wygenerowała, nawet jeśli mail
nie został wysłany.

---

## 8. Poczta: kiedy ją konfigurować

Do demo AI poczta nie jest wymagana.

Poczta jest potrzebna, jeśli chcesz:

- wysyłać feedback do kandydatów,
- monitorować odpowiedzi kandydatów przez IMAP,
- przekazywać sprawy do HR lub IOD.

Wtedy skonfiguruj:

- `EMAIL_USERNAME`,
- `EMAIL_PASSWORD` lub hasło aplikacji,
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS`,
- `IMAP_HOST`, `IMAP_PORT`,
- `HR_EMAIL`,
- `IOD_EMAIL`,
- `EMAIL_MONITOR_ENABLED=true`.

Szczegóły: [Konfiguracja e-mail](EMAIL_SETUP_PL.md).

---

## 9. Najczęstsze problemy użytkowe

### Nie widzę feedbacku w panelu admina

- Poczekaj kilkadziesiąt sekund i odśwież `/admin`.
- Sprawdź, czy w `.env` jest poprawny `OPENAI_API_KEY` albo konfiguracja Azure.
- Sprawdź, czy kandydat miał CV PDF i notatkę HR.

### Kandydat nie dostał maila

- To normalne, jeśli SMTP nie jest skonfigurowane.
- Feedback sprawdź w `/admin`.
- Do wysyłki skonfiguruj SMTP.

### Feedback jest zbyt ogólny

- Dopisz konkretniejszą notatkę HR.
- Upewnij się, że stanowisko ma opis wymagań.

### Aplikacja działa, ale AI zwraca błąd

- Sprawdź klucz API.
- Sprawdź aktywne rozliczenia OpenAI albo konfigurację Azure.
- Upewnij się, że `LLM_PROVIDER` pasuje do używanego klucza.
