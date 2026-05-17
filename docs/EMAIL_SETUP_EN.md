# Email setup – SMTP/IMAP (Zoho, Gmail, others)

This app uses **standard SMTP (sending)** and **IMAP (monitoring)** and can work with
any provider that supports them (Zoho, Gmail, Office 365, etc.). Configuration is done
via environment variables in `.env`.

If you have never configured mail for an application before, read
[Before you configure](#before-you-configure) first, then return to the provider
sections below.

Always use an **app password / application-specific password** when your provider
requires it (e.g. Gmail, Zoho), not your main account password.
If your provider does not use app passwords, follow that provider’s official
authentication guidance.

## Before you configure

### SMTP and IMAP in plain language

| Protocol | Direction | What it does in this project |
|----------|-----------|------------------------------|
| **SMTP** | Outgoing | Sends emails: candidate feedback, acknowledgements, forwards to HR/IOD. |
| **IMAP** | Incoming | Connects to a mailbox and reads **new** messages so the monitor can process them. |

You do not “install” SMTP or IMAP — your mail provider exposes them as server hostnames
and ports (e.g. `smtp.zoho.eu:587`, `imap.zoho.eu:993`). The app stores these in `.env`.

### How this app maps variables to mailboxes

| Variable | Role |
|----------|------|
| `EMAIL_USERNAME` + `EMAIL_PASSWORD` | Login for **both** IMAP (listen) and SMTP (send). This is the **monitored** inbox. |
| `IOD_EMAIL` | Destination for GDPR / information-request forwards (must be a **different** address). |
| `HR_EMAIL` | Destination for HR forwards when the bot cannot answer (must be a **different** address). |
| `EMAIL_MONITOR_ENABLED` | `true` turns on background IMAP polling (`EMAIL_CHECK_INTERVAL` in seconds). |

The monitor watches `EMAIL_USERNAME` via IMAP. When it decides to forward a message, it
**sends** a new email to `HR_EMAIL` or `IOD_EMAIL` via SMTP. Those messages must land in
**other** mailboxes — not in the same inbox that is being watched.

### Critical: separate mailboxes (avoid infinite loops)

> **Do not** set `HR_EMAIL` or `IOD_EMAIL` to the same address as `EMAIL_USERNAME`.
>
> If the monitored inbox and a forward target are the same, the app will forward mail
> to itself, the monitor will see it as a new message, and processing can repeat
> indefinitely.

For **demos and local testing**:

- Use **dedicated test addresses**, not your real company HR or IOD inboxes.
- Use at least **three different mailboxes**, for example:
  - `recruitment-bot@your-domain.test` → `EMAIL_USERNAME` (listen + send as this account),
  - `hr-test@your-domain.test` → `HR_EMAIL`,
  - `iod-test@your-domain.test` → `IOD_EMAIL`.
- Never use one address for both “inbox we watch” and “inbox we forward to”.

**Why Zoho appears in examples:** on a free Zoho Mail plan you can create several
mailboxes on one domain, which makes a safe demo layout easy without mixing production
HR traffic with the bot.

**Your own provider:** if you can create multiple mailboxes (Google Workspace,
Microsoft 365, your hosting panel, etc.), you may use that provider instead — the app
only needs working SMTP + IMAP and **distinct** addresses as above.

### Official sources (what each link is for)

- **Gmail – enable IMAP/SMTP and find server settings**
  - [Google Workspace Admin Help](https://support.google.com/a/answer/9003945) — allowed
    clients, routing, and org-wide mail settings.
  - [Gmail Developers (IMAP/SMTP)](https://developers.google.com/gmail/imap/imap-smtp) —
    hostnames, ports, and protocol details for developers.
- **Gmail – app password (required with 2FA)**
  - [Gmail Help – App passwords](https://support.google.com/mail/answer/185833) — create
    the value you put in `EMAIL_PASSWORD` (not your normal Gmail password).

- **Zoho Mail – enable IMAP/SMTP**
  - [Zoho Mail – IMAP access](https://www.zoho.com/mail/help/imap-access.html) — turn on
    IMAP in the mailbox and confirm `imap.zoho.eu` / `smtp.zoho.eu` (or `.com`).
- **Zoho Mail – app password**
  - [Zoho Accounts – App passwords](https://accounts.zoho.com/home#security/app_passwords) —
    generate a password for `EMAIL_PASSWORD`.

- **Microsoft 365 – SMTP submission**
  - [Microsoft Learn – SMTP AUTH](https://learn.microsoft.com/exchange/clients-and-mobile-in-exchange-online/authenticated-client-smtp-submission) —
    when SMTP is allowed and how tenants enable it.

> Note for Microsoft 365: classic IMAP/SMTP username+password may be restricted by
> tenant policies; OAuth is recommended where possible. For demos, prefer a provider
> where you control several test mailboxes without tenant blocks.

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

Recommended for **demos** when you need several cheap test mailboxes on one domain.

**Typical flow:**

1. Create a Zoho Mail account and add your domain (or use a Zoho-provided address).
2. Create **separate users/aliases** for the bot inbox, `HR_EMAIL`, and `IOD_EMAIL`.
3. Enable IMAP for the bot mailbox ([Zoho IMAP help](https://www.zoho.com/mail/help/imap-access.html)).
4. Generate an [app password](https://accounts.zoho.com/home#security/app_passwords) for
   `EMAIL_USERNAME` and put it in `EMAIL_PASSWORD`.
5. In `.env`, set `HR_EMAIL` / `IOD_EMAIL` to the **other** addresses — never the bot inbox.

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

**Typical flow:**

1. Enable IMAP in Gmail settings ([Admin Help](https://support.google.com/a/answer/9003945)
   for Workspace, or Gmail settings → “Forwarding and POP/IMAP” for personal Gmail).
2. Turn on **2-Step Verification** on the Google account.
3. Create an [App password](https://support.google.com/mail/answer/185833) and use it as
   `EMAIL_PASSWORD`.
4. Use a **dedicated** `@gmail.com` (or Workspace) address for `EMAIL_USERNAME`; set
   `HR_EMAIL` / `IOD_EMAIL` to **other** Google mailboxes you own for testing.

For Gmail users, required:

- 2FA enabled on your Google Account.
- **App password** created in Google Account security.

For non-Gmail providers (Zoho, Microsoft 365, custom SMTP/IMAP),
follow the authentication policy in the provider documentation.

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

- **Emails repeat forever / monitor never “finishes”**
  - Check that `HR_EMAIL` and `IOD_EMAIL` are **not** equal to `EMAIL_USERNAME`.
  - Use separate test mailboxes; see [Critical: separate mailboxes](#critical-separate-mailboxes-avoid-infinite-loops).

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
