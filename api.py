"""
api.py — FastAPI backend for The Dot Resource Matcher
Exposes the matching engine as a REST API so the React frontend can consume it.
Runs on port 7861 (or any port) alongside Streamlit.
"""

import json
import os
import sys
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from needs_engine import infer_needs
from scoring import compute_spider_scores
from config import MATURITY_DIMS, MATURITY_DIM_KEYS

app = FastAPI(title="The Dot Resource Matcher API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RESOURCES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources.csv")


# ── Request / Response schemas ──────────────────────────────────────────────

class DiagnosticRequest(BaseModel):
    startup_name: str
    sector: str = "tech"
    business_model: str = "b2b"
    business_model_type: str = "saas"
    market_type: str = "local"
    market_size: str = "medium"
    diaspora_founder: bool = False
    outside_tunis: bool = False
    stage: str = "pre-seed"
    has_product: bool = False
    has_customers: bool = False
    has_revenue: bool = False
    team_size: int = 1
    full_time_count: int = 1
    has_tech_cofounder: bool = False
    has_business_cofounder: bool = False
    has_competitive_advantage: bool = False
    has_ip_protection: bool = False
    legal_status: str = "not_incorporated"
    has_startup_label: bool = False
    has_branding: bool = False
    funding_need: str = "none"
    funding_range: str = "none"
    has_pitch_deck: bool = False
    seeking_investors: bool = False
    is_ai_startup: bool = False
    is_industry40: bool = False
    is_mobile_focused: bool = False
    needs_workspace: bool = False
    needs_content_production: bool = False
    needs_events_space: bool = False
    needs_mentorship: bool = False
    needs_market_access: bool = False
    needs_legal_expert: bool = False
    value_proposition: str = ""


class MatchResult(BaseModel):
    id: str
    name: str
    type: str
    description: str
    score: float
    priority: str
    reasons: list[str]
    advice: str
    url: str
    stages_raw: list[str]
    llm_powered: bool
    llm_source: str
    semantic_score: float
    duration: str = ""
    deliverables: str = ""
    key_benefit: str = ""


class DiagnosticResponse(BaseModel):
    startup_name: str
    effective_stage: str
    stage_warning: Optional[str]
    spider_scores: dict
    needs: list[str]
    results: list[dict]
    timestamp: str


# ── Match endpoint ──────────────────────────────────────────────────────────

@app.post("/api/match", response_model=DiagnosticResponse)
def run_match(req: DiagnosticRequest):
    diag = req.dict()

    # Build extra needs from booleans
    extra = []
    if req.needs_mentorship:        extra += ["mentorship", "strategy"]
    if req.needs_market_access:     extra += ["market_access", "distribution", "partnerships"]
    if req.seeking_investors:       extra += ["investor_readiness", "fundraising", "vc_access", "pitch"]
    if req.is_ai_startup:           extra += ["ai", "tech_support", "acceleration"]
    if req.is_industry40:           extra += ["tech_support", "acceleration", "partnerships"]
    if req.is_mobile_focused:       extra += ["mobile", "tech_support"]
    if req.needs_events_space or req.needs_workspace: extra += ["workspace", "events"]
    if req.needs_content_production: extra += ["content_production", "design", "branding"]
    if req.outside_tunis:           extra += ["regional_support"]
    if req.legal_status in ("not_incorporated", "in_progress"): extra += ["legal", "incorporation", "legal_structuring"]
    if req.market_type in ("regional", "international"):        extra += ["market_access"]
    if req.needs_legal_expert:      extra += ["legal_structuring", "fiscal", "coaching"]
    if req.has_ip_protection:       extra += ["ip_protection"]
    if not req.has_pitch_deck and req.funding_need != "none":  extra += ["pitch", "investor_readiness"]

    profile = infer_needs(diag)
    profile["needs"] = list(set(profile.get("needs", [])) | set(extra))
    profile["diaspora"]      = req.diaspora_founder
    profile["outside_tunis"] = req.outside_tunis
    profile["foreign_entity"]= (req.legal_status == "foreign_entity")
    profile["seeking_vc"]    = req.seeking_investors or req.funding_need in ("vc", "angel")
    profile["is_ai"]         = req.is_ai_startup
    profile["is_industry40"] = req.is_industry40
    profile["has_ip"]        = req.has_ip_protection

    effective_stage = profile.get("stage", req.stage)
    spider_scores = compute_spider_scores(diag, effective_stage)

    # Import here to avoid circular import at module level
    try:
        from matcher import match
        results = match(profile, resources_path=RESOURCES_PATH, spider_scores=spider_scores)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Matching engine error: {e}")

    # Compute eligibility: startup's effective stage must be in program's accepted stages
    for r in results:
        stages_raw = r.get("stages_raw", [])
        r["eligible"] = effective_stage in stages_raw if stages_raw else True
        # Normalize priority label: LLM uses "short-term" / "medium-term" etc.
        p = r.get("priority", "")
        if "high" in p or "short" in p:
            r["priority"] = "high"
        elif "medium" in p or "mid" in p:
            r["priority"] = "medium"
        else:
            r["priority"] = "low"

    return DiagnosticResponse(
        startup_name=req.startup_name,
        effective_stage=effective_stage,
        stage_warning=profile.get("stage_warning"),
        spider_scores=spider_scores,
        needs=sorted(profile.get("needs", [])),
        results=results,
        timestamp=datetime.now().isoformat(),
    )


@app.get("/api/programs")
def list_programs():
    try:
        import pandas as pd
        df = pd.read_csv(RESOURCES_PATH)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0"}


# ── Serve React frontend (if built) ────────────────────────────────────────────
# When `npm run build` has been run inside ./frontend/, the static files land in
# ./static_frontend/.  Mount them AFTER the /api routes so the API takes priority.

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static_frontend")

if os.path.isdir(_STATIC_DIR):
    # Serve assets (JS/CSS/images)
    app.mount("/assets", StaticFiles(directory=os.path.join(_STATIC_DIR, "assets")), name="assets")

    # SPA fallback — every non-API route returns index.html so React Router works
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        index = os.path.join(_STATIC_DIR, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return {"error": "Frontend not built. Run: cd frontend && npm run build"}

