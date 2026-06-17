"""
app.py — The Dot Resource Matcher
Diagnostic-driven startup resource recommendation system with impact simulation.
"""

import streamlit as st
import streamlit.components.v1 as components
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

from needs_engine import infer_needs
from matcher import match

st.set_page_config(
    page_title="The Dot — Resource Matcher",
    page_icon="🔵",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background: #0a0f1a;
}
.block-container { padding: 0 !important; max-width: 100% !important; }

/* ── Hero ── */
.hero-wrap {
    background: linear-gradient(135deg, #0a1628 0%, #0f2557 55%, #1a3a8c 100%);
    padding: 3rem 3.5rem 2.5rem;
    position: relative; overflow: hidden;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
}
.hero-wrap::before {
    content: '';
    position: absolute; top: -80px; right: -80px;
    width: 340px; height: 340px; border-radius: 50%;
    background: radial-gradient(circle, rgba(37,99,235,0.25) 0%, transparent 70%);
    pointer-events: none;
}
.hero-eyebrow {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em;
    text-transform: uppercase; color: rgba(147,197,253,0.8);
    margin-bottom: 0.6rem; text-align: center;
}
.hero-title {
    font-size: 2.4rem; font-weight: 700; color: #fff;
    letter-spacing: -0.03em; line-height: 1.15; margin: 0 0 0.6rem 0;
}
.hero-title span { color: #60a5fa; }
.hero-sub {
    font-size: 1rem; color: rgba(255,255,255,0.55);
    max-width: 560px; line-height: 1.6; margin: 0 auto;
}
.hero-meta {
    display: flex; gap: 2rem; margin-top: 1.8rem; flex-wrap: wrap;
    justify-content: center;
}
.hero-stat {
    display: flex; flex-direction: column; gap: 2px;
}
.hero-stat-val {
    font-family: 'DM Mono', monospace;
    font-size: 1.4rem; font-weight: 500; color: #93c5fd;
}
.hero-stat-label {
    font-size: 0.72rem; color: rgba(255,255,255,0.35);
    letter-spacing: 0.06em; text-transform: uppercase;
}

/* ── Form ── */
.form-wrap {
    background: #111827;
    margin: 2rem 3.5rem;
    border-radius: 20px;
    border: 1px solid #1e293b;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3);
    overflow: hidden;
}
.form-section {
    padding: 1.8rem 2.2rem 0.5rem;
    border-bottom: 1px solid #1e293b;
}
.form-section:last-child { border-bottom: none; }
.form-section-title {
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #94a3b8; margin-bottom: 1rem;
    display: flex; align-items: center; gap: 8px;
}
.form-section-title::after {
    content: ''; flex: 1; height: 1px; background: #1e293b;
}
.form-footer {
    padding: 1.5rem 2.2rem;
    background: #0f172a;
    border-top: 1px solid #1e293b;
}

/* ── Submit button ── */
.stButton > button {
    background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%);
    color: white; border: none; border-radius: 12px;
    padding: 0.85rem 2.5rem; font-size: 0.95rem; font-weight: 600;
    width: 100%; letter-spacing: 0.01em;
    box-shadow: 0 4px 14px rgba(37,99,235,0.35);
    transition: all 0.2s;
}
.stButton > button:hover {
    box-shadow: 0 6px 20px rgba(37,99,235,0.45);
    transform: translateY(-1px);
}

/* ── Results ── */
.results-wrap { padding: 0 3.5rem 3rem; }

.section-label {
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: #94a3b8;
    margin: 2.5rem 0 1rem 0;
    display: flex; align-items: center; gap: 10px;
}
.section-label::after { content: ''; flex: 1; height: 1px; background: #e2e8f0; }

hr.divider { border: none; border-top: 1px solid #e2e8f0; margin: 2rem 0; }

/* ── Needs pills ── */
.pill {
    display: inline-block; background: #eff6ff; color: #1d4ed8;
    border: 1px solid #bfdbfe; border-radius: 20px;
    padding: 4px 14px; font-size: 0.76rem; margin: 3px; font-weight: 500;
}

/* ── Flag badges ── */
.flag { display: inline-flex; align-items: center; gap: 6px;
        border-radius: 10px; padding: 6px 14px;
        font-size: 0.8rem; margin: 4px; font-weight: 500; }
.flag-ok { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.flag-warn { background: #fef9c3; color: #854d0e; border: 1px solid #fef08a; }

/* ── Print button ── */
.print-btn {
    display: inline-flex; align-items: center; gap: 8px;
    background: white; color: #374151; border: 1.5px solid #d1d5db;
    border-radius: 10px; padding: 0.6rem 1.2rem;
    font-size: 0.83rem; font-weight: 600; cursor: pointer;
    text-decoration: none; transition: all 0.15s;
}
.print-btn:hover { background: #f9fafb; border-color: #9ca3af; }

/* Print styles */
@media print {
    .hero-wrap, .form-wrap, .stButton, .stDownloadButton { display: none !important; }
    .results-wrap { padding: 0 !important; }
    body { background: white !important; }
}
</style>
""", unsafe_allow_html=True)

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-wrap">
  <div class="hero-eyebrow">The Dot — Tunisia's Leading Startup Hub</div>
  <h1 class="hero-title">Find your <span>exact</span> fit<br>in The Dot ecosystem</h1>
  <p class="hero-sub">Answer 6 sections about your startup. Get a personalised radar, strategic advice, and ranked program recommendations — powered by AI.</p>
  <div class="hero-meta">
    <div class="hero-stat">
      <span class="hero-stat-val">15</span>
      <span class="hero-stat-label">Programs analysed</span>
    </div>
    <div class="hero-stat">
      <span class="hero-stat-val">7</span>
      <span class="hero-stat-label">Maturity dimensions</span>
    </div>
    <div class="hero-stat">
      <span class="hero-stat-val">~3s</span>
      <span class="hero-stat-label">AI matching time</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# FORM
# ══════════════════════════════════════════════════════════════════════════

st.markdown('<div class="form-wrap">', unsafe_allow_html=True)

with st.form("diagnostic_form"):

    # ── 1. Identity ────────────────────────────────────────────────────────
    st.markdown('<div class="form-section"><div class="form-section-title">🏢 Startup Identity</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        startup_name   = st.text_input("Startup name", placeholder="e.g. Agritech Tunisia")
        sector         = st.selectbox("Sector", ["tech","fintech","healthtech","edtech","agritech","cleantech","commerce","industry","manufacturing","retail","saas","marketplace","other"])
    with c2:
        business_model = st.selectbox("Business model", ["b2c","b2b","b2b2c","marketplace","other"])
        market_type    = st.selectbox("Target market", ["local","regional","international"])
    c1, c2 = st.columns(2)
    with c1:
        diaspora_founder = st.checkbox("👋 I am a Tunisian diaspora entrepreneur")
    with c2:
        outside_tunis    = st.checkbox("📍 My startup is based outside of Tunis")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 2. Stage ──────────────────────────────────────────────────────────
    st.markdown('<div class="form-section"><div class="form-section-title">📈 Stage & Maturity</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        stage = st.selectbox("Current stage", ["ideation","pre-seed","seed","growth","scale"],
            help="ideation=idea only | pre-seed=building MVP | seed=have product | growth=revenue+scaling | scale=new markets")
    with c2:
        st.caption("💡 ideation → 🔨 pre-seed → 🌱 seed → 📊 growth → 🚀 scale")
    c1, c2, c3 = st.columns(3)
    with c1: has_product   = st.checkbox("We have a product / MVP")
    with c2: has_customers = st.checkbox("We have paying / active customers")
    with c3: has_revenue   = st.checkbox("We are generating revenue")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 3. Team ───────────────────────────────────────────────────────────
    st.markdown('<div class="form-section"><div class="form-section-title">👥 Team</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: team_size             = st.number_input("Number of founders", min_value=1, max_value=10, value=1)
    with c2: has_tech_cofounder    = st.checkbox("We have a technical co-founder / CTO")
    with c3: has_business_cofounder= st.checkbox("We have a business co-founder / commercial lead")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 4. Legal ──────────────────────────────────────────────────────────
    st.markdown('<div class="form-section"><div class="form-section-title">⚖️ Legal Status</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        legal_status = st.selectbox("Incorporation status", [
            "not_incorporated","in_progress","incorporated_suarl","incorporated_sarl","incorporated_sa","foreign_entity"
        ], format_func=lambda x: {
            "not_incorporated":  "❌ Not yet incorporated",
            "in_progress":       "⏳ Incorporation in progress",
            "incorporated_suarl":"✅ Incorporated — SUARL",
            "incorporated_sarl": "✅ Incorporated — SARL",
            "incorporated_sa":   "✅ Incorporated — SA",
            "foreign_entity":    "🌍 Foreign entity entering Tunisia",
        }[x])
    with c2:
        has_startup_label = st.checkbox("We hold the Startup Act label")
        has_branding      = st.checkbox("We have an established brand identity")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 5. Funding ────────────────────────────────────────────────────────
    st.markdown('<div class="form-section"><div class="form-section-title">💰 Funding</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        funding_need = st.selectbox("Funding type sought", ["none","grant","angel","vc","institutional"],
            format_func=lambda x: {"none":"Not currently fundraising","grant":"Public grants / SICAR","angel":"Business angels","vc":"Venture capital","institutional":"Institutional / PE funds"}[x])
    with c2:
        funding_range = st.selectbox("Amount needed (TND)", ["none","under_50k","50k_200k","200k_1m","above_1m"],
            format_func=lambda x: {"none":"—","under_50k":"< 50,000 TND","50k_200k":"50,000–200,000 TND","200k_1m":"200,000–1,000,000 TND","above_1m":"> 1,000,000 TND"}[x])
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 6. Additional ─────────────────────────────────────────────────────
    st.markdown('<div class="form-section"><div class="form-section-title">🎯 Tech Profile & Additional Needs</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        is_ai_startup      = st.checkbox("We build AI / ML solutions")
        is_industry40      = st.checkbox("Industry 4.0 / IoT / Manufacturing")
        is_mobile_focused  = st.checkbox("Mobile-first solution")
    with c2:
        needs_workspace         = st.checkbox("Need workspace / office")
        needs_content_production= st.checkbox("Need design / studio tools")
        needs_events_space      = st.checkbox("Need event / conference space")
    with c3:
        needs_mentorship   = st.checkbox("Seeking mentor / senior advisor")
        needs_market_access= st.checkbox("Need help accessing markets")
        seeking_investors  = st.checkbox("Actively seeking investor introductions")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Submit ─────────────────────────────────────────────────────────────
    st.markdown('<div class="form-footer">', unsafe_allow_html=True)
    submitted = st.form_submit_button("🔍  Analyse My Startup & Find Resources")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # close form-wrap

# ══════════════════════════════════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════════════════════════════════

if submitted:

    # Validate name
    name_display = startup_name.strip() if startup_name and startup_name.strip() else "Your Startup"

    diag = {
        "startup_name": name_display, "stage": stage, "sector": sector,
        "business_model": business_model, "market_type": market_type,
        "diaspora_founder": diaspora_founder, "outside_tunis": outside_tunis,
        "team_size": team_size, "has_tech_cofounder": has_tech_cofounder,
        "has_business_cofounder": has_business_cofounder,
        "legal_status": legal_status, "has_startup_label": has_startup_label,
        "has_branding": has_branding, "has_product": has_product,
        "has_customers": has_customers, "has_revenue": has_revenue,
        "funding_need": funding_need, "funding_range": funding_range,
        "is_ai_startup": is_ai_startup, "is_industry40": is_industry40,
        "is_mobile_focused": is_mobile_focused,
        "needs_workspace": needs_workspace,
        "needs_content_production": needs_content_production,
        "needs_events_space": needs_events_space,
        "needs_mentorship": needs_mentorship,
        "needs_market_access": needs_market_access,
        "seeking_investors": seeking_investors,
    }

    profile = infer_needs(diag)

    # Augment needs
    extra = []
    if needs_mentorship:         extra += ["mentorship","strategy"]
    if needs_market_access:      extra += ["market_access","distribution","partnerships"]
    if seeking_investors:        extra += ["investor_readiness","fundraising","vc_access","pitch","investment_readiness"]
    if is_ai_startup:            extra += ["ai","tech_support","acceleration"]
    if is_industry40:            extra += ["tech_support","acceleration","partnerships"]
    if is_mobile_focused:        extra += ["mobile","tech_support"]
    if needs_events_space or needs_workspace: extra += ["workspace","events"]
    if needs_content_production: extra += ["content_production","design","branding","content_creation"]
    if outside_tunis:            extra += ["regional_support"]
    if legal_status in ("not_incorporated","in_progress"): extra += ["legal","incorporation","legal_structuring"]
    if market_type in ("regional","international"):        extra += ["market_access"]
    profile["needs"] = list(set(profile.get("needs", [])) | set(extra))

    profile["diaspora"]       = diaspora_founder
    profile["outside_tunis"]  = outside_tunis
    profile["foreign_entity"] = (legal_status == "foreign_entity")
    profile["seeking_vc"]     = seeking_investors or funding_need in ("vc","angel")
    profile["is_ai"]          = is_ai_startup
    profile["is_industry40"]  = is_industry40

    effective_stage = profile.get("stage", stage)

    # ── Stage warning ──────────────────────────────────────────────────────
    if profile.get("stage_warning"):
        st.warning(profile["stage_warning"])

    # ── Spider scores (computed before LLM call) ───────────────────────────
    def spider_score(dim):
        if dim == "team":
            if team_size >= 3 and has_tech_cofounder and has_business_cofounder: return 100
            if team_size >= 2 and (has_tech_cofounder or has_business_cofounder): return 65
            if team_size >= 2: return 40
            return 20
        if dim == "legal":
            base = {"not_incorporated":5,"in_progress":30,"incorporated_suarl":70,
                    "incorporated_sarl":75,"incorporated_sa":85,"foreign_entity":60}.get(legal_status,20)
            return min(base + (15 if has_startup_label else 0), 100)
        if dim == "product":
            if has_revenue: return 100
            if has_customers: return 80
            if has_product: return 55
            if effective_stage == "pre-seed": return 30
            return 10
        if dim == "traction":
            if has_revenue and has_customers: return 90
            if has_revenue: return 75
            if has_customers: return 55
            if has_product: return 30
            return 10
        if dim == "funding":
            if funding_need == "none": return 50
            if funding_need == "vc"    and effective_stage in ("growth","scale"):   return 70
            if funding_need == "angel" and effective_stage in ("seed","pre-seed"):  return 60
            if funding_need == "grant": return 55
            return 35
        if dim == "market":
            if market_type == "international" and has_revenue: return 90
            if market_type == "regional": return 65
            if market_type == "international": return 55
            if has_customers: return 50
            return 25
        if dim == "branding":
            sc = 0
            if has_branding: sc += 60
            if not needs_content_production: sc += 20
            if effective_stage in ("growth","scale"): sc += 20
            return min(sc, 100)
        return 0

    dims     = ["Team","Legal","Product","Traction","Funding","Market","Branding"]
    dim_keys = ["team","legal","product","traction","funding","market","branding"]
    scores   = [spider_score(k) for k in dim_keys]
    spider_scores_for_llm = dict(zip(dims, scores))

    # ── Match ──────────────────────────────────────────────────────────────
    resources_path = os.path.join(os.path.dirname(__file__), "resources.csv")
    with st.spinner("⚡ Analysing your profile and matching resources..."):
        results = match(profile, resources_path=resources_path, spider_scores=spider_scores_for_llm)

    llm_powered = any(r.get("llm_powered", False) for r in results)

    st.markdown('<div class="results-wrap">', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # RADAR CARD
    # ══════════════════════════════════════════════════════════════════════════

    st.markdown('<div class="section-label">Startup Maturity Radar</div>', unsafe_allow_html=True)

    name_safe   = name_display.replace("'","").replace('"','')
    scores_json = json.dumps(scores)
    dims_json   = json.dumps(dims)

    dim_tooltips = {
        "team":    "Co-founder completeness and role coverage across tech and business",
        "legal":   "Incorporation status and Startup Act label — prerequisite for fundraising",
        "product": "Product maturity from idea to revenue-generating",
        "traction":"Market validation: customers, revenue, and growth signals",
        "funding": "Alignment between funding type sought and current stage",
        "market":  "Ambition and reach of target market relative to traction",
        "branding":"Brand identity establishment and content production capability",
    }

    stage_badge = ""
    if profile.get("stage_corrected"):
        stage_badge = f"""<span style="background:rgba(245,158,11,0.2);border:1px solid rgba(245,158,11,0.5);
            color:#fbbf24;font-size:0.68rem;font-weight:600;padding:3px 10px;border-radius:20px;">
            Stage adjusted: {profile.get('stated_stage','').capitalize()} → {effective_stage.capitalize()}</span>"""

    ai_badge = ""
    if llm_powered:
        ai_badge = """<span style="background:rgba(96,165,250,0.15);border:1px solid rgba(96,165,250,0.4);
            color:#93c5fd;font-size:0.68rem;font-weight:600;padding:3px 10px;border-radius:20px;">⚡ AI-powered</span>"""

    # Build stat pills
    stat_pills_html = ""
    for dim, sc, key in zip(dims, scores, dim_keys):
        tip = dim_tooltips.get(key, "")
        color = "#4ade80" if sc >= 70 else ("#facc15" if sc >= 40 else "#f87171")
        stat_pills_html += f"""
        <div title="{tip}" style="background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.1);
            border-radius:10px;padding:10px 6px;text-align:center;cursor:help;">
          <div style="font-size:0.58rem;color:rgba(255,255,255,0.4);letter-spacing:0.06em;
              text-transform:uppercase;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{dim}</div>
          <div style="font-family:'DM Mono',monospace;font-size:1.15rem;font-weight:500;color:{color};">{sc}</div>
          <div style="height:3px;border-radius:2px;background:rgba(255,255,255,0.08);margin-top:5px;">
            <div style="height:100%;border-radius:2px;background:{color};width:{sc}%;"></div>
          </div>
        </div>"""

    radar_html = f"""
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;600&display=swap" rel="stylesheet">
<div style="background:linear-gradient(160deg,#0a1628 0%,#0f2557 100%);border-radius:20px;
    padding:1.75rem 2rem;position:relative;overflow:hidden;
    box-shadow:0 8px 40px rgba(10,22,40,0.3);">
  <div style="position:absolute;top:-60px;right:-60px;width:280px;height:280px;border-radius:50%;
      background:radial-gradient(circle,rgba(37,99,235,0.18) 0%,transparent 70%);pointer-events:none;"></div>

  <div style="display:flex;justify-content:space-between;align-items:flex-start;
      margin-bottom:1.2rem;flex-wrap:wrap;gap:8px;position:relative;z-index:2;">
    <div>
      <div style="font-size:1rem;font-weight:600;color:rgba(255,255,255,0.95);">{name_safe}</div>
      <div style="font-size:0.72rem;color:rgba(255,255,255,0.35);margin-top:2px;">
        Maturity profile across 7 dimensions · hover pills for description
      </div>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
      {stage_badge}{ai_badge}
    </div>
  </div>

  <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin-bottom:1.5rem;position:relative;z-index:2;">
    {stat_pills_html}
  </div>

  <div style="position:relative;width:100%;max-width:500px;height:340px;margin:0 auto;z-index:2;">
    <canvas id="radarChart"></canvas>
  </div>

  <div style="display:flex;justify-content:center;gap:20px;margin-top:1rem;position:relative;z-index:2;">
    <span style="display:flex;align-items:center;gap:6px;font-size:0.7rem;color:rgba(255,255,255,0.3);">
      <span style="width:10px;height:10px;border-radius:2px;background:rgba(96,165,250,0.15);
          border:1px solid #60a5fa;display:inline-block;"></span>Score area</span>
    <span style="display:flex;align-items:center;gap:6px;font-size:0.7rem;color:rgba(255,255,255,0.3);">
      <span style="width:10px;height:10px;border-radius:2px;background:#60a5fa;display:inline-block;"></span>
      {name_safe}</span>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
(function(){{
  var ctx = document.getElementById('radarChart');
  new Chart(ctx,{{
    type:'radar',
    data:{{
      labels:{dims_json},
      datasets:[{{
        label:'{name_safe}',
        data:{scores_json},
        backgroundColor:'rgba(96,165,250,0.15)',
        borderColor:'#60a5fa',
        borderWidth:2,
        pointBackgroundColor:'#fff',
        pointBorderColor:'#60a5fa',
        pointBorderWidth:2,
        pointRadius:4,
        pointHoverRadius:7
      }}]
    }},
    options:{{
      responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{display:false}}}},
      scales:{{r:{{
        min:0,max:100,
        ticks:{{stepSize:25,font:{{size:10}},color:'rgba(255,255,255,0.25)',backdropColor:'transparent'}},
        pointLabels:{{font:{{size:11,weight:'600',family:'DM Sans'}},color:'rgba(255,255,255,0.8)'}},
        grid:{{color:'rgba(255,255,255,0.07)'}},
        angleLines:{{color:'rgba(255,255,255,0.08)'}}
      }}}}
    }}
  }});
}})();
</script>
"""
    components.html(radar_html, height=580)

    # ── Strategic Advice ───────────────────────────────────────────────────
    st.markdown('<div class="section-label">Strategic Advice</div>', unsafe_allow_html=True)

    TIPS = {
        "team":    ("⚠️ Incomplete team","Find a co-founder or leverage The Dot's Executives in Residence network to fill gaps. A solo founder is the #1 red flag for early-stage investors."),
        "legal":   ("⚠️ Legal gap — blocker","Incorporate before fundraising or signing any commercial contract. Dot Expert Legal guides you through SUARL/SARL/SA and Startup Act labeling — free."),
        "product": ("⚠️ No product yet","Validate your idea with a lean MVP before raising. Dot Executives in Residence (Strategy & Tech) can help you prioritize what to build first."),
        "traction":("⚠️ No traction yet","Land your first paying customer before approaching investors. Evidence of demand is the single most powerful signal at early stage."),
        "funding": ("ℹ️ Funding path unclear","Grants, angels, and VC each require different readiness. Dot Expert Finance helps map the right path. Meetup VC connects you directly with investors."),
        "market":  ("⚠️ Market reach limited","If targeting international: Dot's Soft Landing supports foreign setup. If local: nail go-to-market first — Dot Expert GTM can help."),
        "branding":("⚠️ Brand not established","A credible brand is essential for B2B sales and fundraising. Dot Services Studio gives you free access to Adobe Suite, Figma, and a podcast studio."),
    }

    weak  = sorted([(k,l,s) for k,l,s in zip(dim_keys,dims,scores) if s < 50], key=lambda x:x[2])
    strong= [l for k,l,s in zip(dim_keys,dims,scores) if s >= 70]

    if not weak:
        st.success("✅ Strong across all dimensions. Focus on execution and leverage The Dot's network to accelerate.")
    else:
        for key, label, sc in weak[:3]:
            if key in TIPS:
                title, body = TIPS[key]
                st.warning(f"**{title}** — {body}")

    if strong:
        st.success(f"✅ Strong areas: **{', '.join(strong)}** — build on these as competitive advantages.")

    contextual = []
    if diaspora_founder: contextual.append("🌍 **Diaspora founder** — Dot Landing is built for you: 4 months of free intensive support to establish your business in Tunisia.")
    if outside_tunis:    contextual.append("📍 **Regional startup** — Dot Camp+ removes the Tunis barrier. Same quality as Dot Camp, designed for founders outside the capital.")
    if seeking_investors:contextual.append("💼 **Investor-seeking** — Attend Meetup VC only after you have legal structure, financial model, and at least an MVP. First impressions with investors are permanent.")
    if is_ai_startup:    contextual.append("🤖 **AI startup** — The DTC AI Hub gives you sector-specific mentorship and direct connections to public/private organizations seeking AI solutions.")
    if is_industry40:    contextual.append("🏭 **Industry 4.0** — The DTC I4.0 Hub provides industry partnerships that can shape your product roadmap toward real deployment.")

    for msg in contextual:
        st.info(msg)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Needs Profile ──────────────────────────────────────────────────────
    st.markdown('<div class="section-label">Identified Needs Profile</div>', unsafe_allow_html=True)

    needs_list = sorted(profile.get("needs",[]))
    if needs_list:
        pills = "".join([f'<span class="pill">{n.replace("_"," ")}</span>' for n in needs_list])
        st.markdown(f"<div style='margin-bottom:1rem;'>{pills}</div>", unsafe_allow_html=True)

    flags_html = ""
    for ok, label, yes_t, no_t in [
        (legal_status not in ("not_incorporated","in_progress"), "Legal", "Incorporated", "Not incorporated"),
        (not profile.get("team_gap"),    "Team",     "Complete",        "Gap detected"),
        (profile.get("has_traction"),    "Traction", "Validated",       "No traction yet"),
        (not profile.get("needs_funding"),"Funding", "Not fundraising", funding_need.upper()),
    ]:
        cls = "flag-ok" if ok else "flag-warn"
        icon = "✅" if ok else "⚠️"
        txt  = yes_t if ok else no_t
        flags_html += f'<span class="flag {cls}">{icon} {label}: {txt}</span>'
    st.markdown(f"<div>{flags_html}</div>", unsafe_allow_html=True)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Recommended Resources ──────────────────────────────────────────────
    ai_label = " &nbsp;<span style='font-size:0.68rem;background:#eff6ff;color:#1d4ed8;padding:2px 10px;border-radius:20px;font-weight:600;'>⚡ AI-powered</span>" if llm_powered else ""
    st.markdown(f'<div class="section-label">Recommended Resources — {len(results)} matches{ai_label}</div>', unsafe_allow_html=True)

    # Simple rule matrix determining which maturity dimension a resource boosts
    RESOURCE_BOOST_MAP = {
        "program": ["product", "traction"],
        "expertise": ["legal", "funding"],
        "mentorship": ["team", "market"],
        "service": ["branding", "product"],
        "investment": ["funding", "traction"],
        "network": ["market", "team"]
    }

    PRIORITY = {
        "immediate":  ("#be123c","#fff1f2","#fecaca","🔴","Do this now"),
        "short-term": ("#92400e","#fffbeb","#fde68a","🟡","Next 1–3 months"),
        "when-ready": ("#166534","#f0fdf4","#bbf7d0","🟢","When ready"),
    }
    TYPE_COLORS = {
        "program":    ("#1d4ed8","#eff6ff"),
        "expertise":  ("#92400e","#fef3c7"),
        "mentorship": ("#166534","#dcfce7"),
        "service":    ("#6d28d9","#f5f3ff"),
        "investment": ("#be123c","#fff1f2"),
        "network":    ("#164e63","#ecfeff"),
    }

    if not results:
        st.info("No strong matches found — try adjusting your answers, particularly around stage and funding needs.")
    else:
        for i, r in enumerate(results):
            sc        = min(r["score"], 100)
            priority  = r.get("priority","short-term")
            p_fg, p_bg, p_border, p_icon, p_label = PRIORITY.get(priority, PRIORITY["short-term"])
            t_fg, t_bg = TYPE_COLORS.get(r["type"], ("#1d4ed8","#eff6ff"))
            bar_color = "#2563eb" if sc >= 70 else ("#0891b2" if sc >= 50 else "#7c3aed")

            # Calculate simulated target progression scores
            boosted_keys = RESOURCE_BOOST_MAP.get(r["type"], ["product"])
            after_scores = []
            for k, cur_sc in zip(dim_keys, scores):
                if k in boosted_keys:
                    after_scores.append(min(cur_sc + 25, 100))
                else:
                    after_scores.append(cur_sc)

            reasons_html = "".join([
                f'<span style="display:inline-block;background:#f0f4ff;color:#2563eb;border-radius:20px;'
                f'padding:3px 12px;font-size:0.74rem;margin:2px 2px 0 0;border:1px solid #dbeafe;">✓ {rr}</span>'
                for rr in r.get("reasons",[])
            ])

            advice_html = ""
            if r.get("advice"):
                advice_html = (
                    f'<div style="margin-top:0.85rem;padding:0.65rem 1rem;background:#f8faff;'
                    f'border-left:3px solid #2563eb;border-radius:0 8px 8px 0;'
                    f'font-size:0.82rem;color:#1e3a8a;line-height:1.5;">'
                    f'💬 {r["advice"]}</div>'
                )

            # High-performance inline markup housing both the card text and the interactive ChartJS engine
            card = f"""
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;600;700&display=swap" rel="stylesheet">

<div style="background:white;border-radius:16px;padding:1.5rem 1.75rem;
    border:1px solid #e2e8f0;box-shadow:0 2px 12px rgba(10,22,40,0.05);
    font-family:'DM Sans', sans-serif;" id="card-{i}">

  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
      <span style="font-family:'DM Mono',monospace;font-size:0.72rem;color:#94a3b8;font-weight:500;">#{i+1:02d}</span>
      <span style="font-size:1rem;font-weight:700;color:#0a1628;">{r['name']}</span>
      <span style="font-size:0.7rem;font-weight:600;padding:2px 10px;border-radius:20px;
          background:{t_bg};color:{t_fg};">{r['type'].capitalize()}</span>
      <span style="font-size:0.7rem;font-weight:600;padding:2px 10px;border-radius:20px;
          background:{p_bg};color:{p_fg};border:1px solid {p_border};">{p_icon} {p_label}</span>
    </div>
    <div style="display:flex;align-items:baseline;gap:2px;">
      <span style="font-family:'DM Mono',monospace;font-size:1.5rem;font-weight:500;color:#0a1628;">{int(sc)}</span>
      <span style="font-size:0.75rem;color:#94a3b8;">/100</span>
    </div>
  </div>

  <div style="background:#f1f5f9;border-radius:4px;height:5px;margin:0.8rem 0;overflow:hidden;">
    <div style="background:{bar_color};border-radius:4px;height:5px;width:{sc}%;"></div>
  </div>

  <p style="font-size:0.85rem;color:#64748b;margin:0 0 0.6rem 0;line-height:1.55;">{r['description']}</p>
  <div style="margin-bottom:2px;">{reasons_html}</div>
  {advice_html}

  <div style="margin-top:1rem;padding-top:0.75rem;border-top:1px solid #f1f5f9;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
    <a href="{r['url']}" target="_blank"
       style="font-size:0.8rem;color:#2563eb;text-decoration:none;font-weight:600;
           display:inline-flex;align-items:center;gap:4px;">
      Learn more on thedot.tn →
    </a>
  </div>

  <div id="prog-{i}">
    <div style="margin-top:1.5rem;padding-top:1.25rem;border-top:1px dashed #e2e8f0;">
      <div style="background:linear-gradient(160deg,#0a1628 0%,#0f2557 100%);border-radius:12px;padding:1.25rem;">
        <div style="font-size:0.8rem;font-weight:600;color:#fff;margin-bottom:2px;">Estimated Impact Strategy</div>
        <div style="font-size:0.72rem;color:rgba(255,255,255,0.4);margin-bottom:1rem;">Visualizing maturity transformation if you complete this resource program.</div>
        <div style="position:relative;width:100%;max-width:380px;height:260px;margin:0 auto;">
          <canvas id="impactChart-{i}"></canvas>
        </div>
        <div style="display:flex;justify-content:center;gap:16px;margin-top:0.75rem;">
          <span style="display:flex;align-items:center;gap:6px;font-size:0.68rem;color:rgba(255,255,255,0.45);">
            <span style="width:8px;height:8px;border-radius:50%;background:#94a3b8;display:inline-block;"></span> Before (Current)
          </span>
          <span style="display:flex;align-items:center;gap:6px;font-size:0.68rem;color:rgba(255,255,255,0.45);">
            <span style="width:8px;height:8px;border-radius:50%;background:#38bdf8;display:inline-block;"></span> After (Projected)
          </span>
        </div>
      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
(function() {{
  setTimeout(function() {{
    var ctx = document.getElementById('impactChart-{i}').getContext('2d');
    new Chart(ctx, {{
      type: 'radar',
      data: {{
        labels: {dims_json},
        datasets: [
          {{
            label: 'Before',
            data: {scores_json},
            backgroundColor: 'rgba(148,163,184,0.08)',
            borderColor: '#94a3b8',
            borderWidth: 1.5,
            borderDash: [3,3],
            pointRadius: 2,
            pointBackgroundColor: '#94a3b8'
          }},
          {{
            label: 'After',
            data: {json.dumps(after_scores)},
            backgroundColor: 'rgba(56,189,248,0.18)',
            borderColor: '#38bdf8',
            borderWidth: 2,
            pointRadius: 3,
            pointBackgroundColor: '#fff',
            pointBorderColor: '#38bdf8'
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          r: {{
            min: 0, max: 100,
            ticks: {{ display: false, stepSize: 25 }},
            pointLabels: {{ font: {{ size: 9, family: 'DM Sans', weight: '600' }}, color: 'rgba(255,255,255,0.7)' }},
            grid: {{ color: 'rgba(255,255,255,0.06)' }},
            angleLines: {{ color: 'rgba(255,255,255,0.06)' }}
          }}
        }}
      }}
    }});
  }}, 50);
}})();
</script>
"""
            n_r = len(r.get("reasons",[]))
            has_adv = bool(r.get("advice"))
            # Adjusted height container calculation to comfortably adapt the newly layouted open view
            h = 240 + n_r * 32 + (85 if has_adv else 0) + 400
            components.html(card, height=h, scrolling=False)

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # ── Progress Summary Export Setup ─────────────────────────────────────
    st.markdown('<div class="section-label">Export</div>', unsafe_allow_html=True)

    avg_score   = int(sum(scores) / len(scores)) if scores else 0
    weak_label  = dims[scores.index(min(scores))] if scores else "—"
    strong_label= dims[scores.index(max(scores))] if scores else "—"

    summary = {
        "startup": name_display, "stage": effective_stage, "sector": sector,
        "generated": "The Dot Resource Matcher — thedot.tn",
        "radar_scores": dict(zip(dims, scores)),
        "average_score": avg_score,
        "strongest_dimension": strong_label,
        "priority_gap": weak_label,
        "flags": {k: v for k, v in profile.items() if k != "needs"},
        "identified_needs": sorted(profile.get("needs",[])),
        "top_resources": [
            {"rank":i+1,"name":r["name"],"score":r["score"],"type":r["type"],"priority":r.get("priority",""),"advice":r.get("advice","")}
            for i,r in enumerate(results)
        ],
    }

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 Download Full Report (JSON)",
            data=json.dumps(summary, indent=2, ensure_ascii=False),
            file_name=f"dot_diagnostic_{name_display.replace(' ','_').lower()}.json",
            mime="application/json",
        )
    with col2:
        st.button("🔄 Start Over", on_click=lambda: st.session_state.clear())

    st.markdown('</div>', unsafe_allow_html=True)  # close results-wrap
