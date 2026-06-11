"""
needs_engine.py
Converts a startup diagnostic (fiche) into a structured needs profile.
Includes stage validation — detects and corrects inconsistent self-reported stages.
"""

STAGE_ORDER = ["ideation", "pre-seed", "seed", "growth", "scale"]


def validate_stage(diag: dict) -> tuple:
    """
    Cross-checks the self-reported stage against actual maturity signals.
    Returns (corrected_stage, warning_message | None).

    A warning is returned whenever the stated stage is inconsistent with
    the evidence — so the UI can show the founder what we detected.
    """
    stated   = diag.get("stage", "pre-seed")
    has_product   = diag.get("has_product",   False)
    has_customers = diag.get("has_customers", False)
    has_revenue   = diag.get("has_revenue",   False)

    # ── Overstated stage (founder claims more than evidence shows) ─────────
    if stated == "scale" and not has_revenue:
        return "seed", (
            "⚠️ Stage adjusted: you selected **Scale** but have no revenue yet. "
            "Based on your answers we set your stage to **Seed** for matching purposes."
        )

    if stated == "growth" and not has_revenue:
        corrected = "seed" if has_customers else "pre-seed"
        label = corrected.capitalize()
        return corrected, (
            f"⚠️ Stage adjusted: you selected **Growth** but have no revenue. "
            f"Based on your answers we set your stage to **{label}** for matching purposes."
        )

    if stated == "seed" and not has_product and not has_customers:
        return "pre-seed", (
            "⚠️ Stage adjusted: you selected **Seed** but have no product or customers yet. "
            "We set your stage to **Pre-seed** for matching purposes."
        )

    if stated == "pre-seed" and not has_product:
        # pre-seed without product is fine — ideation is the only thing lower
        # only flag if they also claim customers/revenue (contradictory)
        if has_customers or has_revenue:
            return "seed", (
                "⚠️ Stage adjusted: you selected **Pre-seed** but already have customers or revenue. "
                "We set your stage to **Seed** for matching purposes."
            )

    # ── Understated stage (founder is more advanced than they think) ───────
    if stated in ("ideation", "pre-seed") and has_revenue:
        return "seed", (
            "ℹ️ Stage adjusted: you selected **" + stated.capitalize() + "** but already have revenue. "
            "We set your stage to **Seed** — you're further along than you think!"
        )

    # No inconsistency found
    return stated, None


def infer_needs(diag: dict) -> dict:
    """
    Input:  diag  – dictionary from the diagnostic form
    Output: needs_profile – enriched dict used by the matcher
    """
    needs = set()
    flags = {}

    # ── Stage validation ───────────────────────────────────────────────────
    corrected_stage, stage_warning = validate_stage(diag)
    flags["stage"]          = corrected_stage
    flags["stated_stage"]   = diag.get("stage", "pre-seed")
    flags["stage_warning"]  = stage_warning   # None if no inconsistency
    flags["stage_corrected"] = corrected_stage != diag.get("stage", "pre-seed")

    stage = corrected_stage   # use corrected stage for all downstream logic

    if stage in ("ideation", "pre-seed"):
        needs.update(["workspace", "community", "networking"])

    # ── Legal ──────────────────────────────────────────────────────────────
    legal_status = diag.get("legal_status", "")
    flags["legal_gap"] = legal_status in ("not_incorporated", "in_progress")
    if flags["legal_gap"]:
        needs.update(["legal_structuring", "incorporation", "fiscal"])

    # ── Team ──────────────────────────────────────────────────────────────
    team_size = diag.get("team_size", 1)
    flags["solo_founder"] = team_size == 1
    has_tech = diag.get("has_tech_cofounder", False)
    has_biz  = diag.get("has_business_cofounder", False)
    flags["team_gap"] = flags["solo_founder"] or (not has_tech and not has_biz)

    if flags["team_gap"]:
        needs.update(["networking", "mentorship"])
    if not has_tech and stage not in ("ideation",):
        needs.add("technology")

    # ── Traction / Maturity ───────────────────────────────────────────────
    has_product   = diag.get("has_product",   False)
    has_revenue   = diag.get("has_revenue",   False)
    has_customers = diag.get("has_customers", False)
    flags["has_traction"] = has_revenue or has_customers
    flags["pre_product"]  = not has_product

    if not has_product:
        needs.update(["strategy", "product", "mentorship"])
    if has_product and not has_customers:
        needs.update(["go_to_market", "marketing", "sales"])
    if has_customers and not has_revenue:
        needs.update(["sales", "pricing_strategy"])

    # ── Funding ───────────────────────────────────────────────────────────
    funding_need = diag.get("funding_need", "none")
    flags["needs_funding"] = funding_need != "none"
    flags["funding_need"]  = funding_need

    if funding_need == "grant":
        needs.update(["grant_access", "financial_modeling"])
    elif funding_need == "vc":
        needs.update(["fundraising", "investor_readiness", "vc_access", "deal_structuring"])
    elif funding_need == "angel":
        needs.update(["fundraising", "investor_readiness"])
    elif funding_need == "institutional":
        needs.update(["institutional_funding", "co_investment"])

    if flags["needs_funding"] and stage in ("seed", "growth", "scale"):
        needs.add("investment_readiness")

    # ── Market ────────────────────────────────────────────────────────────
    market_type = diag.get("market_type", "local")
    flags["international"] = market_type in ("regional", "international")
    flags["market_type"]   = market_type

    if flags["international"]:
        needs.update(["internationalization", "eu_network", "regional_expansion"])

    # ── Diaspora ──────────────────────────────────────────────────────────
    flags["diaspora"] = diag.get("diaspora_founder", False)
    if flags["diaspora"]:
        needs.update(["diaspora_support", "soft_landing", "coaching"])

    # ── Regional ──────────────────────────────────────────────────────────
    flags["outside_tunis"] = diag.get("outside_tunis", False)
    if flags["outside_tunis"]:
        needs.add("regional_support")

    # ── Marketing / Branding ──────────────────────────────────────────────
    has_brand     = diag.get("has_branding", False)
    needs_content = diag.get("needs_content_production", False)
    if not has_brand:
        needs.update(["branding", "communication"])
    if needs_content:
        needs.update(["content_creation", "design"])

    # ── B2B ───────────────────────────────────────────────────────────────
    business_model = diag.get("business_model", "b2c")
    flags["b2b"] = business_model in ("b2b", "b2b2c")
    if flags["b2b"] and stage not in ("ideation",):
        needs.update(["b2b", "partnerships", "sales"])
    if stage in ("growth", "scale"):
        needs.update(["market_access", "distribution", "partnerships"])

    # ── Workspace ─────────────────────────────────────────────────────────
    if diag.get("needs_workspace", False):
        needs.add("workspace")
        if stage in ("seed", "pre-seed"):
            needs.add("hosting")

    # ── Tech flags ────────────────────────────────────────────────────────
    flags["foreign_entity"] = diag.get("legal_status") == "foreign_entity"
    flags["seeking_vc"]     = diag.get("seeking_investors", False) or funding_need in ("vc", "angel")
    flags["is_ai"]          = diag.get("is_ai_startup", False)
    flags["is_industry40"]  = diag.get("is_industry40", False)
    flags["is_mobile"]      = diag.get("is_mobile_focused", False)

    flags["needs"] = list(needs)
    flags["sector"] = diag.get("sector", "other")

    return flags