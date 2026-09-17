"""
config.py — Centralized constants for The Dot Resource Matcher.
All UI display dicts, URLs, LLM settings, and dimension lists live here
so pages never need to hardcode values.
"""

# ── Scoring ────────────────────────────────────────────────────────────────────
RECOMMENDATION_MIN_SCORE = 40
LLM_CANDIDATE_LIMIT = 10       # max candidates forwarded to the LLM

# ── Program apply URLs (override resource CSV url for direct apply links) ──────
APPLY_URLS: dict = {
    "R001": "https://thedot.tn/programs-services/1-dot-camp",
    "R002": "https://thedot.tn/programs-services/1-dot-camp",
    "R003": "https://thedot.tn/programs-services/5-dot-landing",
    "R004": "https://thedot.tn/programs-services/4-dot-executives-in-residence",
    "R005": "https://thedot.tn",
    "R006": "https://thedot.tn/9-dot-community-services",
    "R007": "https://thedot.tn/6-digital-transformation-center",
    "R008": "https://tech216.de",
}

# ── Priority display mapping ───────────────────────────────────────────────────
# key → (fg_color, bg_color, border_color, icon, label)
PRIORITY: dict = {
    "immediate":  ("#be123c", "#fff1f2", "#fecaca", "🔴", "Do this now"),
    "short-term": ("#92400e", "#fffbeb", "#fde68a", "🟡", "Next 1–3 months"),
    "when-ready": ("#166534", "#f0fdf4", "#bbf7d0", "🟢", "When ready"),
}

# ── Resource type → badge colours ─────────────────────────────────────────────
# key → (fg_color, bg_color)
TYPE_COLORS: dict = {
    "program":    ("#1d4ed8", "#eff6ff"),
    "expertise":  ("#92400e", "#fef3c7"),
    "mentorship": ("#166534", "#dcfce7"),
    "service":    ("#6d28d9", "#f5f3ff"),
    "investment": ("#be123c", "#fff1f2"),
    "network":    ("#164e63", "#ecfeff"),
}

# ── Resource type → maturity dimensions boosted by completing this resource ────
RESOURCE_BOOST_MAP: dict = {
    "program":    ["product", "traction"],
    "expertise":  ["legal", "funding"],
    "mentorship": ["team", "market"],
    "service":    ["branding", "product"],
    "investment": ["funding", "traction"],
    "network":    ["market", "team"],
}

# ── Stage ordering ─────────────────────────────────────────────────────────────
STAGE_ORDER = ["ideation", "pre-seed", "seed", "growth", "scale"]

# ── Maturity dimensions (display order must match key order) ───────────────────
MATURITY_DIMS     = ["Team", "Legal", "Product", "Traction", "Funding", "Market", "Branding"]
MATURITY_DIM_KEYS = ["team", "legal",  "product", "traction", "funding", "market", "branding"]

# ── Groq LLM ──────────────────────────────────────────────────────────────────
GROQ_MODEL   = "llama-3.1-8b-instant"
GROQ_TIMEOUT = 15           # seconds — hard cutoff so a slow response never hangs the UI

# ── Ollama LLM ────────────────────────────────────────────────────────────────
OLLAMA_MODEL   = "llama3.2"
OLLAMA_URL     = "http://localhost:11434/api/generate"
OLLAMA_TIMEOUT = 90         # seconds

# ── Semantic Embeddings ────────────────────────────────────────────────────────
# Model: paraphrase-multilingual-MiniLM-L12-v2
#   - 118 MB, CPU-only, supports French/English/Arabic and 50+ languages
#   - Encodes text into 384-dimensional vectors capturing semantic meaning
#   - Downloaded automatically on first use via HuggingFace Hub
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Weight split between rule-based and semantic scoring in the pre-filter:
#   final_score = RULE_WEIGHT * rule_score + SEMANTIC_WEIGHT * semantic_score * 100
# Increase SEMANTIC_WEIGHT to rely more on AI understanding, less on tag matching.
RULE_WEIGHT     = 0.6
SEMANTIC_WEIGHT = 0.4
