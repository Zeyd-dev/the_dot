"""
matcher.py — LLM-powered resource matcher for The Dot
Matching chain: Groq (fast cloud) → Ollama (local) → Rule-based (always works)

Performance optimization: rule-based pre-filter sends only top candidates
to the LLM, keeping prompt size small and response time fast (~3-4s).

Improvements:
  - "stages_raw" included in all result dicts so build_eligibility_checklist
    can compare the real programme stages instead of falling back to
    [effective_stage].
  - Groq calls now have an explicit timeout (GROQ_TIMEOUT) so a slow response
    never blocks the Streamlit UI indefinitely.
  - load_resources() is cached with @st.cache_data to avoid re-reading the CSV
    on every match() call (was previously re-read on every user interaction).
  - LLM config (model names, URL, timeout) imported from config.py.
"""

import json
import os

import pandas as pd

# Streamlit cache is optional — when matcher.py is imported by FastAPI (api.py),
# st is unavailable.  We fall back to a no-op decorator so the functions work
# identically without caching.
try:
    import streamlit as st
    _cache = st.cache_data(show_spinner=False)
except Exception:
    def _cache(fn=None, **_kw):
        if fn is None:
            return lambda f: f
        return fn
    class _StStub:
        @staticmethod
        def cache_data(show_spinner=False):
            return _cache
    st = _StStub()

_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_ENV_PATH)
except ImportError:
    pass

from config import (
    GROQ_MODEL,
    OLLAMA_MODEL,
    OLLAMA_URL,
    OLLAMA_TIMEOUT,
)
import app_settings as _settings
from embeddings import encode_resources, semantic_scores as compute_semantic_scores

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

PROSE_TRUNCATE = 90
DESC_TRUNCATE  = 140


# ── Load resources (cached) ────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _cached_resource_embeddings(path: str = "resources.csv") -> dict:
    """
    Encode all resources into embedding vectors and cache the result.
    This runs once per Streamlit server session (~2-3s on first load, then instant).
    Returns a plain dict (resource_id → list) — st.cache_data requires
    JSON-serialisable types, so we convert numpy arrays to lists here and
    restore them in the caller.

    A 30-second timeout guards against slow first-time model downloads:
    if the model isn't ready in time, we return {} and fall back to
    pure rule-based scoring — the app stays responsive.
    """
    import concurrent.futures
    df = load_resources(path)

    def _encode():
        raw = encode_resources(df)
        return {rid: vec.tolist() for rid, vec in raw.items()}

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_encode)
            return future.result(timeout=30)
    except concurrent.futures.TimeoutError:
        print("[matcher] Embedding model load timed out (>30s). Falling back to rule-based scoring.")
        return {}
    except Exception as e:
        print(f"[matcher] Embeddings unavailable ({e}). Semantic scoring disabled.")
        return {}


def _load_from_supabase() -> "pd.DataFrame | None":
    """Try to load programs from Supabase. Returns None on any failure."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        return None
    try:
        import psycopg2, psycopg2.extras
        conn = psycopg2.connect(db_url, sslmode="require")
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM programs ORDER BY id")
        rows = cur.fetchall()
        cur.close(); conn.close()
        if not rows:
            return None
        df = pd.DataFrame([dict(r) for r in rows])
        # Drop internal Supabase columns if present
        df = df.drop(columns=[c for c in ("created_at", "updated_at") if c in df.columns])
        print(f"[matcher] Loaded {len(df)} programs from Supabase")
        return df
    except Exception as e:
        print(f"[matcher] Supabase program load failed: {e}")
        return None


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Apply shared normalization (list cols, bools, optional cols)."""
    list_cols = ["stages", "needs", "sectors"]
    for col in list_cols:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: [s.strip() for s in str(x).split(",")] if isinstance(x, str) else (x if isinstance(x, list) else [])
            )
    for bool_col in ("diaspora_only", "outside_hub_only", "international_focus"):
        if bool_col in df.columns:
            df[bool_col] = df[bool_col].apply(
                lambda x: bool(x) if isinstance(x, bool) else str(x).lower() == "true"
            )
    for opt_col in ("duration", "deliverables", "key_benefit", "ideal_profile"):
        if opt_col not in df.columns:
            df[opt_col] = ""
        else:
            df[opt_col] = df[opt_col].fillna("")
    return df


@st.cache_data(show_spinner=False)
def load_resources(path: str = "resources.csv") -> pd.DataFrame:
    """
    Load programs from Supabase (if available), falling back to resources.csv.
    Cached with @st.cache_data in Streamlit context; runs fresh in FastAPI context.
    """
    df = _load_from_supabase()
    if df is not None and len(df) > 0:
        return _normalize_df(df)

    # Fallback: read from CSV
    print(f"[matcher] Falling back to CSV: {path}")
    df = pd.read_csv(path)
    return _normalize_df(df)


# ── Hard filters ───────────────────────────────────────────────────────────────

def apply_hard_filters(df: pd.DataFrame, profile: dict) -> pd.DataFrame:
    filtered = []
    for _, row in df.iterrows():
        if row.get("diaspora_only") and not profile.get("diaspora"):
            continue
        if row.get("outside_hub_only") and not profile.get("outside_tunis"):
            continue
        filtered.append(row)
    return pd.DataFrame(filtered)


# ── Rule-based scorer ──────────────────────────────────────────────────────────

def rule_based_score(resource: pd.Series, profile: dict) -> tuple:
    score = 0.0
    reasons = []
    startup_needs  = set(profile.get("needs", []))
    startup_stage  = profile.get("stage", "pre-seed")
    startup_sector = profile.get("sector", "other")

    if startup_stage in resource["stages"]:
        score += 30
        reasons.append(f"Matches your current stage ({startup_stage})")
    else:
        score -= 10

    resource_needs = set(resource["needs"])
    overlap = startup_needs & resource_needs
    if overlap:
        score += min(len(overlap) * 7, 40)
        readable = [n.replace("_", " ") for n in overlap]
        reasons.append(f"Covers: {', '.join(readable)}")

    if "all" in resource["sectors"] or startup_sector in resource["sectors"]:
        score += 10

    if profile.get("diaspora") and resource.get("diaspora_only"):
        score += 20
        reasons.append("Purpose-built for diaspora founders")

    if profile.get("legal_gap") and any(n in resource["needs"] for n in ["legal_structuring", "incorporation", "fiscal"]):
        score += 15
        reasons.append("Directly addresses your legal gap (priority blocker)")

    # Dot Expert bonus — very relevant for legal/financial needs at any stage
    if resource.get("id") == "R005":
        if profile.get("legal_gap"):
            score += 20
            reasons.append("Certified expert can guide your legal structuring immediately")
        if profile.get("needs_funding") and profile.get("seeking_vc"):
            score += 20
            reasons.append("Expert pitch review and fundraising strategy sessions available")
        if profile.get("has_ip"):
            score += 10
            reasons.append("IP protection and patent advice available through expert sessions")

    if profile.get("needs_funding") and any(n in resource["needs"] for n in ["fundraising", "investment_readiness", "vc_access"]):
        score += 15
        reasons.append("Supports your fundraising path")

    if profile.get("team_gap") and any(n in resource["needs"] for n in ["mentorship", "networking", "team_building"]):
        score += 10
        reasons.append("Helps compensate team gaps")

    if profile.get("outside_tunis") and "regional_support" in resource["needs"]:
        score += 20
        reasons.append("Specifically designed for regional (non-Tunis) startups")

    if profile.get("foreign_entity") and resource.get("international_focus"):
        score += 20
        reasons.append("Designed for foreign entities entering Tunisia")

    if profile.get("is_ai") and "ai" in resource["needs"]:
        score += 15
        reasons.append("Sector-specific: AI/ML focus")

    if profile.get("is_industry40") and any(n in resource["needs"] for n in ["tech_support"]) and startup_sector in resource["sectors"]:
        score += 15
        reasons.append("Sector-specific: Industry 4.0 focus")

    return max(score, 0), reasons


def _truncate(text: str, max_chars: int) -> str:
    if not text or len(str(text)) <= max_chars:
        return str(text) if text else ""
    return str(text)[:max_chars].rsplit(" ", 1)[0] + "…"


# ── Prompt builder ─────────────────────────────────────────────────────────────

def build_prompt(profile: dict, resources_df: pd.DataFrame, spider_scores: dict = None) -> str:
    profile_json = json.dumps({
        "stage":           profile.get("stage"),
        "stated_stage":    profile.get("stated_stage"),
        "stage_corrected": profile.get("stage_corrected", False),
        "sector":          profile.get("sector"),
        "business_model":  profile.get("business_model", "unknown"),
        "market":          profile.get("market_type", "local"),
        "needs":           profile.get("needs", []),
        "flags": {
            "legal_gap":      profile.get("legal_gap"),
            "team_gap":       profile.get("team_gap"),
            "solo_founder":   profile.get("solo_founder"),
            "has_traction":   profile.get("has_traction"),
            "pre_product":    profile.get("pre_product"),
            "needs_funding":  profile.get("needs_funding"),
            "funding_need":   profile.get("funding_need"),
            "diaspora":       profile.get("diaspora"),
            "outside_tunis":  profile.get("outside_tunis"),
            "international":  profile.get("international"),
            "foreign_entity": profile.get("foreign_entity"),
            "seeking_vc":     profile.get("seeking_vc"),
            "b2b":            profile.get("b2b"),
            "is_ai":          profile.get("is_ai"),
            "is_industry40":  profile.get("is_industry40"),
        }
    }, indent=2)

    spider_section = ""
    if spider_scores:
        spider_section = "\nMATURITY SCORES (0-100):\n"
        for dim, sc in spider_scores.items():
            level = "STRONG" if sc >= 70 else ("MODERATE" if sc >= 40 else "WEAK")
            spider_section += f"  {dim}: {sc} ({level})\n"
        spider_section += (
            "Use scores to adjust priority: WEAK dims = higher priority resources. "
            "STRONG dims = lower priority (founder already doing well there).\n"
        )

    resources_text = ""
    for _, row in resources_df.iterrows():
        desc    = _truncate(row.get("description", ""), DESC_TRUNCATE)
        ideal   = _truncate(row.get("ideal_profile", ""), PROSE_TRUNCATE)
        not_for = _truncate(row.get("not_suited_for", ""), PROSE_TRUNCATE)
        seq     = _truncate(row.get("sequencing_note", ""), PROSE_TRUNCATE)
        resources_text += (
            f"\n---\nID: {row['id']} | {row['name']} ({row['type']})\n"
            f"Description: {desc}\n"
            f"Ideal: {ideal}\n"
            f"Exclude if: {not_for}\n"
            f"Sequence: {seq}\n"
            f"Stages: {', '.join(row['stages'])} | "
            f"Needs: {', '.join(row['needs'])} | "
            f"Sectors: {', '.join(row['sectors'])}\n"
        )

    prompt = f"""You are a startup advisor at The Dot, Tunisia's leading startup hub.
Match this startup to the most relevant programs from the {len(resources_df)} pre-selected candidates below.

STARTUP PROFILE:
{profile_json}
{spider_section}
CANDIDATES:
{resources_text}

TASK: Re-rank and score these candidates by genuine fit for this startup.

Think through:
1. What are the startup's most critical blockers right now?
2. Which candidates match the "Ideal" description? Which match "Exclude if"?
3. Are any candidates mutually exclusive? Flag in advice.
4. What is the right ORDER? Use "Sequence" notes. Legal before fundraising. Product before GTM.
5. Do maturity scores confirm the profile? Let them adjust your ranking.

Return ONLY a valid JSON array. No explanation outside JSON. No markdown.

Format:
[
  {{
    "id": "R001",
    "score": 92,
    "priority": "immediate",
    "reasons": ["Specific reason tied to this startup", "Another reason"],
    "advice": "One concrete sentence: how this founder should use this resource and why now."
  }}
]

Rules:
- Only include resources with score >= 30
- score: 0-100 integer
- priority: "immediate" | "short-term" | "when-ready"
- reasons: 2-3 short strings, specific to THIS startup
- advice: one actionable sentence. Do NOT mention the resource ID (R001, R002, etc.) — refer to the programme by name only.
- Return raw JSON array only.
"""
    return prompt


# ── LLM calls ─────────────────────────────────────────────────────────────────

def _call_groq(prompt: str) -> list:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set in environment")
    from groq import Groq
    # Explicit timeout prevents an unresponsive Groq endpoint from hanging
    # the Streamlit UI indefinitely (previously had no timeout at all).
    client   = Groq(api_key=GROQ_API_KEY, timeout=_settings.get("groq_timeout"))
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=2000,
    )
    raw = response.choices[0].message.content.strip()
    return _parse_json(raw)


def _call_ollama(prompt: str) -> list:
    import urllib.request
    body = json.dumps({
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
        result = json.loads(resp.read().decode())
    raw = result.get("response", "").strip()
    return _parse_json(raw)


def _parse_json(raw: str) -> list:
    if "```" in raw:
        for part in raw.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("["):
                raw = part
                break
    start = raw.find("[")
    end   = raw.rfind("]") + 1
    if start == -1 or end <= start:
        raise ValueError("No JSON array found in LLM response")
    return json.loads(raw[start:end])


# ── Main match function ────────────────────────────────────────────────────────

def match(profile: dict, resources_path: str = "resources.csv", top_n: int = 8, spider_scores: dict = None) -> list:
    """
    Matching chain:
      1. Groq  (cloud LLM, fast)    — preferred
      2. Ollama (local LLM, slower) — fallback if Groq fails
      3. Rule-based scorer          — always works, no dependencies

    All result dicts include "stages_raw" (list of stages accepted by the
    programme), used by build_eligibility_checklist to display correct
    eligibility criteria.
    """
    df_all      = load_resources(resources_path)
    df_filtered = apply_hard_filters(df_all, profile)
    resource_lookup = {row["id"]: row for _, row in df_all.iterrows()}

    # ── Pre-filter: retrieve top candidates ───────────────────────────────────
    # Hybrid scoring: rule-based (60%) + semantic embeddings (40%)
    # Settings can be adjusted at runtime from the Admin panel.
    cfg              = _settings.load()
    rule_weight      = cfg["rule_weight"]
    semantic_weight  = cfg["semantic_weight"]
    candidate_limit  = cfg["llm_candidate_limit"]

    sem_scores: dict[str, float] = {}
    hybrid_scores: dict[str, float] = {}

    # ── In-memory hybrid scoring ──────────────────────────────────────────────
    try:
        import numpy as np
        raw_embeddings = _cached_resource_embeddings(resources_path)
        if raw_embeddings:
            np_embeddings = {rid: np.array(vec) for rid, vec in raw_embeddings.items()}
            sem_scores = compute_semantic_scores(profile, np_embeddings)
            print(f"[matcher] Semantic scores computed for {len(sem_scores)} resources.")
    except Exception as e:
        print(f"[matcher] Semantic scoring failed ({e}). Using rule-based only.")

    # Normalise semantic scores min-max so the 0.4 weight contributes a full 0–40 pt range.
    if sem_scores:
        s_min = min(sem_scores.values())
        s_max = max(sem_scores.values())
        sem_range = s_max - s_min
        if sem_range > 1e-6:
            sem_scores_norm = {
                rid: (s - s_min) / sem_range
                for rid, s in sem_scores.items()
            }
        else:
            sem_scores_norm = {rid: 0.5 for rid in sem_scores}
    else:
        sem_scores_norm = {}

    pre_scores = []
    hybrid_scores: dict[str, float] = {}
    for _, row in df_filtered.iterrows():
        rule_sc, _ = rule_based_score(row, profile)
        sem_sc     = sem_scores_norm.get(row["id"], 0.0)
        hybrid_sc  = (rule_weight * rule_sc + semantic_weight * sem_sc * 100
                      if sem_scores_norm else rule_sc)
        hybrid_scores[row["id"]] = round(hybrid_sc, 1)
        pre_scores.append((hybrid_sc, row["id"]))
    pre_scores.sort(reverse=True)
    top_ids = {rid for _, rid in pre_scores[:candidate_limit]}

    df_candidates = df_filtered[df_filtered["id"].isin(top_ids)].copy()

    print(f"[matcher] Pre-filter: {len(df_filtered)} → {len(df_candidates)} candidates sent to LLM")

    prompt = build_prompt(profile, df_candidates, spider_scores=spider_scores)
    print(f"[matcher] Prompt size: ~{len(prompt)//4} tokens")

    llm_results = None
    llm_source  = None

    try:
        llm_results = _call_groq(prompt)
        llm_source  = "groq"
        print("[matcher] Groq succeeded.")
    except Exception as e:
        print(f"[matcher] Groq unavailable ({type(e).__name__}: {e}). Trying Ollama...")

    if llm_results is None:
        try:
            llm_results = _call_ollama(prompt)
            llm_source  = "ollama"
            print("[matcher] Ollama succeeded.")
        except Exception as e:
            print(f"[matcher] Ollama unavailable ({type(e).__name__}: {e}). Using rule-based fallback.")

    # Fallback rule-based
    if llm_results is None:
        results = []
        for _, row in df_filtered.iterrows():
            score, reasons = rule_based_score(row, profile)
            if score > 0:
                results.append({
                    "id":            row["id"],
                    "name":          row["name"],
                    "type":          row["type"],
                    "description":   row["description"],
                    "score":         hybrid_scores.get(row["id"], round(score, 1)),
                    "priority":      "short-term",
                    "reasons":       reasons,
                    "advice":        "",
                    "justification": "",
                    "url":           row["url"],
                    "stages_raw":    list(row["stages"]),
                    "llm_powered":   False,
                    "llm_source":    "rule-based",
                    "semantic_score": round(sem_scores_norm.get(row["id"], 0.0) * 100, 1),
                    "duration":              row.get("duration", ""),
                    "deliverables":          row.get("deliverables", ""),
                    "key_benefit":           row.get("key_benefit", ""),
                    "eligibility_criteria":  row.get("ideal_profile", ""),
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_n]

    # Merge LLM results — score = hybrid (reliable), order = hybrid, text = LLM
    results = []
    for item in llm_results:
        rid = item.get("id")
        if rid not in resource_lookup:
            continue
        row = resource_lookup[rid]
        results.append({
            "id":            rid,
            "name":          row["name"],
            "type":          row["type"],
            "description":   row["description"],
            "score":         hybrid_scores.get(rid, round(item.get("score", 50), 1)),
            "priority":      item.get("priority", "short-term"),
            "reasons":       item.get("reasons", []),
            "advice":        item.get("advice", ""),
            "justification": item.get("justification", item.get("advice", "")),
            "url":           row["url"],
            "stages_raw":    list(row["stages"]),
            "llm_powered":   True,
            "llm_source":    llm_source,
            "semantic_score": round(sem_scores_norm.get(rid, 0.0) * 100, 1),
            "duration":              row.get("duration", ""),
            "deliverables":          row.get("deliverables", ""),
            "key_benefit":           row.get("key_benefit", ""),
            "eligibility_criteria":  row.get("ideal_profile", ""),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]
