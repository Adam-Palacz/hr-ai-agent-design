# Konfiguracja e‑mail – SMTP/IMAP (Zoho, Gmail, inne)

Aplikacja używa standardowego **SMTP (wysyłanie)** i **IMAP (monitoring)**, więc może
pracować z dowolnym dostawcą obsługującym te protokoły (Zoho, Gmail, Office 365 itd.).
Konfiguracja odbywa się przez zmienne środowiskowe w pliku `.env`.

Zawsze używaj **hasła aplikacji / app password**, jeśli dostawca tego wymaga
(np. Gmail, Zoho), a nie głównego hasła do konta.

## 1. Zmienne środowiskowe

Podstawowe zmienne dla e‑mail:

- `EMAIL_USERNAME` – login SMTP/IMAP (pełny adres e‑mail).
- `EMAIL_PASSWORD` – hasło SMTP/IMAP lub **hasło aplikacji**.
- `SMTP_HOST` – adres hosta serwera SMTP.
- `SMTP_PORT` – port SMTP (typowo `587` dla TLS, `465` dla SSL).
- `SMTP_USE_TLS` – `true` dla STARTTLS (zalecane z portem `587`).
- `IMAP_HOST` – adres hosta serwera IMAP.
- `IMAP_PORT` – port IMAP (typowo `993` dla SSL).

Monitoring skrzynki (opcjonalny, IMAP):

- `EMAIL_MONITOR_ENABLED` – `true`, aby włączyć monitoring.
- `IOD_EMAIL` – adres e‑mail dla tematów IOD / RODO.
- `HR_EMAIL` – skrzynka HR, na którą trafiają zapytania.
- `EMAIL_CHECK_INTERVAL` – odstęp między sprawdzeniami IMAP (np. `60` sekund).

Aplikacja czyta te wartości z `config/settings.py` i używa ich w
`services/email_sender.py`, `services/email_listener.py`, `services/email_router.py`
oraz `services/email_monitor.py`.

---

## 2. Zoho Mail

Użyj regionu EU lub COM zgodnie z Twoim kontem.

**SMTP (wysyłanie)**:

- Host: `smtp.zoho.eu` (lub `smtp.zoho.com` dla regionu `.com`)
- Port: `587`
- TLS: `true` (STARTTLS)

**IMAP (monitoring)**:

- Host: `imap.zoho.eu` (lub `imap.zoho.com`)
- Port: `993`

Przykładowy fragment `.env` (region EU):

```env
EMAIL_USERNAME=twoje-imie@twoja-domena.eu
EMAIL_PASSWORD=twoje-haslo-aplikacji-zoho

SMTP_HOST=smtp.zoho.eu
SMTP_PORT=587
SMTP_USE_TLS=true

IMAP_HOST=imap.zoho.eu
IMAP_PORT=993
```

Zoho zazwyczaj wymaga **hasła aplikacji** do dostępu SMTP/IMAP. W dokumentacji
Zoho znajdziesz instrukcje pod hasłami „app password” lub „SMTP/IMAP access”.

---

## 3. Gmail

Gmail wymaga:

- włączonego 2FA na koncie Google,
- wygenerowania **hasła aplikacji** w ustawieniach bezpieczeństwa konta.

**SMTP (wysyłanie)**:

- Host: `smtp.gmail.com`
- Port: `587`
- TLS: `true` (STARTTLS)

**IMAP (monitoring)**:

- Host: `imap.gmail.com`
- Port: `993`

Przykładowy fragment `.env`:

```env
EMAIL_USERNAME=twoje.konto@gmail.com
EMAIL_PASSWORD=twoje-haslo-aplikacji-gmail

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true

IMAP_HOST=imap.gmail.com
IMAP_PORT=993
```

> Nie używaj głównego hasła do Gmaila. Utwórz **hasło aplikacji** w
> Konto Google → Bezpieczeństwo → „Hasła aplikacji” i tę wartość ustaw jako
> `EMAIL_PASSWORD`.

---

## 4. Office 365 / Microsoft 365 (opcjonalnie)

Konfiguracja dla Office 365 zależy od polityk bezpieczeństwa Twojego tenanta,
ale często spotykane ustawienia to:

**SMTP (wysyłanie)**:

- Host: `smtp.office365.com`
- Port: `587`
- TLS: `true` (STARTTLS)

**IMAP (monitoring)** – jeśli IMAP jest włączony:

- Host: `outlook.office365.com`
- Port: `993`

Przykładowy fragment `.env`:

```env
EMAIL_USERNAME=twoje.imie@twoja-firma.com
EMAIL_PASSWORD=twoje-haslo-aplikacji-lub-haslo-maila

SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USE_TLS=true

IMAP_HOST=outlook.office365.com
IMAP_PORT=993
```

Przy nowoczesnym uwierzytelnianiu może być wymagane OAuth; szczegóły znajdziesz
w dokumentacji Microsoft („SMTP AUTH in Exchange Online”, „IMAP access”).
Ten projekt zakłada prosty dostęp SMTP/IMAP na bazie loginu i hasła.

---

## 5. Rozwiązywanie problemów

- **Authentication failed / błąd logowania**
  - Sprawdź `EMAIL_USERNAME` / `EMAIL_PASSWORD`.
  - Dla Gmail/Zoho upewnij się, że używasz **hasła aplikacji**, a nie głównego.
  - Sprawdź, czy dostęp SMTP/IMAP jest włączony w ustawieniach konta.

- **Connection refused / timeout**
  - Zweryfikuj `SMTP_HOST`, `SMTP_PORT`, `IMAP_HOST`, `IMAP_PORT`.
  - Sprawdź firewall lub ograniczenia sieci (VPN, proxy).

- **TLS/SSL errors / błędy TLS/SSL**
  - Sprawdź, czy `SMTP_USE_TLS` pasuje do portu (`true` z `587`).
  - Dla portu `465` może być wymagane czyste SSL (sprawdź dokumentację dostawcy).
