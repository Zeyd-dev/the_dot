# The Dot — Resource Matcher

An intelligent matchmaking tool that connects startups to The Dot's programs, mentors, and services based on a structured diagnostic. Built with Streamlit, a hybrid rule-based + semantic scoring engine, and an optional ChromaDB vector store.

---

## How it works

A startup fills out a diagnostic form (stage, sector, needs, maturity scores). The engine runs two scoring passes in parallel:

1. **Rule-based score (60%)** — deterministic matching against hard criteria: sector, stage, needs keywords, hard filters (diaspora-only, outside-hub).
2. **Semantic score (40%)** — cosine similarity between the startup's profile and each program description, using the `paraphrase-multilingual-MiniLM-L12-v2` sentence embedding model (French/English/Arabic). Scores are min-max normalized across the candidate set so the 40% always contributes its full range.

The top-N candidates are forwarded to a Groq LLM (with Ollama local fallback) which provides a human-readable justification, priority level, and reasons. The final card displayed to the startup shows the **hybrid score** (deterministic), not the LLM score.

For larger program catalogs (50+ programs), an optional ChromaDB RAG mode replaces the in-memory cosine search with approximate nearest-neighbor retrieval.

---

## Quick start (local development)

### 1. Clone and enter the repo

```bash
git clone <your-repo-url>
cd the-dot-matcher
```

### 2. Create your environment file

```bash
cp .env.example .env
# Then edit .env and fill in your GROQ_API_KEY and DB credentials
```

> **Get a Groq key:** https://console.groq.com — free tier is sufficient.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> `sentence-transformers` (~118 MB model) downloads automatically on first run.
> If you don't need ChromaDB RAG mode, you can comment out `chromadb` in requirements.txt.

### 4. Set up the database

**SQLite (local dev — no config needed):**
The app falls back to SQLite automatically if no `DB_HOST` is set.

**MySQL (production):**
Fill in `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` in `.env`, then create the database.

### 5. Run the app

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

Default admin credentials are set in `auth.py` — change them before sharing the app.

---

## Project structure

```
app.py                  # Landing page + entry point
pages/
  1_Startup.py          # Diagnostic form + results for startups
  2_Admin.py            # Admin dashboard (programs, stats, settings, accounts)
config.py               # All constants (model, weights, timeouts, etc.)
app_settings.py         # Runtime settings persisted to settings.json
matcher.py              # Core matching pipeline (rule + semantic + LLM)
embeddings.py           # Sentence embedding helpers (encode, cosine similarity)
vector_store.py         # ChromaDB wrapper (optional RAG mode)
scoring.py              # Rule-based scoring functions (7 spider dimensions)
auth.py                 # Login, session management, user CRUD
database.py             # MySQL / SQLite connector
pdf_export.py           # PDF report generation
styles.py               # Shared CSS
resources.csv           # Program catalog (source of truth)
```

---

## Optional: ChromaDB RAG mode

For catalogs with 50+ programs, RAG mode is faster than in-memory cosine search.

**Build the index (once, or after adding new programs):**
```bash
python build_rag_index.py
```

**Enable in the Admin UI:**
Go to Admin > Parametres > toggle "Activer la base de donnees vectorielle (RAG)".

Or set `USE_RAG = True` in `config.py` to enable by default.

The `chroma_db/` folder is excluded from git — rebuild the index after cloning.

---

## Docker

```bash
docker build -t the-dot-matcher .
docker run -p 7860:7860 --env-file .env the-dot-matcher
```

The app runs on port 7860 inside the container.

---

## Environment variables reference

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Groq LLM API key (llama-3.1-8b-instant) |
| `DB_HOST` | No | MySQL host (omit for SQLite fallback) |
| `DB_PORT` | No | MySQL port (default 3306) |
| `DB_NAME` | No | MySQL database name |
| `DB_USER` | No | MySQL username |
| `DB_PASSWORD` | No | MySQL password |

See `.env.example` for the full template.

---

## Tech stack

- **Frontend:** Streamlit
- **Scoring:** Rule-based (Python) + Semantic (sentence-transformers MiniLM)
- **LLM:** Groq (llama-3.1-8b-instant), Ollama local fallback
- **Vector store:** ChromaDB (optional)
- **Database:** MySQL (prod) / SQLite (dev)
- **Auth:** bcrypt password hashing
- **PDF export:** fpdf2
