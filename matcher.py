"""
matcher.py — LLM-powered resource matcher for The Dot
Matching chain: Groq (fast cloud) → Ollama (local) → Rule-based (always works)

Performance optimization: rule-based pre-filter sends only top candidates
to the LLM, keeping prompt size small and response time fast (~3-4s).
"""

import json
import pandas as pd

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL   = "llama-3.1-8b-instant"
OLLAMA_MODEL = "llama3.2"
OLLAMA_URL   = "http://localhost:11434/api/generate"

# How many candidates to send to the LLM (after rule-based pre-filter)
LLM_CANDIDATE_LIMIT = 8
# Max chars for prose fields in the LLM prompt (full text stays in CSV for display)
PROSE_TRUNCATE = 90


# ── Load resources ─────────────────────────────────────────────────────────────

def load_resources(path="resources.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    list_cols = ["stages", "needs", "sectors"]
    for col in list_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: [s.strip() for s in str(x).split(",")])
    if "diaspora_only" in df.columns:
        df["diaspora_only"] = df["diaspora_only"].astype(str).str.lower() == "true"
    if "international_focus" in df.columns:
        df["international_focus"] = df["international_focus"].astype(str).str.lower() == "true"
    return df


# ── Hard filters (always applied before any matching) ─────────────────────────

def apply_hard_filters(df: pd.DataFrame, profile: dict) -> pd.DataFrame:
    filtered = []
    for _, row in df.iterrows():
        if row.get("diaspora_only") and not profile.get("diaspora"):
            continue
        filtered.append(row)
    return pd.DataFrame(filtered)


# ── Rule-based scorer (used both as fallback AND pre-filter) ──────────────────

def rule_based_score(resource: pd.Series, profile: dict) -> tuple:
    """
    Deterministic scoring used when all LLM options are unavailable,
    and also to pre-filter candidates before sending to the LLM.
    Returns (score, reasons_list).
    """
    score = 0.0
    reasons = []
    startup_needs  = set(profile.get("needs", []))
    startup_stage  = profile.get("stage", "pre-seed")
    startup_sector = profile.get("sector", "other")

    # Stage match (30 pts)
    if startup_stage in resource["stages"]:
        score += 30
        reasons.append(f"Matches your current stage ({startup_stage})")
    else:
        score -= 10

    # Needs overlap (up to 40 pts)
    resource_needs = set(resource["needs"])
    overlap = startup_needs & resource_needs
    if overlap:
        score += min(len(overlap) * 7, 40)
        readable = [n.replace("_", " ") for n in overlap]
        reasons.append(f"Covers: {', '.join(readable)}")

    # Sector match bonus
    if "all" in resource["sectors"] or startup_sector in resource["sectors"]:
        score += 10

    # Flag bonuses
    if profile.get("diaspora") and resource.get("diaspora_only"):
        score += 20
        reasons.append("Purpose-built for diaspora founders")

    if profile.get("legal_gap") and any(n in resource["needs"] for n in ["legal_structuring", "incorporation", "fiscal"]):
        score += 15
        reasons.append("Directly addresses your legal gap (priority blocker)")

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
    """Truncate a prose string for the LLM prompt to keep tokens low."""
    if not text or len(str(text)) <= max_chars:
        return str(text) if text else ""
    return str(text)[:max_chars].rsplit(" ", 1)[0] + "…"


# ── Prompt builder ─────────────────────────────────────────────────────────────

def build_prompt(profile: dict, resources_df: pd.DataFrame, spider_scores: dict = None) -> str:
    """
    Build the LLM prompt. resources_df should already be pre-filtered to
    LLM_CANDIDATE_LIMIT rows — do NOT pass the full CSV here.
    Prose fields are truncated to PROSE_TRUNCATE chars to keep token count low.
    """
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

    # Spider scores section
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

    # Resource catalogue — prose fields truncated to keep prompt small
    resources_text = ""
    for _, row in resources_df.iterrows():
        ideal   = _truncate(row.get("ideal_profile", ""), PROSE_TRUNCATE)
        not_for = _truncate(row.get("not_suited_for", ""), PROSE_TRUNCATE)
        seq     = _truncate(row.get("sequencing_note", ""), PROSE_TRUNCATE)
        resources_text += (
            f"\n---\nID: {row['id']} | {row['name']} ({row['type']})\n"
            f"Description: {row['description']}\n"
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
- advice: one actionable sentence
- Return raw JSON array only.
"""
    return prompt


# ── LLM call: Groq ────────────────────────────────────────────────────────────

def _call_groq(prompt: str) -> list:
    from groq import Groq
    client   = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=2000,
    )
    raw = response.choices[0].message.content.strip()
    return _parse_json(raw)


# ── LLM call: Ollama (local fallback) ─────────────────────────────────────────

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
    with urllib.request.urlopen(req, timeout=90) as resp:
        result = json.loads(resp.read().decode())
    raw = result.get("response", "").strip()
    return _parse_json(raw)


# ── JSON extraction helper ─────────────────────────────────────────────────────

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

def match(profile: dict, resources_path="resources.csv", top_n=8, spider_scores: dict = None) -> list:
    """
    Matching chain:
      1. Groq (cloud LLM, fast)         — preferred
      2. Ollama (local LLM, slower)     — fallback if Groq fails
      3. Rule-based scorer              — always works, no dependencies

    Performance: rule-based pre-filter runs first to select top LLM_CANDIDATE_LIMIT
    candidates. Only those are sent to the LLM, keeping prompts small and fast.
    """
    df_all      = load_resources(resources_path)
    df_filtered = apply_hard_filters(df_all, profile)
    resource_lookup = {row["id"]: row for _, row in df_all.iterrows()}

    # ── Pre-filter: rule-based score on all filtered resources ────────────────
    # This keeps the LLM prompt small regardless of catalogue size.
    pre_scores = []
    for _, row in df_filtered.iterrows():
        sc, _ = rule_based_score(row, profile)
        pre_scores.append((sc, row["id"]))

    pre_scores.sort(reverse=True)
    top_ids = {rid for _, rid in pre_scores[:LLM_CANDIDATE_LIMIT]}
    df_candidates = df_filtered[df_filtered["id"].isin(top_ids)].copy()

    print(f"[matcher] Pre-filter: {len(df_filtered)} → {len(df_candidates)} candidates sent to LLM")

    prompt = build_prompt(profile, df_candidates, spider_scores=spider_scores)
    print(f"[matcher] Prompt size: ~{len(prompt)//4} tokens")

    # ── Layer 1: Groq ─────────────────────────────────────────────────────────
    llm_results = None
    llm_source  = None

    try:
        llm_results = _call_groq(prompt)
        llm_source  = "groq"
        print("[matcher] Groq succeeded.")
    except Exception as e:
        print(f"[matcher] Groq unavailable ({type(e).__name__}: {e}). Trying Ollama...")

    # ── Layer 2: Ollama ───────────────────────────────────────────────────────
    if llm_results is None:
        try:
            llm_results = _call_ollama(prompt)
            llm_source  = "ollama"
            print("[matcher] Ollama succeeded.")
        except Exception as e:
            print(f"[matcher] Ollama unavailable ({type(e).__name__}: {e}). Using rule-based fallback.")

    # ── Layer 3: Rule-based (full fallback — runs on all filtered resources) ──
    if llm_results is None:
        results = []
        for _, row in df_filtered.iterrows():
            score, reasons = rule_based_score(row, profile)
            if score > 0:
                results.append({
                    "id":          row["id"],
                    "name":        row["name"],
                    "type":        row["type"],
                    "description": row["description"],
                    "score":       round(score, 1),
                    "priority":    "short-term",
                    "reasons":     reasons,
                    "advice":      "",
                    "url":         row["url"],
                    "llm_powered": False,
                    "llm_source":  "rule-based",
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_n]

    # ── Merge LLM results with CSV ground truth ────────────────────────────────
    results = []
    for item in llm_results:
        rid = item.get("id")
        if rid not in resource_lookup:
            continue
        row = resource_lookup[rid]
        results.append({
            "id":          rid,
            "name":        row["name"],
            "type":        row["type"],
            "description": row["description"],
            "score":       item.get("score", 50),
            "priority":    item.get("priority", "short-term"),
            "reasons":     item.get("reasons", []),
            "advice":      item.get("advice", ""),
            "url":         row["url"],
            "llm_powered": True,
            "llm_source":  llm_source,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]