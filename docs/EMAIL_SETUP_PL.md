# Konfiguracja e‑mail – SMTP/IMAP (Zoho, Gmail, inne)

Aplikacja używa standardowego **SMTP (wysyłanie)** i **IMAP (monitoring)**, więc może
pracować z dowolnym dostawcą obsługującym te protokoły (Zoho, Gmail, Office 365 itd.).
Konfiguracja odbywa się przez zmienne środowiskowe w pliku `.env`.

Jeśli nigdy nie konfigurowałeś poczty dla aplikacji, najpierw przeczytaj sekcję
[Zanim zaczniesz](#zanim-zaczniesz), a potem wróć do instrukcji dla wybranego dostawcy.

Zawsze używaj **hasła aplikacji / app password**, jeśli dostawca tego wymaga
(np. Gmail, Zoho), a nie głównego hasła do konta.
Jeśli Twój dostawca nie używa haseł aplikacji, stosuj metodę logowania opisaną
w jego oficjalnej dokumentacji.

## Zanim zaczniesz

### SMTP i IMAP — krótko i po ludzku

| Protokół | Kierunek | Rola w tym projekcie |
|----------|----------|----------------------|
| **SMTP** | Wychodząca | Wysyłka maili: feedback dla kandydatów, potwierdzenia, przekazania do HR/IOD. |
| **IMAP** | Przychodząca | Połączenie ze skrzynką i odczyt **nowych** wiadomości dla monitora. |

SMTP i IMAP to nie programy do instalacji — dostawca poczty podaje **hosty i porty**
(np. `smtp.zoho.eu:587`, `imap.zoho.eu:993`). Wpisujesz je w `.env`.

### Jak aplikacja mapuje zmienne na skrzynki

| Zmienna | Rola |
|---------|------|
| `EMAIL_USERNAME` + `EMAIL_PASSWORD` | Login do **IMAP (nasłuch)** i **SMTP (wysyłka)** — to **monitorowana** skrzynka. |
| `IOD_EMAIL` | Adres docelowy przekazań RODO / IOD (musi być **inny** niż `EMAIL_USERNAME`). |
| `HR_EMAIL` | Adres docelowy przekazań do HR, gdy bot nie odpowie sam (też **inny** adres). |
| `EMAIL_MONITOR_ENABLED` | `true` włącza cykliczne sprawdzanie skrzynki (`EMAIL_CHECK_INTERVAL` w sekundach). |

Monitor ogląda skrzynkę `EMAIL_USERNAME` przez IMAP. Gdy trzeba coś przekazać, aplikacja
**wysyła** nowy mail na `HR_EMAIL` lub `IOD_EMAIL` przez SMTP. Te adresy muszą być
**osobnymi skrzynkami** — nie tą samą, którą nasłuchujemy.

### Ważne: osobne skrzynki (unikaj nieskończonej pętli)

> **Nie ustawiaj** `HR_EMAIL` ani `IOD_EMAIL` na ten sam adres co `EMAIL_USERNAME`.
>
> Gdy skrzynka monitorowana i adres przekazania są takie same, aplikacja przekazuje
> mail „do siebie”, monitor traktuje go jako nowy i przetwarzanie może zapętlać się
> w nieskończoność.

Przy **demo i testach lokalnych**:

- Używaj **dedykowanych adresów testowych**, nie produkcyjnej skrzynki HR ani IOD.
- Potrzebujesz co najmniej **trzech różnych skrzynek**, np.:
  - `rekrutacja-bot@twoja-domena.test` → `EMAIL_USERNAME` (nasłuch + wysyłka z tego konta),
  - `hr-test@twoja-domena.test` → `HR_EMAIL`,
  - `iod-test@twoja-domena.test` → `IOD_EMAIL`.
- Nigdy jednego adresu na „skrzynkę, którą obserwujemy” i „skrzynkę, na którą przekazujemy”.

**Dlaczego w przykładach jest Zoho:** na darmowym planie Zoho Mail można założyć kilka
skrzynek w jednej domenie — wygodne do demo bez mieszania prawdziwej poczty HR z botem.

**Własny dostawca:** jeśli u Ciebie da się utworzyć kilka skrzynek (Google Workspace,
Microsoft 365, panel hostingu itd.), możesz użyć swojego dostawcy — aplikacji wystarczy
działające SMTP + IMAP oraz **rozdzielone** adresy jak wyżej.

### Oficjalne źródła (do czego służy który link)

- **Gmail – włączenie IMAP/SMTP i ustawienia serwera**
  - [Google Workspace Admin Help](https://support.google.com/a/answer/9003945?hl=pl) —
    dozwolone klienty i ustawienia organizacji.
  - [Gmail Developers (IMAP/SMTP)](https://developers.google.com/gmail/imap/imap-smtp) —
    hosty, porty i szczegóły protokołu.
- **Gmail – hasło aplikacji (przy włączonym 2FA)**
  - [Gmail Help – hasła aplikacji](https://support.google.com/mail/answer/185833?hl=pl) —
    wartość do `EMAIL_PASSWORD` (nie zwykłe hasło do Gmaila).

- **Zoho Mail – włączenie IMAP/SMTP**
  - [Zoho Mail – dostęp IMAP](https://www.zoho.com/mail/help/imap-access.html) — włączenie
    IMAP i potwierdzenie hostów `imap.zoho.eu` / `smtp.zoho.eu` (lub `.com`).
- **Zoho Mail – hasło aplikacji**
  - [Zoho Accounts – App passwords](https://accounts.zoho.com/home#security/app_passwords) —
    hasło do `EMAIL_PASSWORD`.

- **Microsoft 365 – wysyłka SMTP**
  - [Microsoft Learn – SMTP AUTH](https://learn.microsoft.com/exchange/clients-and-mobile-in-exchange-online/authenticated-client-smtp-submission) —
    kiedy SMTP jest dozwolone w tenantcie.

> Uwaga dla Microsoft 365: klasyczne IMAP/SMTP z loginem i hasłem bywa ograniczane
> politykami tenantu; Microsoft zaleca OAuth tam, gdzie to możliwe. Do demo wygodniej
> wybrać dostawcę, u którego łatwo założysz kilka skrzynek testowych.

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

Zalecane do **demo**, gdy potrzebujesz kilku tanich skrzynek testowych w jednej domenie.

**Typowy przebieg:**

1. Załóż konto Zoho Mail i dodaj domenę (lub użyj adresu od Zoho).
2. Utwórz **osobne skrzynki** dla bota, `HR_EMAIL` i `IOD_EMAIL`.
3. Włącz IMAP na skrzynce bota ([pomoc Zoho IMAP](https://www.zoho.com/mail/help/imap-access.html)).
4. Wygeneruj [hasło aplikacji](https://accounts.zoho.com/home#security/app_passwords) dla
   `EMAIL_USERNAME` i wpisz je w `EMAIL_PASSWORD`.
5. W `.env` ustaw `HR_EMAIL` / `IOD_EMAIL` na **inne** adresy — nigdy na skrzynkę bota.

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

**Typowy przebieg:**

1. Włącz IMAP ([Admin Help](https://support.google.com/a/answer/9003945?hl=pl) w Workspace
   lub Ustawienia Gmail → „Przekazywanie i POP/IMAP” na koncie osobistym).
2. Włącz **weryfikację dwuetapową** na koncie Google.
3. Utwórz [hasło aplikacji](https://support.google.com/mail/answer/185833?hl=pl) i użyj go
   jako `EMAIL_PASSWORD`.
4. `EMAIL_USERNAME` — **osobny** adres testowy; `HR_EMAIL` / `IOD_EMAIL` — **inne**
   skrzynki Google, które posiadasz do testów.

Dla użytkowników Gmail: wymagane jest:

- włączone 2FA na koncie Google,
- wygenerowanie **hasła aplikacji** w ustawieniach bezpieczeństwa konta.

Dla innych dostawców (Zoho, Microsoft 365, własny serwer SMTP/IMAP)
obowiązują zasady z dokumentacji danego dostawcy.

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

- **Maile powtarzają się w nieskończoność / monitor „nie kończy”**
  - Sprawdź, czy `HR_EMAIL` i `IOD_EMAIL` **nie są** równe `EMAIL_USERNAME`.
  - Użyj osobnych skrzynek testowych; patrz sekcję [Zanim zaczniesz](#zanim-zaczniesz).

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
