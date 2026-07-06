"""
tests/test_needs_engine.py
Unit tests for needs_engine.validate_stage() and needs_engine.infer_needs().

Run with:  pytest tests/
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from needs_engine import validate_stage, infer_needs


# ── validate_stage ─────────────────────────────────────────────────────────────

class TestValidateStage:
    def test_no_change_when_consistent(self):
        diag = {"stage": "seed", "has_product": True, "has_customers": False, "has_revenue": False}
        stage, warning = validate_stage(diag)
        assert stage == "seed"
        assert warning is None

    def test_scale_without_revenue_corrected_to_seed(self):
        diag = {"stage": "scale", "has_product": True, "has_customers": True, "has_revenue": False}
        stage, warning = validate_stage(diag)
        assert stage == "seed"
        assert warning is not None
        assert "Scale" in warning

    def test_growth_without_revenue_with_customers_corrected_to_seed(self):
        diag = {"stage": "growth", "has_product": True, "has_customers": True, "has_revenue": False}
        stage, warning = validate_stage(diag)
        assert stage == "seed"
        assert warning is not None

    def test_growth_without_revenue_without_customers_corrected_to_pre_seed(self):
        diag = {"stage": "growth", "has_product": True, "has_customers": False, "has_revenue": False}
        stage, warning = validate_stage(diag)
        assert stage == "pre-seed"
        assert warning is not None

    def test_seed_without_product_or_customers_corrected_to_pre_seed(self):
        diag = {"stage": "seed", "has_product": False, "has_customers": False, "has_revenue": False}
        stage, warning = validate_stage(diag)
        assert stage == "pre-seed"
        assert warning is not None

    def test_pre_seed_with_customers_bumped_to_seed(self):
        diag = {"stage": "pre-seed", "has_product": False, "has_customers": True, "has_revenue": False}
        stage, warning = validate_stage(diag)
        assert stage == "seed"
        assert warning is not None

    def test_ideation_with_revenue_bumped_to_seed(self):
        diag = {"stage": "ideation", "has_product": False, "has_customers": False, "has_revenue": True}
        stage, warning = validate_stage(diag)
        assert stage == "seed"
        assert warning is not None
        assert "revenue" in warning.lower()

    def test_pre_seed_without_product_no_revenue_no_customers_unchanged(self):
        """Pre-seed + no product + no customers + no revenue is valid — ideation is the only lower stage."""
        diag = {"stage": "pre-seed", "has_product": False, "has_customers": False, "has_revenue": False}
        stage, warning = validate_stage(diag)
        assert stage == "pre-seed"
        assert warning is None

    def test_consistent_growth_stage(self):
        diag = {"stage": "growth", "has_product": True, "has_customers": True, "has_revenue": True}
        stage, warning = validate_stage(diag)
        assert stage == "growth"
        assert warning is None


# ── infer_needs ────────────────────────────────────────────────────────────────

class TestInferNeeds:
    def _base_diag(self, **overrides):
        base = {
            "stage": "seed", "sector": "tech", "business_model": "b2b",
            "market_type": "local", "diaspora_founder": False, "outside_tunis": False,
            "team_size": 2, "has_tech_cofounder": True, "has_business_cofounder": False,
            "legal_status": "incorporated_sarl", "has_startup_label": False,
            "has_branding": True, "has_product": True, "has_customers": False,
            "has_revenue": False, "funding_need": "none", "funding_range": "none",
            "is_ai_startup": False, "is_industry40": False, "is_mobile_focused": False,
            "needs_workspace": False, "needs_content_production": False,
            "needs_events_space": False, "needs_mentorship": False,
            "needs_market_access": False, "seeking_investors": False,
        }
        base.update(overrides)
        return base

    def test_returns_dict_with_needs_list(self):
        profile = infer_needs(self._base_diag())
        assert isinstance(profile, dict)
        assert "needs" in profile
        assert isinstance(profile["needs"], list)

    def test_legal_gap_adds_legal_needs(self):
        profile = infer_needs(self._base_diag(legal_status="not_incorporated"))
        assert "legal_structuring" in profile["needs"]
        assert "incorporation" in profile["needs"]
        assert profile["legal_gap"] is True

    def test_diaspora_adds_diaspora_needs(self):
        profile = infer_needs(self._base_diag(diaspora_founder=True))
        assert "diaspora_support" in profile["needs"]
        assert "soft_landing" in profile["needs"]

    def test_no_product_adds_strategy_needs(self):
        profile = infer_needs(self._base_diag(has_product=False))
        assert "strategy" in profile["needs"]
        assert "product" in profile["needs"]

    def test_vc_funding_adds_fundraising_needs(self):
        profile = infer_needs(self._base_diag(funding_need="vc", stage="seed"))
        assert "fundraising" in profile["needs"]
        assert "investor_readiness" in profile["needs"]
        assert "vc_access" in profile["needs"]

    def test_international_market_adds_internationalization(self):
        profile = infer_needs(self._base_diag(market_type="international"))
        assert "internationalization" in profile["needs"]

    def test_stage_correction_reflected_in_flags(self):
        """scale without revenue should be corrected to seed in the profile."""
        diag = self._base_diag(stage="scale", has_revenue=False, has_customers=True)
        profile = infer_needs(diag)
        assert profile["stage"] == "seed"
        assert profile["stage_corrected"] is True
        assert profile["stated_stage"] == "scale"

    def test_outside_tunis_adds_regional_support(self):
        profile = infer_needs(self._base_diag(outside_tunis=True))
        assert "regional_support" in profile["needs"]

    def test_solo_founder_flagged(self):
        profile = infer_needs(self._base_diag(team_size=1, has_tech_cofounder=False, has_business_cofounder=False))
        assert profile["solo_founder"] is True
        assert profile["team_gap"] is True
