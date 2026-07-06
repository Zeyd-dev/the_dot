"""
scoring.py — Startup maturity spider scoring for The Dot Resource Matcher.
Extracted from pages/1_Startup.py so the logic can be unit-tested and reused
without importing Streamlit.
"""

from config import MATURITY_DIMS, MATURITY_DIM_KEYS


def spider_score(dim: str, diag: dict, effective_stage: str) -> int:
    """
    Compute a 0–100 maturity score for one radar dimension.

    Args:
        dim:             Dimension key (lowercase): team, legal, product, etc.
        diag:            Raw diagnostic dict from the form.
        effective_stage: Stage after validation by needs_engine.validate_stage().

    Returns:
        int: 0–100 score.
    """
    # ── Team ──────────────────────────────────────────────────────────────────
    if dim == "team":
        team_size          = diag.get("team_size", 1)
        has_tech_cofounder = diag.get("has_tech_cofounder", False)
        has_biz_cofounder  = diag.get("has_business_cofounder", False)
        if team_size >= 3 and has_tech_cofounder and has_biz_cofounder:
            return 100
        if team_size >= 2 and (has_tech_cofounder or has_biz_cofounder):
            return 65
        if team_size >= 2:
            return 40
        return 20

    # ── Legal ─────────────────────────────────────────────────────────────────
    if dim == "legal":
        legal_status      = diag.get("legal_status", "not_incorporated")
        has_startup_label = diag.get("has_startup_label", False)
        base = {
            "not_incorporated":   5,
            "in_progress":        30,
            "incorporated_suarl": 70,
            "incorporated_sarl":  75,
            "incorporated_sa":    85,
            "foreign_entity":     60,
        }.get(legal_status, 20)
        return min(base + (15 if has_startup_label else 0), 100)

    # ── Product ───────────────────────────────────────────────────────────────
    if dim == "product":
        if diag.get("has_revenue"):
            return 100
        if diag.get("has_customers"):
            return 80
        if diag.get("has_product"):
            return 55
        if effective_stage == "pre-seed":
            return 30
        return 10

    # ── Traction ──────────────────────────────────────────────────────────────
    if dim == "traction":
        has_revenue   = diag.get("has_revenue", False)
        has_customers = diag.get("has_customers", False)
        has_product   = diag.get("has_product", False)
        if has_revenue and has_customers:
            return 90
        if has_revenue:
            return 75
        if has_customers:
            return 55
        if has_product:
            return 30
        return 10

    # ── Funding ───────────────────────────────────────────────────────────────
    if dim == "funding":
        funding_need = diag.get("funding_need", "none")
        if funding_need == "none":
            return 50
        if funding_need == "vc" and effective_stage in ("growth", "scale"):
            return 70
        if funding_need == "angel" and effective_stage in ("seed", "pre-seed"):
            return 60
        if funding_need == "grant":
            return 55
        return 35

    # ── Market ────────────────────────────────────────────────────────────────
    if dim == "market":
        market_type = diag.get("market_type", "local")
        if market_type == "international" and diag.get("has_revenue"):
            return 90
        if market_type == "regional":
            return 65
        if market_type == "international":
            return 55
        if diag.get("has_customers"):
            return 50
        return 25

    # ── Branding ──────────────────────────────────────────────────────────────
    if dim == "branding":
        sc = 0
        if diag.get("has_branding"):
            sc += 60
        if not diag.get("needs_content_production"):
            sc += 20
        if effective_stage in ("growth", "scale"):
            sc += 20
        return min(sc, 100)

    return 0


def compute_spider_scores(diag: dict, effective_stage: str) -> dict:
    """
    Compute all 7 maturity dimension scores at once.

    Returns:
        dict mapping display dimension names (e.g. "Team") → int score 0–100.
    """
    return {
        dim: spider_score(key, diag, effective_stage)
        for dim, key in zip(MATURITY_DIMS, MATURITY_DIM_KEYS)
    }
