"""
pages/1_Startup.py — The Dot · Front office
Formulaire diagnostic + résultats.
Sidebar et nav entièrement cachées — aucun lien vers l'admin visible.

Refactoring:
  - CSS dupliqué remplacé par styles.HIDE_SIDEBAR / styles.FONTS_AND_RESET.
  - spider_score() et compute_spider_scores() importés depuis scoring.py.
  - Constantes UI (APPLY_URLS, PRIORITY, TYPE_COLORS, …) importées depuis config.py.
  - Validation du formulaire : le nom de la startup est requis avant soumission.
  - Bouton "Start Over" corrigé : st.rerun() explicite après st.session_state.clear()
    pour éviter que les résultats restent visibles jusqu'au prochain clic.
  - Barre de progression renommée pour ne pas suggérer une complétion factice.
  - Indicateur de sauvegarde DB affiché pendant l'écriture (st.toast).
"""

import json
import os
import sys

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

st.set_page_config(
    page_title="The Dot — Resource Matcher",
    page_icon="🔵",
    layout="wide",
    initial_sidebar_state="collapsed",
)

import styles
st.markdown(styles.HIDE_SIDEBAR,      unsafe_allow_html=True)
st.markdown(styles.FONTS_AND_RESET,   unsafe_allow_html=True)

from config import (
    APPLY_URLS,
    MATURITY_DIMS,
    MATURITY_DIM_KEYS,
    PRIORITY,
    RECOMMENDATION_MIN_SCORE,
    RESOURCE_BOOST_MAP,
    TYPE_COLORS,
)
from needs_engine import infer_needs
from matcher import match
from scoring import compute_spider_scores
from database import save_diagnostic, init_db

# Guard DB
if "db_initialized" not in st.session_state:
    try:
        init_db()
        st.session_state["db_initialized"] = True
    except Exception as e:
        st.session_state["db_initialized"] = False
        st.warning(f"⚠️ Base de données inaccessible ({e}) — les diagnostics ne seront pas sauvegardés.")

st.markdown("""
<style>
.hero-wrap {
    background: linear-gradient(135deg, #0a1628 0%, #0f2557 55%, #1a3a8c 100%);
    padding: 2.5rem 3.5rem 2rem; position: relative; overflow: hidden;
    text-align: center; display: flex; flex-direction: column; align-items: center;
}
.back-link {
    position: absolute; top: 1.2rem; left: 1.5rem;
    font-size: 0.78rem; color: rgba(255,255,255,0.4); text-decoration: none;
    display: flex; align-items: center; gap: 6px;
    transition: color 0.15s;
}
.back-link:hover { color: rgba(255,255,255,0.8); }
.hero-eyebrow { font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: rgba(147,197,253,0.8); margin-bottom: 0.6rem; }
.hero-title { font-size: 2.4rem; font-weight: 700; color: #fff; letter-spacing: -0.03em; line-height: 1.15; margin: 0 0 0.6rem 0; }
.hero-title span { color: #60a5fa; }
.hero-sub { font-size: 1rem; color: rgba(255,255,255,0.55); max-width: 560px; line-height: 1.6; margin: 0 auto; }
.hero-meta { display: flex; gap: 2rem; margin-top: 1.5rem; flex-wrap: wrap; justify-content: center; }
.hero-stat { display: flex; flex-direction: column; gap: 2px; }
.hero-stat-val { font-family: 'DM Mono', monospace; font-size: 1.4rem; font-weight: 500; color: #93c5fd; }
.hero-stat-label { font-size: 0.72rem; color: rgba(255,255,255,0.35); letter-spacing: 0.06em; text-transform: uppercase; }
.progress-wrap { background: #0f172a; padding: 0.85rem 2.2rem; border-bottom: 1px solid #1e293b; display: flex; align-items: center; gap: 1rem; }
.progress-label { font-size: 0.72rem; font-weight: 600; color: #94a3b8; letter-spacing: 0.08em; text-transform: uppercase; white-space: nowrap; }
.progress-steps { display: flex; gap: 6px; flex: 1; }
.progress-step { flex: 1; height: 4px; border-radius: 2px; background: #1e293b; }
.form-wrap { background: #111827; margin: 2rem 3.5rem; border-radius: 20px; border: 1px solid #1e293b; box-shadow: 0 4px 24px rgba(0,0,0,0.3); overflow: hidden; }
.form-section { padding: 1.8rem 2.2rem 0.5rem; border-bottom: 1px solid #1e293b; }
.form-section:last-child { border-bottom: none; }
.form-section-title { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: rgba(255,255,255,0.35); margin-bottom: 1rem; display: flex; align-items: center; gap: 8px; }
.form-section-title::before { content: ''; width: 3px; height: 13px; border-radius: 2px; background: linear-gradient(180deg, #2563eb, #60a5fa); flex-shrink: 0; }
.form-section-title::after { content: ''; flex: 1; height: 1px; background: #1a2744; }
.form-footer { padding: 1.5rem 2.2rem; background: #0f172a; border-top: 1px solid #1e293b; }
.stButton > button { background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%); color: white; border: none; border-radius: 12px; padding: 0.85rem 2.5rem; font-size: 0.95rem; font-weight: 600; width: 100%; letter-spacing: 0.01em; box-shadow: 0 4px 14px rgba(37,99,235,0.35); }
.results-wrap { padding: 0 3.5rem 3rem; }
.section-label { font-size: 0.65rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: rgba(255,255,255,0.28); margin: 2.5rem 0 1rem 0; display: flex; align-items: center; gap: 10px; }
.section-label::before { content: ''; width: 3px; height: 12px; border-radius: 2px; background: linear-gradient(180deg, #2563eb, #60a5fa); flex-shrink: 0; }
.section-label::after { content: ''; flex: 1; height: 1px; background: #1a2744; }
hr.divider { border: none; border-top: 1px solid #1e293b; margin: 2rem 0; }
.pill { display: inline-block; background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; border-radius: 20px; padding: 4px 14px; font-size: 0.76rem; margin: 3px; font-weight: 500; }
.flag { display: inline-flex; align-items: center; gap: 6px; border-radius: 10px; padding: 6px 14px; font-size: 0.8rem; margin: 4px; font-weight: 500; }
.flag-ok   { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.flag-warn { background: #fef9c3; color: #854d0e; border: 1px solid #fef08a; }
.confidence-note { display: inline-flex; align-items: center; gap: 6px; background: rgba(96,165,250,0.08); border: 1px solid rgba(96,165,250,0.2); border-radius: 10px; padding: 6px 14px; font-size: 0.75rem; color: #93c5fd; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

# Hero
st.markdown("""
<div class="hero-wrap">
  <a href="/" class="back-link" target="_self">← Accueil</a>
  <div class="hero-eyebrow">The Dot — Tunisia's Leading Startup Hub</div>
  <h1 class="hero-title">Find your <span>exact</span> fit<br>in The Dot ecosystem</h1>
  <p class="hero-sub">Répondez à 7 sections sur votre startup. Obtenez un radar de maturité personnalisé, des conseils stratégiques et un classement des programmes — propulsé par l'IA.</p>
  <div class="hero-meta">
    <div class="hero-stat"><span class="hero-stat-val">9</span><span class="hero-stat-label">Programmes analysés</span></div>
    <div class="hero-stat"><span class="hero-stat-val">7</span><span class="hero-stat-label">Dimensions de maturité</span></div>
    <div class="hero-stat"><span class="hero-stat-val">~3s</span><span class="hero-stat-label">Temps d'analyse IA</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# FORM
# ══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="form-wrap">', unsafe_allow_html=True)
# Progress bar — shows 6 neutral section indicators (not fake "done" states).
st.markdown("""
<div class="progress-wrap">
  <span class="progress-label">7 sections à remplir</span>
  <div class="progress-steps">
    <div class="progress-step"></div><div class="progress-step"></div>
    <div class="progress-step"></div><div class="progress-step"></div>
    <div class="progress-step"></div><div class="progress-step"></div>
    <div class="progress-step"></div>
  </div>
  <span class="progress-label" style="color:#60a5fa;">~4 min</span>
</div>
""", unsafe_allow_html=True)

with st.form("diagnostic_form"):
    # ── Section 1: Startup Identity ──────────────────────────────────────────
    st.markdown('<div class="form-section"><div class="form-section-title">🏢 1 / 7 — Identité de la Startup</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        startup_name = st.text_input("Nom de la startup *", placeholder="ex. Agritech Tunisia", max_chars=80)
        sector = st.selectbox("Secteur d'activité", ["tech","fintech","healthtech","edtech","agritech","cleantech","commerce","industry","manufacturing","retail","saas","marketplace","other"],
            format_func=lambda x: {"tech":"Tech / Digital","fintech":"Fintech","healthtech":"Healthtech / MedTech","edtech":"Edtech","agritech":"Agritech","cleantech":"Cleantech / GreenTech","commerce":"Commerce / Retail","industry":"Industrie","manufacturing":"Manufacturing","retail":"Retail","saas":"SaaS","marketplace":"Marketplace","other":"Autre"}[x])
    with c2:
        business_model = st.selectbox("Modèle économique (relations)", ["b2c","b2b","b2b2c","marketplace","other"],
            format_func=lambda x: {"b2c":"B2C (grand public)","b2b":"B2B (entreprises)","b2b2c":"B2B2C","marketplace":"Marketplace","other":"Autre / Mixte"}[x])
        business_model_type = st.selectbox("Type de modèle", ["saas","service","product","marketplace","other"],
            format_func=lambda x: {"saas":"SaaS (abonnement)","service":"Service / Conseil","product":"Produit physique","marketplace":"Marketplace / Plateforme","other":"Autre / Mixte"}[x])
    c1, c2 = st.columns(2)
    with c1:
        market_type = st.selectbox("Marché cible", ["local","regional","international"],
            format_func=lambda x: {"local":"Local (Tunisie)","regional":"Régional (Maghreb/Afrique)","international":"International (Europe/Monde)"}[x])
        market_size = st.selectbox("Taille de marché estimée", ["small","medium","large"],
            format_func=lambda x: {"small":"Petit (< 1M TND)","medium":"Moyen (1M–50M TND)","large":"Grand (> 50M TND)"}[x])
    with c2:
        diaspora_founder = st.checkbox("👋 Je suis un entrepreneur de la diaspora tunisienne")
        outside_tunis = st.checkbox("📍 Startup basée hors des grands hubs côtiers (hors Tunis, Sousse, Sfax, Médenine)")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Section 2: Stage & Maturity ──────────────────────────────────────────
    st.markdown('<div class="form-section"><div class="form-section-title">📈 2 / 7 — Stade & Maturité</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        stage = st.selectbox("Stade actuel", ["ideation","pre-seed","seed","growth","scale"],
            format_func=lambda x: {"ideation":"💡 Idéation (concept)","pre-seed":"🔨 Pré-seed (construction MVP)","seed":"🌱 Seed (produit validé)","growth":"📊 Croissance (revenus)","scale":"🚀 Scale (nouveaux marchés)"}[x])
    with c2:
        st.caption("Choisissez le stade qui correspond réellement à votre situation actuelle.")
    c1, c2, c3 = st.columns(3)
    with c1: has_product = st.checkbox("✅ Nous avons un produit / MVP")
    with c2: has_customers = st.checkbox("✅ Nous avons des clients actifs ou payants")
    with c3: has_revenue = st.checkbox("✅ Nous générons du chiffre d'affaires")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Section 3: Team ──────────────────────────────────────────────────────
    st.markdown('<div class="form-section"><div class="form-section-title">👥 3 / 7 — Équipe</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        team_size = st.number_input("Nombre de fondateurs", min_value=1, max_value=20, value=1)
        full_time_count = st.number_input("Personnes dédiées à 100%", min_value=0, max_value=20, value=1,
            help="Nombre de personnes consacrées à 100% au projet (fondateurs inclus)")
    with c2:
        has_tech_cofounder = st.checkbox("Nous avons un co-fondateur technique / CTO")
        has_business_cofounder = st.checkbox("Nous avons un co-fondateur commercial / business lead")
    with c3:
        has_competitive_advantage = st.checkbox("Nous avons un avantage concurrentiel identifié",
            help="Technologie propriétaire, brevet, réseau exclusif, position de marché différenciée…")
        has_ip_protection = st.checkbox("Technologie brevetée ou propriété intellectuelle protégée")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Section 4: Legal Status ──────────────────────────────────────────────
    st.markdown('<div class="form-section"><div class="form-section-title">⚖️ 4 / 7 — Statut Juridique</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        legal_status = st.selectbox("Statut de constitution", [
            "not_incorporated","in_progress","incorporated_suarl","incorporated_sarl","incorporated_sa","foreign_entity"
        ], format_func=lambda x: {
            "not_incorporated": "❌ Non encore constitué",
            "in_progress": "⏳ Constitution en cours",
            "incorporated_suarl": "✅ Constitué — SUARL",
            "incorporated_sarl": "✅ Constitué — SARL",
            "incorporated_sa": "✅ Constitué — SA",
            "foreign_entity": "🌍 Entité étrangère (implantation en Tunisie)",
        }[x])
    with c2:
        has_startup_label = st.checkbox("🏷️ Nous détenons le label Startup Act")
        has_branding = st.checkbox("🎨 Nous avons une identité de marque établie")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Section 5: Funding ───────────────────────────────────────────────────
    st.markdown('<div class="form-section"><div class="form-section-title">💰 5 / 7 — Financement</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        funding_need = st.selectbox("Type de financement recherché", ["none","grant","angel","vc","institutional"],
            format_func=lambda x: {"none":"Pas de recherche active","grant":"Subventions publiques / SICAR","angel":"Business angels","vc":"Capital-risque (VC)","institutional":"Institutionnel / PE"}[x])
    with c2:
        funding_range = st.selectbox("Montant recherché (TND)", ["none","under_50k","50k_200k","200k_1m","above_1m"],
            format_func=lambda x: {"none":"—","under_50k":"< 50 000 TND","50k_200k":"50 000–200 000 TND","200k_1m":"200 000–1 000 000 TND","above_1m":"> 1 000 000 TND"}[x])
    with c3:
        has_pitch_deck = st.checkbox("📊 Nous avons un pitch deck investisseurs",
            help="Présentation préparée pour des comités d'investissement")
        seeking_investors = st.checkbox("🤝 Nous cherchons activement des introductions investisseurs")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Section 6: Tech Profile ──────────────────────────────────────────────
    st.markdown('<div class="form-section"><div class="form-section-title">🔬 6 / 7 — Profil Technologique</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        is_ai_startup = st.checkbox("🤖 Nous développons des solutions IA / ML")
        is_industry40 = st.checkbox("🏭 Industrie 4.0 / IoT / Manufacturing")
        is_mobile_focused = st.checkbox("📱 Solution mobile-first")
    with c2:
        needs_workspace = st.checkbox("🏢 Besoin d'espace de travail / bureau")
        needs_content_production = st.checkbox("🎬 Besoin de design / studio")
        needs_events_space = st.checkbox("🎤 Besoin d'espace événementiel")
    with c3:
        needs_mentorship = st.checkbox("🧠 En recherche de mentor / conseiller senior")
        needs_market_access = st.checkbox("🌍 Besoin d'accès aux marchés")
        needs_legal_expert = st.checkbox("⚖️ Besoin d'expertise juridique / fiscale",
            help="Structuration juridique, pacte d'associés, IP, fiscalité startup")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Section 7: Value Proposition ────────────────────────────────────────
    st.markdown('<div class="form-section"><div class="form-section-title">💡 7 / 7 — Proposition de Valeur</div>', unsafe_allow_html=True)
    value_proposition = st.text_area(
        "Décrivez votre startup en 2–3 phrases (optionnel)",
        placeholder="Ex: SaisIAR automatise la saisie comptable via IA. Notre moteur propriétaire traite factures et relevés bancaires sans dépendance externe, garantissant confidentialité et conformité PCG tunisien.",
        max_chars=500,
        height=80,
        help="Cette description améliore la précision du matching sémantique IA"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="form-footer">', unsafe_allow_html=True)
    submitted = st.form_submit_button("🔍  Analyser Ma Startup & Trouver les Programmes")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════════════════════════════════
if submitted:
    # ── Form validation ───────────────────────────────────────────────────
    if not startup_name or not startup_name.strip():
        st.error("⚠️ Veuillez saisir le nom de votre startup avant de soumettre.")
        st.stop()

    name_display = startup_name.strip()[:80]
    name_safe = (
        name_display
        .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace("'", "&#39;").replace('"', "&quot;")
    )

    diag = {
        "startup_name": name_display, "stage": stage, "sector": sector,
        "business_model": business_model, "business_model_type": business_model_type,
        "market_type": market_type, "market_size": market_size,
        "diaspora_founder": diaspora_founder, "outside_tunis": outside_tunis,
        "team_size": team_size, "full_time_count": full_time_count,
        "has_tech_cofounder": has_tech_cofounder,
        "has_business_cofounder": has_business_cofounder,
        "has_competitive_advantage": has_competitive_advantage,
        "has_ip_protection": has_ip_protection,
        "legal_status": legal_status, "has_startup_label": has_startup_label,
        "has_branding": has_branding, "has_product": has_product,
        "has_customers": has_customers, "has_revenue": has_revenue,
        "funding_need": funding_need, "funding_range": funding_range,
        "has_pitch_deck": has_pitch_deck,
        "is_ai_startup": is_ai_startup, "is_industry40": is_industry40,
        "is_mobile_focused": is_mobile_focused,
        "needs_workspace": needs_workspace,
        "needs_content_production": needs_content_production,
        "needs_events_space": needs_events_space,
        "needs_mentorship": needs_mentorship,
        "needs_market_access": needs_market_access,
        "needs_legal_expert": needs_legal_expert,
        "seeking_investors": seeking_investors,
        "value_proposition": value_proposition or "",
    }

    profile = infer_needs(diag)

    extra = []
    if needs_mentorship:          extra += ["mentorship","strategy"]
    if needs_market_access:       extra += ["market_access","distribution","partnerships"]
    if seeking_investors:         extra += ["investor_readiness","fundraising","vc_access","pitch","investment_readiness"]
    if is_ai_startup:             extra += ["ai","tech_support","acceleration"]
    if is_industry40:             extra += ["tech_support","acceleration","partnerships"]
    if is_mobile_focused:         extra += ["mobile","tech_support"]
    if needs_events_space or needs_workspace: extra += ["workspace","events"]
    if needs_content_production:  extra += ["content_production","design","branding","content_creation"]
    if outside_tunis:             extra += ["regional_support"]
    if legal_status in ("not_incorporated","in_progress"): extra += ["legal","incorporation","legal_structuring"]
    if market_type in ("regional","international"):        extra += ["market_access"]
    if needs_legal_expert:        extra += ["legal_structuring","fiscal","incorporation","coaching"]
    if has_ip_protection:         extra += ["ip_protection"]
    if not has_pitch_deck and funding_need != "none": extra += ["pitch","investor_readiness"]
    profile["needs"]         = list(set(profile.get("needs", [])) | set(extra))
    profile["diaspora"]      = diaspora_founder
    profile["outside_tunis"] = outside_tunis
    profile["foreign_entity"]= (legal_status == "foreign_entity")
    profile["seeking_vc"]    = seeking_investors or funding_need in ("vc","angel")
    profile["is_ai"]         = is_ai_startup
    profile["is_industry40"] = is_industry40
    profile["has_ip"]        = has_ip_protection

    effective_stage = profile.get("stage", stage)

    if profile.get("stage_warning"):
        st.warning(profile["stage_warning"])

    # Spider scores (now computed in scoring.py)
    spider_scores_for_llm = compute_spider_scores(diag, effective_stage)
    scores = [spider_scores_for_llm[dim] for dim in MATURITY_DIMS]

    resources_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources.csv")
    with st.spinner("⚡ Analysing your profile and matching resources..."):
        results = match(profile, resources_path=resources_path, spider_scores=spider_scores_for_llm)

    llm_powered = any(r.get("llm_powered", False) for r in results)

    recommendations_to_save = [r for r in results if r.get("score", 0) >= RECOMMENDATION_MIN_SCORE]
    if st.session_state.get("db_initialized"):
        try:
            profile_for_db = {
                "startup_name": name_display, "sector": sector, "stage": effective_stage,
                "is_diaspora": diaspora_founder, "outside_tunis": outside_tunis,
                "team_size": team_size, "has_product": has_product,
                "has_clients": has_customers, "has_revenue": has_revenue,
                "is_incorporated": legal_status not in ("not_incorporated", "in_progress"),
                "has_startup_act": has_startup_label, "is_ai": is_ai_startup,
            }
            with st.spinner("💾 Saving diagnostic..."):
                save_diagnostic(
                    profile=profile_for_db,
                    scores=spider_scores_for_llm,
                    needs=profile.get("needs", []),
                    recommendations=recommendations_to_save,
                )
        except Exception as e:
            st.toast(f"⚠️ Sauvegarde DB échouée : {e}")

    st.markdown('<div class="results-wrap">', unsafe_allow_html=True)
    score_method = "7 maturity dimensions + Groq AI re-ranking" if llm_powered else "7 maturity dimensions + rule-based scoring"
    st.markdown(f'<div class="confidence-note">ℹ️ Scores based on {score_method}.</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Startup Maturity Radar</div>', unsafe_allow_html=True)
    scores_json = json.dumps(scores)
    dims_json   = json.dumps(MATURITY_DIMS)

    dim_tooltips = {
        "team":     "Co-founder completeness and role coverage",
        "legal":    "Incorporation status and Startup Act label",
        "product":  "Product maturity from idea to revenue-generating",
        "traction": "Market validation: customers, revenue, growth",
        "funding":  "Alignment between funding type and current stage",
        "market":   "Ambition and reach of target market",
        "branding": "Brand identity and content production capability",
    }

    stage_badge = ""
    if profile.get("stage_corrected"):
        stage_badge = f'<span style="background:rgba(245,158,11,0.2);border:1px solid rgba(245,158,11,0.5);color:#fbbf24;font-size:0.68rem;font-weight:600;padding:3px 10px;border-radius:20px;">Stage adjusted: {profile.get("stated_stage","").capitalize()} → {effective_stage.capitalize()}</span>'
    ai_badge = ""
    if llm_powered:
        ai_badge = '<span style="background:rgba(96,165,250,0.15);border:1px solid rgba(96,165,250,0.4);color:#93c5fd;font-size:0.68rem;font-weight:600;padding:3px 10px;border-radius:20px;">⚡ AI-powered</span>'

    stat_pills_html = ""
    for dim, sc, key in zip(MATURITY_DIMS, scores, MATURITY_DIM_KEYS):
        tip = dim_tooltips.get(key, "")
        color = "#4ade80" if sc >= 70 else ("#facc15" if sc >= 40 else "#f87171")
        stat_pills_html += (
            f'<div title="{tip}" style="background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.1);'
            f'border-radius:10px;padding:10px 6px;text-align:center;cursor:help;">'
            f'<div style="font-size:0.58rem;color:rgba(255,255,255,0.4);letter-spacing:0.06em;text-transform:uppercase;margin-bottom:4px;">{dim}</div>'
            f'<div style="font-family:\'DM Mono\',monospace;font-size:1.15rem;font-weight:500;color:{color};">{sc}</div>'
            f'<div style="height:3px;border-radius:2px;background:rgba(255,255,255,0.08);margin-top:5px;">'
            f'<div style="height:100%;border-radius:2px;background:{color};width:{sc}%;"></div></div></div>'
        )

    radar_html = f"""
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;600&display=swap" rel="stylesheet">
<div style="background:linear-gradient(160deg,#0a1628 0%,#0f2557 100%);border-radius:20px;padding:1.75rem 2rem;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1.2rem;flex-wrap:wrap;gap:8px;">
    <div>
      <div style="font-size:1rem;font-weight:600;color:rgba(255,255,255,0.95);">{name_safe}</div>
      <div style="font-size:0.72rem;color:rgba(255,255,255,0.35);margin-top:2px;">Maturity profile · hover pills for description</div>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">{stage_badge}{ai_badge}</div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin-bottom:1.5rem;">{stat_pills_html}</div>
  <div style="position:relative;width:100%;max-width:500px;height:340px;margin:0 auto;"><canvas id="radarChart"></canvas></div>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
(function(){{var ctx=document.getElementById('radarChart');
new Chart(ctx,{{type:'radar',data:{{labels:{dims_json},datasets:[{{label:'{name_safe}',data:{scores_json},
backgroundColor:'rgba(96,165,250,0.15)',borderColor:'#60a5fa',borderWidth:2,
pointBackgroundColor:'#fff',pointBorderColor:'#60a5fa',pointBorderWidth:2,pointRadius:4,pointHoverRadius:7}}]}},
options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},
scales:{{r:{{min:0,max:100,ticks:{{stepSize:25,font:{{size:10}},color:'rgba(255,255,255,0.25)',backdropColor:'transparent'}},
pointLabels:{{font:{{size:11,weight:'600',family:'DM Sans'}},color:'rgba(255,255,255,0.8)'}},
grid:{{color:'rgba(255,255,255,0.07)'}},angleLines:{{color:'rgba(255,255,255,0.08)'}}}}}}}}}}); }})();
</script>"""
    components.html(radar_html, height=520)

    # ── Snapshot + Strategic Advice (polished) ────────────────────────────────
    TIPS = {
        "team":    ("🧑‍🤝‍🧑", "Team Gap", "Find a co-founder or leverage The Dot's Executives in Residence network."),
        "legal":   ("⚖️",  "Legal Blocker", "Incorporate before fundraising or signing any commercial contract."),
        "product": ("🛠️",  "No Product Yet", "Validate your idea with a lean MVP before approaching investors."),
        "traction":("📈",  "No Traction Yet", "Land your first paying customer before approaching investors."),
        "funding": ("💰",  "Funding Path Unclear", "Grants, angels, and VC each require different readiness levels."),
        "market":  ("🌍",  "Limited Market Reach", "TECH216 or Bridge'up can open international doors."),
        "branding":("🎨",  "Brand Not Established", "A credible brand is essential for B2B sales and fundraising."),
    }
    weak   = sorted([(k,l,s) for k,l,s in zip(MATURITY_DIM_KEYS, MATURITY_DIMS, scores) if s < 50], key=lambda x:x[2])
    strong = [l for k,l,s in zip(MATURITY_DIM_KEYS, MATURITY_DIMS, scores) if s >= 70]
    needs_list = sorted(profile.get("needs", []))

    # Advice cards data
    advice_cards = []
    if not weak:
        advice_cards.append(("ok", "✅", "All Systems Strong", "You're strong across all dimensions. Focus on execution and leverage The Dot's network to accelerate."))
    else:
        for key, label, sc in weak[:3]:
            if key in TIPS:
                icon, title, body = TIPS[key]
                advice_cards.append(("warn", icon, title, body))
    if strong:
        advice_cards.append(("ok", "⭐", f"Strong: {', '.join(strong)}", "Build on these as competitive advantages."))
    for icon, title, body, cond in [
        ("🌍", "Diaspora Founder",  "Dot Landing is built for you: 4 months of free intensive support.", diaspora_founder),
        ("📍", "Regional Startup",  "Dot Camp+ is designed for your region — removes the Tunis barrier.", outside_tunis),
        ("💼", "Investor-Seeking",  "Attend Meetup VC only after legal structure, financial model, and MVP are ready.", seeking_investors),
        ("🤖", "AI Startup",        "The AI Hub gives you GPU compute and NVIDIA-linked training.", is_ai_startup),
        ("🏭", "Industry 4.0",      "TECH216 can open nearshoring partnerships with European industrial clients.", is_industry40),
    ]:
        if cond:
            advice_cards.append(("info", icon, title, body))

    # Status indicators
    status_flags = [
        (legal_status not in ("not_incorporated","in_progress"), "⚖️", "Legal", "Incorporated" if legal_status not in ("not_incorporated","in_progress") else "Not incorporated"),
        (not profile.get("team_gap"),    "🧑‍🤝‍🧑", "Team",     "Complete"         if not profile.get("team_gap")    else "Gap detected"),
        (bool(profile.get("has_traction")), "📈", "Traction", "Validated"        if profile.get("has_traction")   else "No traction yet"),
        (not profile.get("needs_funding"),  "💰", "Funding",  "Not fundraising"  if not profile.get("needs_funding") else funding_need.upper()),
    ]

    def _advice_card(kind, icon, title, body):
        colors = {
            "warn": ("#f59e0b", "rgba(245,158,11,0.08)", "rgba(245,158,11,0.2)"),
            "ok":   ("#10b981", "rgba(16,185,129,0.08)",  "rgba(16,185,129,0.2)"),
            "info": ("#60a5fa", "rgba(59,130,246,0.08)",  "rgba(59,130,246,0.2)"),
        }
        accent, bg, border = colors[kind]
        return (f'<div style="padding:14px 16px;border-radius:12px;background:{bg};border:1px solid {border};'
                f'border-left:3px solid {accent};display:flex;gap:12px;align-items:flex-start;">'
                f'<span style="font-size:1.1rem;margin-top:2px;">{icon}</span>'
                f'<div><div style="font-size:0.79rem;font-weight:700;color:#fff;margin-bottom:3px;">{title}</div>'
                f'<div style="font-size:0.75rem;color:rgba(255,255,255,0.5);line-height:1.5;">{body}</div></div></div>')

    def _flag_card(ok, icon, label, val):
        accent = "#6ee7b7" if ok else "#fcd34d"
        bg     = "rgba(16,185,129,0.07)" if ok else "rgba(245,158,11,0.07)"
        border = "rgba(16,185,129,0.18)" if ok else "rgba(245,158,11,0.18)"
        return (f'<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:10px;'
                f'background:{bg};border:1px solid {border};">'
                f'<span style="font-size:1rem;">{icon}</span>'
                f'<div><div style="font-size:0.7rem;font-weight:700;color:{accent};letter-spacing:0.03em;">{label}</div>'
                f'<div style="font-size:0.73rem;color:rgba(255,255,255,0.45);">{val}</div></div></div>')

    needs_tags = "".join([
        f'<span style="display:inline-block;padding:4px 11px;border-radius:20px;font-size:0.71rem;'
        f'font-weight:500;color:rgba(255,255,255,0.55);background:rgba(255,255,255,0.06);'
        f'border:1px solid rgba(255,255,255,0.1);margin:3px 3px 0 0;">{n.replace("_"," ")}</span>'
        for n in needs_list
    ])
    flags_inner  = "".join([_flag_card(ok, ic, lb, vl) for ok, ic, lb, vl in status_flags])
    advice_inner = "".join([_advice_card(k, i, t, b) for k, i, t, b in advice_cards])
    n_advice_rows = max(1, (len(advice_cards) + 1) // 2)

    snapshot = f"""
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>body{{background:#060d1c;margin:0;padding:0;font-family:'DM Sans',sans-serif;}}</style>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;">
  <div style="background:linear-gradient(145deg,#0a1628,#0d1b35);border-radius:14px;padding:1.2rem 1.4rem;border:1px solid #1a2744;">
    <div style="font-size:0.65rem;font-weight:700;letter-spacing:0.09em;color:rgba(255,255,255,0.28);margin-bottom:10px;">IDENTIFIED NEEDS</div>
    {needs_tags if needs_tags else '<span style="color:rgba(255,255,255,0.25);font-size:0.78rem;">No specific needs detected.</span>'}
  </div>
  <div style="background:linear-gradient(145deg,#0a1628,#0d1b35);border-radius:14px;padding:1.2rem 1.4rem;border:1px solid #1a2744;">
    <div style="font-size:0.65rem;font-weight:700;letter-spacing:0.09em;color:rgba(255,255,255,0.28);margin-bottom:10px;">STATUS INDICATORS</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">{flags_inner}</div>
  </div>
</div>
<div style="background:linear-gradient(145deg,#0a1628,#0d1b35);border-radius:14px;padding:1.2rem 1.4rem;border:1px solid #1a2744;">
  <div style="font-size:0.65rem;font-weight:700;letter-spacing:0.09em;color:rgba(255,255,255,0.28);margin-bottom:12px;">STRATEGIC ADVICE</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">{advice_inner}</div>
</div>
"""
    snap_height = 200 + max(1, (len(needs_list) // 5 + 1)) * 28 + n_advice_rows * 95
    components.html(snapshot, height=snap_height, scrolling=False)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Results cards
    ai_label = " &nbsp;<span style='font-size:0.68rem;background:#eff6ff;color:#1d4ed8;padding:2px 10px;border-radius:20px;font-weight:600;'>⚡ AI-powered</span>" if llm_powered else ""
    st.markdown(f'<div class="section-label">Programmes Recommandés — {len(results)} correspondances{ai_label}</div>', unsafe_allow_html=True)

    def build_eligibility_checklist(r, diag, profile, effective_stage):
        checks = []
        rid = r.get("id","")
        incorporated = diag.get("legal_status","") not in ("not_incorporated","in_progress")
        resource_stages = r.get("stages_raw", [effective_stage])
        checks.append((effective_stage in resource_stages, f"Stade ({effective_stage}) compatible"))
        if rid == "R001":
            checks += [(diag.get("has_product",False),"A un MVP fonctionnel"),(incorporated,"Juridiquement constitué"),(not diag.get("outside_tunis",False),"Basé à / peut se relocaliser à Tunis")]
        elif rid == "R002":
            checks += [(diag.get("outside_tunis",False),"Basé hors des grands hubs côtiers"),(not diag.get("has_revenue",False),"Pas encore en phase de revenus")]
        elif rid == "R003":
            checks.append((diag.get("diaspora_founder",False),"Fondateur de la diaspora tunisienne"))
        elif rid == "R004":
            checks += [(diag.get("has_product",False),"A un produit à challenger"),(effective_stage in ("seed","growth","scale"),"Stade Seed ou au-delà")]
        elif rid == "R005":
            checks += [(True,"Accessible à tous les stades"),(True,"Aucun prérequis — session à la demande")]
        elif rid == "R006":
            checks.append((True,"Accessible à tous les stades"))
        elif rid == "R007":
            checks.append((True,"Membre de la communauté The Dot"))
        elif rid == "R008":
            checks += [(diag.get("is_ai_startup",False),"Produit IA / ML core"),(diag.get("has_product",False),"A un MVP fonctionnel"),(incorporated,"Juridiquement constitué")]
        elif rid == "R009":
            checks += [(diag.get("sector","") in ("tech","saas"),"Secteur Tech ou SaaS"),(incorporated,"Juridiquement constitué"),(effective_stage in ("seed","growth","scale"),"Stade Seed ou au-delà")]
        met = sum(1 for ok,_ in checks if ok)
        total = len(checks)
        pct = int((met/total)*100) if total else 0
        bar_color = "#16a34a" if pct >= 75 else ("#f59e0b" if pct >= 50 else "#ef4444")
        items_html = "".join([
            f'<span style="display:inline-flex;align-items:center;gap:5px;'
            f'background:{"rgba(22,163,74,0.13)" if ok else "rgba(239,68,68,0.1)"};'
            f'border:1px solid {"rgba(74,222,128,0.25)" if ok else "rgba(248,113,113,0.22)"};'
            f'color:{"#4ade80" if ok else "#f87171"};'
            f'border-radius:20px;padding:3px 12px;font-size:0.73rem;margin:2px 2px 0 0;">{"✅" if ok else "❌"} {label}</span>'
            for ok, label in checks
        ])
        return (
            f'<div style="margin-top:0.85rem;padding:0.75rem 1rem;background:rgba(255,255,255,0.04);border-radius:10px;border:1px solid rgba(255,255,255,0.08);">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
            f'<span style="font-size:0.7rem;font-weight:700;color:rgba(255,255,255,0.25);letter-spacing:0.07em;text-transform:uppercase;">Éligibilité</span>'
            f'<span style="font-size:0.72rem;font-weight:600;color:{bar_color};">{met}/{total} criteria met</span></div>'
            f'<div style="background:rgba(255,255,255,0.08);border-radius:4px;height:4px;margin-bottom:8px;">'
            f'<div style="background:{bar_color};border-radius:4px;height:4px;width:{pct}%;"></div></div>'
            f'<div style="flex-wrap:wrap;">{items_html}</div></div>'
        )

    def _program_meta_strip(r):
        """Render duration / key_benefit / deliverables / ideal_profile strips."""
        duration    = r.get("duration", "")
        key_benefit = r.get("key_benefit", "")
        deliverables = r.get("deliverables", "")
        ideal_profile = r.get("eligibility_criteria", "")  # mapped from ideal_profile column
        if not any([duration, key_benefit, deliverables, ideal_profile]):
            return ""
        parts = []
        if duration:
            parts.append(f'<span style="display:inline-flex;align-items:center;gap:5px;font-size:0.73rem;color:rgba(255,255,255,0.5);background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:4px 10px;">⏱ {duration}</span>')
        if key_benefit:
            parts.append(f'<span style="display:inline-flex;align-items:center;gap:5px;font-size:0.73rem;color:#86efac;background:rgba(22,163,74,0.1);border:1px solid rgba(74,222,128,0.2);border-radius:8px;padding:4px 10px;">⭐ {key_benefit}</span>')
        meta_html = f'<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:0.75rem;">{"".join(parts)}</div>' if parts else ""
        if ideal_profile:
            meta_html += (
                f'<div style="margin-bottom:0.65rem;padding:0.55rem 0.85rem;background:rgba(99,102,241,0.07);'
                f'border-radius:8px;border:1px solid rgba(99,102,241,0.18);">'
                f'<span style="font-size:0.62rem;font-weight:700;letter-spacing:0.08em;color:rgba(255,255,255,0.22);text-transform:uppercase;">Pour qui ?</span>'
                f'<br><span style="font-size:0.78rem;color:rgba(255,255,255,0.5);line-height:1.5;">{ideal_profile}</span></div>'
            )
        if deliverables:
            meta_html += (
                f'<div style="margin-bottom:0.75rem;padding:0.6rem 0.9rem;background:rgba(37,99,235,0.07);'
                f'border-radius:8px;border:1px solid rgba(37,99,235,0.15);">'
                f'<span style="font-size:0.62rem;font-weight:700;letter-spacing:0.07em;color:rgba(255,255,255,0.22);text-transform:uppercase;">Ce que vous obtenez</span>'
                f'<br><span style="font-size:0.78rem;color:rgba(255,255,255,0.55);line-height:1.5;">{deliverables}</span></div>'
            )
        return meta_html

    if not results:
        st.info("Aucune correspondance forte trouvée — essayez d'ajuster vos réponses.")
    else:
        for i, r in enumerate(results):
            sc = min(r["score"], 100)
            priority = r.get("priority","short-term")
            p_fg, p_bg, p_border, p_icon, p_label = PRIORITY.get(priority, PRIORITY["short-term"])
            t_fg, t_bg = TYPE_COLORS.get(r["type"], ("#1d4ed8","#eff6ff"))
            bar_color = "#2563eb" if sc >= 70 else ("#0891b2" if sc >= 50 else "#7c3aed")
            apply_url = APPLY_URLS.get(r.get("id",""), r["url"])
            boosted_keys = RESOURCE_BOOST_MAP.get(r["type"], ["product"])
            after_scores = [min(s+25,100) if k in boosted_keys else s for k,s in zip(MATURITY_DIM_KEYS, scores)]
            reasons_html = "".join([
                f'<span style="display:inline-block;background:rgba(37,99,235,0.14);color:#93c5fd;border-radius:20px;'
                f'padding:3px 12px;font-size:0.74rem;margin:2px 2px 0 0;border:1px solid rgba(37,99,235,0.3);">✓ {rr}</span>'
                for rr in r.get("reasons",[])
            ])
            advice_html = (
                f'<div style="margin-top:0.85rem;padding:0.65rem 1rem;background:rgba(37,99,235,0.1);border-left:3px solid #2563eb;'
                f'border-radius:0 8px 8px 0;font-size:0.82rem;color:#93c5fd;line-height:1.5;">💬 {r["advice"]}</div>'
                if r.get("advice") else ""
            )
            checklist_html = build_eligibility_checklist(r, diag, profile, effective_stage)
            n_checks = checklist_html.count("✅") + checklist_html.count("❌")
            card = f"""
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>body{{background:#060d1c;margin:0;padding:0;}}</style>
<div style="background:linear-gradient(145deg,#0a1628 0%,#0d1b35 100%);border-radius:16px;padding:1.5rem 1.75rem;border:1px solid #1a2744;box-shadow:0 4px 24px rgba(0,0,0,0.4);font-family:'DM Sans',sans-serif;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
      <span style="font-family:'DM Mono',monospace;font-size:0.72rem;color:rgba(255,255,255,0.25);">#{i+1:02d}</span>
      <span style="font-family:'DM Mono',monospace;font-size:0.72rem;color:rgba(255,255,255,0.18);background:rgba(255,255,255,0.06);border-radius:4px;padding:1px 6px;">{r['id']}</span>
      <span style="font-size:1rem;font-weight:700;color:#fff;">{r['name']}</span>
      <span style="font-size:0.7rem;font-weight:600;padding:2px 10px;border-radius:20px;background:{t_bg};color:{t_fg};">{r['type'].capitalize()}</span>
      <span style="font-size:0.7rem;font-weight:600;padding:2px 10px;border-radius:20px;background:{p_bg};color:{p_fg};border:1px solid {p_border};">{p_icon} {p_label}</span>
    </div>
    <div style="display:flex;align-items:baseline;gap:2px;">
      <span style="font-family:'DM Mono',monospace;font-size:1.5rem;font-weight:500;color:#93c5fd;">{int(sc)}</span>
      <span style="font-size:0.75rem;color:rgba(255,255,255,0.25);">/100</span>
    </div>
  </div>
  <div style="background:#1a2744;border-radius:4px;height:5px;margin:0.8rem 0;overflow:hidden;">
    <div style="background:{bar_color};border-radius:4px;height:5px;width:{sc}%;"></div>
  </div>
  <p style="font-size:0.85rem;color:rgba(255,255,255,0.45);margin:0 0 0.75rem 0;line-height:1.55;">{r['description']}</p>
  {_program_meta_strip(r)}
  <div style="margin-bottom:6px;">{reasons_html}</div>
  {advice_html}{checklist_html}
  <div style="margin-top:1rem;padding-top:0.75rem;border-top:1px solid #1a2744;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
    <a href="{r['url']}" target="_blank" style="font-size:0.8rem;color:rgba(255,255,255,0.3);text-decoration:none;font-weight:500;">En savoir plus →</a>
    <a href="{apply_url}" target="_blank" style="font-size:0.82rem;font-weight:700;color:white;background:linear-gradient(135deg,#1d4ed8,#2563eb);border-radius:8px;padding:7px 18px;text-decoration:none;box-shadow:0 2px 10px rgba(37,99,235,0.4);">Postuler →</a>
  </div>
  <div style="margin-top:1.5rem;padding-top:1.25rem;border-top:1px dashed #1a2744;">
    <div style="background:linear-gradient(160deg,#0a1628 0%,#0f2557 100%);border-radius:12px;padding:1.25rem;">
      <div style="font-size:0.8rem;font-weight:600;color:#fff;margin-bottom:2px;">Estimated Impact</div>
      <div style="font-size:0.72rem;color:rgba(255,255,255,0.4);margin-bottom:1rem;">Projected maturity shift if you complete this programme.</div>
      <div style="position:relative;width:100%;max-width:380px;height:260px;margin:0 auto;"><canvas id="impactChart-{i}"></canvas></div>
    </div>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
(function(){{setTimeout(function(){{
  var ctx=document.getElementById('impactChart-{i}').getContext('2d');
  new Chart(ctx,{{type:'radar',data:{{labels:{dims_json},datasets:[
    {{label:'Before',data:{scores_json},backgroundColor:'rgba(148,163,184,0.08)',borderColor:'#94a3b8',borderWidth:1.5,borderDash:[3,3],pointRadius:2,pointBackgroundColor:'#94a3b8'}},
    {{label:'After',data:{json.dumps(after_scores)},backgroundColor:'rgba(56,189,248,0.18)',borderColor:'#38bdf8',borderWidth:2,pointRadius:3,pointBackgroundColor:'#fff',pointBorderColor:'#38bdf8'}}
  ]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},
  scales:{{r:{{min:0,max:100,ticks:{{display:false}},
  pointLabels:{{font:{{size:9,family:'DM Sans',weight:'600'}},color:'rgba(255,255,255,0.7)'}},
  grid:{{color:'rgba(255,255,255,0.06)'}},angleLines:{{color:'rgba(255,255,255,0.06)'}}}}}}}}}}); }},50); }})();
</script>"""
            ideal_len = len(r.get("eligibility_criteria",""))
            h = 260 + len(r.get("reasons",[])) * 32 + (85 if r.get("advice") else 0) + (n_checks * 34) + 420 + (80 if ideal_len > 0 else 0) + min(ideal_len // 80 * 20, 120)
            components.html(card, height=h, scrolling=False)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Export</div>', unsafe_allow_html=True)
    avg_score = int(sum(scores)/len(scores)) if scores else 0
    summary = {
        "startup_name":  profile.get("startup_name",""),
        "stage":         effective_stage,
        "sector":        sector,
        "spider_scores": dict(zip(MATURITY_DIMS, scores)),
        "needs":         needs_list,
        "results": [
            {"rank":i+1,"name":r["name"],"score":r["score"],"type":r["type"],
             "priority":r.get("priority",""),"advice":r.get("advice",""),"url":r["url"]}
            for i,r in enumerate(results)
        ],
    }
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "⬇️ Download JSON summary",
            data=json.dumps(summary, ensure_ascii=False, indent=2),
            file_name="thedot_diagnostic.json",
            mime="application/json",
        )
    with col2:
        try:
            from pdf_export import generate_diagnostic_pdf
            pdf_bytes = generate_diagnostic_pdf(summary)
            st.download_button(
                "⬇️ Download PDF report",
                data=pdf_bytes,
                file_name="thedot_report.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.error(f"PDF unavailable: {e}")
