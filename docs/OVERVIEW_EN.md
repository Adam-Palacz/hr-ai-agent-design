## Recruitment AI – high‑level overview

Recruitment AI is a web application that helps HR teams manage candidates,
analyze CVs, generate personalised feedback emails, and handle incoming
email inquiries using company knowledge (RAG).

### Who is this for

- **HR team** – people running recruitment processes, sending feedback,
  answering candidate questions.
- **Managers / business owners** – want a clear view of the pipeline
  (candidates, stages, sent emails, IOD / GDPR tickets).
- **Candidates** – receive feedback emails and answers to their questions.

### Main features

- **Candidate management** – add and edit candidates, assign them to positions,
  track recruitment stage.
- **CV upload and parsing** – upload PDF files and automatically extract
  key information (experience, education, skills).
- **AI‑generated feedback on rejection** – create constructive, personalised
  feedback emails based on the CV, HR notes and job description.
- **Email sending** – send feedback via SMTP (Zoho, Gmail, others), including
  consent information and privacy‑policy links.
- **Inbox monitoring (optional)** – read emails via IMAP, classify them with AI
  (IOD/GDPR, consent yes/no, normal conversation), create tickets and/or send
  automatic replies.
- **RAG (answers from company documents)** – use a Qdrant vector database to
  answer candidate questions based on internal documents (policies, GDPR/RODO,
  recruitment rules, info about the company).
- **Admin panel & metrics** – see candidates, sent emails, HR notes, tickets,
  and basic statistics/metrics.

> **RAG in simple words:** instead of only using the “raw” AI model, the system
> can search company documents and feed them into the model as context
> (for example GDPR policies or recruitment procedures).

---

## Flow 1: from CV to feedback email

Scenario: HR rejects a candidate and wants to send a clear, consistent
feedback email.

```mermaid
sequenceDiagram
    participant HR as HR
    participant App as Application
    participant AI as Azure OpenAI
    participant Email as Mail server

    HR->>App: 1. Add candidate and upload CV (PDF)
    HR->>App: 2. Fill in HR note and choose decision \"Rejected\"
    App->>AI: 3. Parse CV (CV parser agent)
    AI-->>App: 4. Structured CV data (CVData)
    App->>AI: 5. Generate feedback (feedback agent)
    AI-->>App: 6. HTML email content
    App->>AI: 7. Validate email (validator agent)
    AI-->>App: 8. Validation result (OK or issues)
    App->>AI: 9. (optional) Correct email (correction agent)
    AI-->>App: 10. Corrected HTML
    App->>Email: 11. Send email to candidate
    Email-->>HR: 12. Delivery / log visible in admin panel
```

In practice, HR sees in the UI:
a list of candidates, their stage, a “Process”/“Reject with feedback”
action and the history of notes and sent emails.

---

## Flow 2: from candidate email to reply or escalation

Scenario: a candidate replies to an email or sends a new question related
to recruitment, personal data, or offer details.

```mermaid
sequenceDiagram
    participant Cand as Candidate
    participant Inbox as Mailbox (IMAP)
    participant Listener as EmailListener
    participant Router as EmailRouter
    participant AI as Azure OpenAI + RAG
    participant HR as HR/IOD

    Cand->>Inbox: 1. Sends an email (question / request)
    Listener->>Inbox: 2. Reads new messages
    Listener->>Router: 3. Passes email content
    Router->>AI: 4. Classify (IOD / consent / normal)
    AI-->>Router: 5. Decision: iod | consent_yes | consent_no | default

    alt IOD / GDPR
        Router->>HR: 6a. Create IOD ticket and forward to IOD/HR
    else Consent yes/no
        Router->>HR: 6b. Update consent flag for candidate
        Router-->>Cand: 7b. (optional) Confirmation email
    else Normal question
        Router->>AI: 6c. Fetch context from Qdrant (RAG)
        AI-->>Router: 7c. Suggested reply or \"forward to HR\"
        alt Confident answer
            Router-->>Cand: 8c. Send AI answer on behalf of HR
        else Low confidence
            Router->>HR: 8d. Forward email for manual answer
        end
    end
```

From the HR perspective:

- the system can automatically handle repetitive, simple questions (FAQ),
- all sensitive topics (GDPR, individual decisions, complaints)
  are still routed to a human (IOD/HR),
- AI decisions can be audited (metrics, admin panel).
