# Email setup – SMTP/IMAP (Zoho, Gmail, others)

This app uses **standard SMTP (sending)** and **IMAP (monitoring)** and can work with
any provider that supports them (Zoho, Gmail, Office 365, etc.). Configuration is done
via environment variables in `.env`.

Always use an **app password / application-specific password** when your provider
requires it (e.g. Gmail, Zoho), not your main account password.

## 1. Environment variables

Core email variables:

- `EMAIL_USERNAME` – SMTP/IMAP login (full email address).
- `EMAIL_PASSWORD` – SMTP/IMAP password or **app password**.
- `SMTP_HOST` – SMTP server hostname.
- `SMTP_PORT` – SMTP port (typically `587` for TLS, `465` for SSL).
- `SMTP_USE_TLS` – `true` for STARTTLS (recommended with port `587`).
- `IMAP_HOST` – IMAP server hostname.
- `IMAP_PORT` – IMAP port (typically `993` for SSL).

Email monitoring (optional, IMAP inbox watcher):

- `EMAIL_MONITOR_ENABLED` – `true` to enable monitoring.
- `IOD_EMAIL` – email address for IOD / GDPR-related messages.
- `HR_EMAIL` – HR inbox for forwarded queries.
- `EMAIL_CHECK_INTERVAL` – seconds between IMAP checks (e.g. `60`).

The app reads these values via `config/settings.py` and uses them in
`services/email_sender.py`, `services/email_listener.py`, `services/email_router.py`
and `services/email_monitor.py`.

---

## 2. Zoho Mail

Use the EU or COM region matching your account.

**SMTP (sending)**:

- Host: `smtp.zoho.eu` (or `smtp.zoho.com` for `.com` region)
- Port: `587`
- TLS: `true` (STARTTLS)

**IMAP (monitoring)**:

- Host: `imap.zoho.eu` (or `imap.zoho.com`)
- Port: `993`

Example `.env` snippet (EU region):

```env
EMAIL_USERNAME=your-name@your-domain.eu
EMAIL_PASSWORD=your-zoho-app-password

SMTP_HOST=smtp.zoho.eu
SMTP_PORT=587
SMTP_USE_TLS=true

IMAP_HOST=imap.zoho.eu
IMAP_PORT=993
```

Zoho usually requires an **app password** for SMTP/IMAP access. See Zoho’s
documentation for “app passwords” or “SMTP/IMAP access” to generate one.

---

## 3. Gmail

Gmail requires:

- 2FA enabled on your Google Account.
- **App password** created in Google Account security.

**SMTP (sending)**:

- Host: `smtp.gmail.com`
- Port: `587`
- TLS: `true` (STARTTLS)

**IMAP (monitoring)**:

- Host: `imap.gmail.com`
- Port: `993`

Example `.env` snippet:

```env
EMAIL_USERNAME=your.account@gmail.com
EMAIL_PASSWORD=your-gmail-app-password

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true

IMAP_HOST=imap.gmail.com
IMAP_PORT=993
```

> Do **not** use your main Gmail password. Create an **App password** in
> Google Account → Security → “App passwords” and use that value as
> `EMAIL_PASSWORD`.

---

## 4. Office 365 / Microsoft 365 (optional)

Configuration for Office 365 depends on your tenant security policies, but a
common setup is:

**SMTP (sending)**:

- Host: `smtp.office365.com`
- Port: `587`
- TLS: `true` (STARTTLS)

**IMAP (monitoring)** – if IMAP is enabled:

- Host: `outlook.office365.com`
- Port: `993`

Example `.env` snippet:

```env
EMAIL_USERNAME=your.name@your-company.com
EMAIL_PASSWORD=your-app-password-or-mail-password

SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USE_TLS=true

IMAP_HOST=outlook.office365.com
IMAP_PORT=993
```

For modern authentication, OAuth flows may be required; consult Microsoft
documentation for “SMTP AUTH in Exchange Online” and “IMAP access” for your
tenant. This project assumes simple username/password SMTP/IMAP.

---

## 5. Troubleshooting

- **Authentication failed**
  - Check `EMAIL_USERNAME` / `EMAIL_PASSWORD`.
  - For Gmail/Zoho, ensure you are using an **app password**, not your main one.
  - Verify that SMTP/IMAP access is enabled in your account settings.

- **Connection refused / timeout**
  - Verify `SMTP_HOST`, `SMTP_PORT`, `IMAP_HOST`, `IMAP_PORT`.
  - Check firewall or corporate network rules.

- **TLS/SSL errors**
  - Confirm that `SMTP_USE_TLS` matches the port (`true` with `587`).
  - For port `465`, you may need SSL (see provider docs).
