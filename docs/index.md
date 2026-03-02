## Recruitment AI – Documentation

Welcome to the documentation for the **Recruitment AI** assistant used to manage candidates, generate feedback emails, and handle incoming questions.

- **High-level overview (non-technical):**
  - Polish: [Przegląd systemu](OVERVIEW_PL.md)
  - English: [System overview](OVERVIEW_EN.md)
- **Quickstart guides (from zero to running app):**
  - Polish: [Szybki start](QUICKSTART_PL.md)
  - English: [Quickstart](QUICKSTART_EN.md)
- **Running with Docker:**
  - Polish: [Uruchomienie w Dockerze](DOCKER_PL.md)
  - English: [Docker guide](DOCKER_EN.md)
- **API reference generated from code:**
  - [Agents & services](api.md)

To build these docs locally:

```bash
pip install -r requirements-docs.txt
mkdocs serve
```

Then open `http://127.0.0.1:8000/` in your browser.
