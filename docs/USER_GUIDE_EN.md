# Using the Application – User Guide

This guide explains what to do **after the app is running** at
`http://localhost:5000`.

If the app is not running yet, start with:
[First run – non-technical guide](QUICKSTART_NONTECH_EN.md).

---

## 1. Main screens

| Screen | URL | Purpose |
|--------|-----|---------|
| Candidate list | `http://localhost:5000` | Add and review candidates. |
| Admin panel | `http://localhost:5000/admin` | View candidates, notes, generated feedback, tickets, and model responses. |
| Health check | `http://localhost:5000/health` | Quick check that the app is running. |

---

## 2. Add a position

Before adding a candidate, create the position they applied for.

1. Open **Positions**.
2. Add the title, company, and description.
3. Save the position.

The position description helps the AI generate more relevant feedback.

---

## 3. Add a candidate

1. On the home page, add a candidate.
2. Enter first name, last name, and email address.
3. Select a position.
4. Upload a PDF CV.
5. Set the consent option for considering the candidate for other roles.
6. Save the candidate.

The candidate will appear on the main list.

---

## 4. Review the CV and add an HR note

1. Click the candidate in the list.
2. Check the CV preview.
3. Add an HR note, for example strengths, gaps, rejection reason, or interview decision.

The HR note matters: the AI uses it to prepare the feedback. More specific notes usually
produce better feedback.

---

## 5. Generate feedback

On the candidate screen, choose a decision:

- **Accepted** – the candidate moves forward in the process.
- **Rejected** – the app generates candidate feedback.

After rejection, the app works in the background:

1. reads the CV,
2. generates feedback,
3. validates the content,
4. saves the prepared email in the database,
5. sends it only if SMTP is configured.

Generation can take several seconds or longer.

---

## 6. Where to find feedback without email setup

If SMTP is not configured, the candidate **will not receive an email**, but the feedback
is still saved in the app.

1. Open `http://localhost:5000/admin`.
2. Go to **“Sent feedback emails”**.
3. Find the candidate.
4. In the **email content** column, you will see the prepared feedback.

The section name says “sent”, but without SMTP it means: **generated and saved in the
app**. To deliver real emails, configure mail using [Email setup](EMAIL_SETUP_EN.md).

---

## 7. Admin panel

The admin panel (`/admin`) shows:

- candidates,
- positions,
- HR notes,
- generated feedback,
- tickets,
- AI model responses.

This is the best place to check whether the app generated something, even if no email
was sent.

---

## 8. When to configure email

Email is not required for an AI demo.

Email is required if you want to:

- send feedback to candidates,
- monitor candidate replies via IMAP,
- forward issues to HR or IOD/DPO.

Then configure:

- `EMAIL_USERNAME`,
- `EMAIL_PASSWORD` or app password,
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS`,
- `IMAP_HOST`, `IMAP_PORT`,
- `HR_EMAIL`,
- `IOD_EMAIL`,
- `EMAIL_MONITOR_ENABLED=true`.

Details: [Email setup](EMAIL_SETUP_EN.md).

---

## 9. Common user issues

### I do not see feedback in the admin panel

- Wait a few seconds and refresh `/admin`.
- Check that `.env` has a valid `OPENAI_API_KEY` or Azure configuration.
- Check that the candidate had a PDF CV and an HR note.

### The candidate did not receive an email

- This is expected if SMTP is not configured.
- Check feedback in `/admin`.
- Configure SMTP to send real emails.

### Feedback is too generic

- Add a more specific HR note.
- Make sure the position has a requirements description.

### The app works, but AI returns an error

- Check the API key.
- Check active OpenAI billing or Azure configuration.
- Make sure `LLM_PROVIDER` matches the key you are using.
