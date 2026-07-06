"""
tests/test_scoring.py
Unit tests for scoring.spider_score() and scoring.compute_spider_scores().

Run with:  pytest tests/
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from scoring import spider_score, compute_spider_scores


# ── Team ──────────────────────────────────────────────────────────────────────

class TestTeamScore:
    def test_solo_founder_returns_20(self):
        assert spider_score("team", {"team_size": 1}, "seed") == 20

    def test_two_founders_no_cofounder_type_returns_40(self):
        assert spider_score("team", {"team_size": 2, "has_tech_cofounder": False, "has_business_cofounder": False}, "seed") == 40

    def test_two_founders_with_tech_returns_65(self):
        assert spider_score("team", {"team_size": 2, "has_tech_cofounder": True, "has_business_cofounder": False}, "seed") == 65

    def test_full_team_returns_100(self):
        assert spider_score("team", {"team_size": 3, "has_tech_cofounder": True, "has_business_cofounder": True}, "seed") == 100


# ── Legal ─────────────────────────────────────────────────────────────────────

class TestLegalScore:
    def test_not_incorporated_returns_5(self):
        assert spider_score("legal", {"legal_status": "not_incorporated"}, "seed") == 5

    def test_incorporated_sa_returns_85(self):
        assert spider_score("legal", {"legal_status": "incorporated_sa"}, "seed") == 85

    def test_startup_label_adds_15(self):
        score = spider_score("legal", {"legal_status": "incorporated_sarl", "has_startup_label": True}, "seed")
        assert score == 75 + 15  # 90

    def test_max_capped_at_100(self):
        score = spider_score("legal", {"legal_status": "incorporated_sa", "has_startup_label": True}, "seed")
        assert score == 100


# ── Product ───────────────────────────────────────────────────────────────────

class TestProductScore:
    def test_no_product_seed_returns_10(self):
        assert spider_score("product", {"has_product": False, "has_customers": False, "has_revenue": False}, "seed") == 10

    def test_no_product_pre_seed_returns_30(self):
        assert spider_score("product", {"has_product": False, "has_customers": False, "has_revenue": False}, "pre-seed") == 30

    def test_has_product_no_customers_returns_55(self):
        assert spider_score("product", {"has_product": True, "has_customers": False, "has_revenue": False}, "seed") == 55

    def test_has_customers_returns_80(self):
        assert spider_score("product", {"has_product": True, "has_customers": True, "has_revenue": False}, "seed") == 80

    def test_has_revenue_returns_100(self):
        assert spider_score("product", {"has_product": True, "has_customers": True, "has_revenue": True}, "growth") == 100


# ── Traction ──────────────────────────────────────────────────────────────────

class TestTractionScore:
    def test_no_traction_returns_10(self):
        assert spider_score("traction", {"has_product": False, "has_customers": False, "has_revenue": False}, "ideation") == 10

    def test_has_product_only_returns_30(self):
        assert spider_score("traction", {"has_product": True, "has_customers": False, "has_revenue": False}, "seed") == 30

    def test_has_customers_only_returns_55(self):
        assert spider_score("traction", {"has_product": True, "has_customers": True, "has_revenue": False}, "seed") == 55

    def test_has_revenue_only_returns_75(self):
        assert spider_score("traction", {"has_product": True, "has_customers": False, "has_revenue": True}, "growth") == 75

    def test_full_traction_returns_90(self):
        assert spider_score("traction", {"has_product": True, "has_customers": True, "has_revenue": True}, "growth") == 90


# ── Funding ───────────────────────────────────────────────────────────────────

class TestFundingScore:
    def test_not_fundraising_returns_50(self):
        assert spider_score("funding", {"funding_need": "none"}, "seed") == 50

    def test_vc_at_growth_returns_70(self):
        assert spider_score("funding", {"funding_need": "vc"}, "growth") == 70

    def test_vc_at_seed_returns_35(self):
        assert spider_score("funding", {"funding_need": "vc"}, "seed") == 35

    def test_angel_at_seed_returns_60(self):
        assert spider_score("funding", {"funding_need": "angel"}, "seed") == 60

    def test_grant_returns_55(self):
        assert spider_score("funding", {"funding_need": "grant"}, "seed") == 55


# ── Market ────────────────────────────────────────────────────────────────────

class TestMarketScore:
    def test_local_no_customers_returns_25(self):
        assert spider_score("market", {"market_type": "local", "has_customers": False, "has_revenue": False}, "seed") == 25

    def test_local_with_customers_returns_50(self):
        assert spider_score("market", {"market_type": "local", "has_customers": True, "has_revenue": False}, "seed") == 50

    def test_regional_returns_65(self):
        assert spider_score("market", {"market_type": "regional", "has_customers": False, "has_revenue": False}, "seed") == 65

    def test_international_no_revenue_returns_55(self):
        assert spider_score("market", {"market_type": "international", "has_customers": False, "has_revenue": False}, "seed") == 55

    def test_international_with_revenue_returns_90(self):
        assert spider_score("market", {"market_type": "international", "has_revenue": True}, "growth") == 90


# ── Branding ──────────────────────────────────────────────────────────────────

class TestBrandingScore:
    def test_no_brand_needs_content_returns_0(self):
        assert spider_score("branding", {"has_branding": False, "needs_content_production": True}, "seed") == 0

    def test_has_brand_no_content_need_returns_80(self):
        assert spider_score("branding", {"has_branding": True, "needs_content_production": False}, "seed") == 80

    def test_has_brand_at_growth_returns_100(self):
        score = spider_score("branding", {"has_branding": True, "needs_content_production": False}, "growth")
        assert score == 100


# ── compute_spider_scores ─────────────────────────────────────────────────────

class TestComputeSpiderScores:
    def test_returns_all_7_dimensions(self):
        diag = {
            "team_size": 2, "has_tech_cofounder": True, "has_business_cofounder": False,
            "legal_status": "incorporated_sarl", "has_startup_label": False,
            "has_product": True, "has_customers": False, "has_revenue": False,
            "funding_need": "none", "market_type": "local",
            "has_branding": True, "needs_content_production": False,
        }
        scores = compute_spider_scores(diag, "seed")
        assert set(scores.keys()) == {"Team", "Legal", "Product", "Traction", "Funding", "Market", "Branding"}
        for v in scores.values():
            assert 0 <= v <= 100

    def test_all_scores_are_integers(self):
        diag = {"team_size": 1, "legal_status": "not_incorporated", "has_product": False,
                "has_customers": False, "has_revenue": False, "funding_need": "none",
                "market_type": "local", "has_branding": False, "needs_content_production": True}
        scores = compute_spider_scores(diag, "ideation")
        for v in scores.values():
            assert isinstance(v, int)
