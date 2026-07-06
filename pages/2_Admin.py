"""
pages/2_Admin.py — Dashboard admin The Dot (Back office)

Accès : URL directe /Admin — protégé par login.
Les startups ne voient jamais cette page (sidebar cachée partout).
L'auth gate est la première chose exécutée : sans login valide, rien ne s'affiche.
"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

st.set_page_config(
    page_title="The Dot — Admin",
    page_icon="🔵",
    layout="wide",
)

import styles
st.markdown(styles.HIDE_SIDEBAR, unsafe_allow_html=True)

# Guard DB init
from database import init_db, DatabaseError
if "db_initialized" not in st.session_state:
    try:
        init_db()
        st.session_state["db_initialized"] = True
    except Exception as e:
        st.session_state["db_initialized"] = False
        st.error(f"Base de données inaccessible : {e}")
        st.stop()

from auth import login_page, current_user, logout, is_admin, user_management_ui, bootstrap_admin

try:
    bootstrap_admin()
except Exception:
    pass

# ── Auth gate ─────────────────────────────────────────────────────────────────
# login_page() handles layout CSS, back link, and ghost-widget cleanup itself.
if not current_user():
    login_page()
    st.stop()

# ── Utilisateur connecté ──────────────────────────────────────────────────────
from database import (
    get_stats, get_all_diagnostics, get_diagnostic_with_recs,
    delete_diagnostic,
)
from pdf_export import generate_diagnostic_pdf

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json

user = current_user()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

/* ── Global dark theme ────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background: #060d1c !important;
    color: #e2e8f0;
}
.stApp, .stApp > div { background: #060d1c; }
.block-container { background: transparent !important; padding-top: 1.5rem !important; }

/* Inputs / selects */
input, select, textarea, [data-testid="stTextInput"] input,
[data-testid="stSelectbox"] div { background: #0d1b35 !important; color: #e2e8f0 !important; border-color: #1e293b !important; }

/* Metric delta color */
[data-testid="stMetricValue"] { color: #93c5fd !important; font-family: 'DM Mono', monospace; }

/* ── Admin header ────────────────────────────────────────────────────────── */
.admin-header {
    background: linear-gradient(135deg, #060d1c 0%, #0d1f45 100%);
    padding: 1.4rem 2rem; border-radius: 18px; margin-bottom: 1rem;
    display: flex; justify-content: space-between; align-items: center;
    border: 1px solid rgba(96,165,250,0.12);
    box-shadow: 0 4px 28px rgba(0,0,0,0.5);
    position: relative; overflow: hidden;
}
.admin-header::after {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent 0%, rgba(96,165,250,0.4) 40%, rgba(139,92,246,0.3) 70%, transparent 100%);
}

/* ── KPI cards ───────────────────────────────────────────────────────────── */
.admin-kpi {
    background: linear-gradient(145deg, #0a1628 0%, #0f2557 100%);
    border-radius: 16px; padding: 1.5rem 1.25rem;
    border: 1px solid rgba(96,165,250,0.14);
    box-shadow: 0 4px 20px rgba(0,0,0,0.35);
    text-align: center; position: relative; overflow: hidden;
}
.admin-kpi::before {
    content: ''; position: absolute; top: 0; left: 25%; right: 25%; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(96,165,250,0.55), transparent);
}
.kpi-val {
    font-family: 'DM Mono', monospace; font-size: 2.2rem;
    font-weight: 500; color: #93c5fd; line-height: 1.2;
}
.kpi-label {
    font-size: 0.65rem; color: rgba(255,255,255,0.6);
    letter-spacing: 0.08em; text-transform: uppercase; margin-top: 8px;
}

/* ── Section dividers ────────────────────────────────────────────────────── */
.section-title {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #e2e8f0;
    margin: 2.5rem 0 1.2rem; padding-bottom: 0.6rem;
    border-bottom: 1px solid #1e3a5f;
    display: flex; align-items: center; gap: 10px;
}
.section-title::before {
    content: ''; width: 3px; height: 13px; border-radius: 2px;
    background: linear-gradient(180deg, #2563eb, #60a5fa); flex-shrink: 0;
}

/* ── Diagnostic rows ─────────────────────────────────────────────────────── */
.diag-info { padding: 0.4rem 0; }
.diag-name { font-weight: 600; color: #e2e8f0; font-size: 0.92rem; }
.diag-sub  { font-size: 0.74rem; color: rgba(255,255,255,0.3); margin-top: 2px; }

/* Streamlit divider override */
hr { border-color: #1e293b !important; }
[data-testid="stSeparator"] { border-color: #1e293b !important; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="admin-header">
  <div>
    <div style="font-size:1.2rem;font-weight:700;color:white;">🔵 The Dot — Admin Dashboard</div>
    <div style="font-size:0.8rem;color:rgba(255,255,255,0.45);margin-top:2px;">
      Connecté en tant que <strong style="color:#93c5fd;">{user['username']}</strong>
      &nbsp;·&nbsp; Rôle : <strong style="color:#93c5fd;">{user['role']}</strong>
    </div>
  </div>
  <div style="display:flex;gap:10px;align-items:center;">
    <a href="/" target="_self" style="font-size:0.78rem;color:rgba(255,255,255,0.4);text-decoration:none;padding:6px 14px;border:1px solid rgba(255,255,255,0.15);border-radius:8px;">← Accueil</a>
  </div>
</div>
""", unsafe_allow_html=True)

col_logout = st.columns([8, 1])[1]
with col_logout:
    if st.button("Déconnexion", key="btn_logout"):
        logout()
        st.rerun()

# ── Stats ─────────────────────────────────────────────────────────────────────
try:
    stats = get_stats()
except DatabaseError as e:
    st.error(f"Impossible de charger les statistiques : {e}")
    if st.button("🔄 Réessayer"):
        st.rerun()
    st.stop()

# ══════════════════════════════════════════════════════════════════════════
# 1. VUE D'ENSEMBLE
# ══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">Vue d\'ensemble</div>', unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f'<div class="admin-kpi"><div class="kpi-val">{stats.get("total_diagnostics",0)}</div><div class="kpi-label">Diagnostics</div></div>', unsafe_allow_html=True)
with k2:
    avg = stats.get("avg_scores", {})
    global_avg = int(sum(avg.values()) / len(avg)) if avg else 0
    st.markdown(f'<div class="admin-kpi"><div class="kpi-val">{global_avg}</div><div class="kpi-label">Score moyen</div></div>', unsafe_allow_html=True)
with k3:
    sectors = stats.get("by_sector", [])
    if isinstance(sectors, list):
        sectors_dict = {s["sector"]: s["count"] for s in sectors}
    else:
        sectors_dict = sectors
    top_sector = max(sectors_dict, key=sectors_dict.get) if sectors_dict else "—"
    ts_display = top_sector.capitalize() if top_sector != "—" else "—"
    st.markdown(f'<div class="admin-kpi"><div class="kpi-val" style="font-size:2.1rem;font-family:\'DM Sans\',sans-serif;font-weight:600;">{ts_display}</div><div class="kpi-label">Secteur dominant</div></div>', unsafe_allow_html=True)
with k4:
    monthly_raw = stats.get("monthly_trend", [])
    if isinstance(monthly_raw, list):
        monthly = {m["month"]: m["count"] for m in monthly_raw}
    else:
        monthly = monthly_raw
    last_month = list(monthly.values())[-1] if monthly else 0
    st.markdown(f'<div class="admin-kpi"><div class="kpi-val">{last_month}</div><div class="kpi-label">Ce mois-ci</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
col_left, col_right = st.columns(2)

with col_left:
    if avg:
        dims_r   = list(avg.keys())
        values_r = list(avg.values())
        fig_radar = go.Figure(go.Scatterpolar(
            r=values_r + [values_r[0]], theta=dims_r + [dims_r[0]],
            fill="toself",
            fillcolor="rgba(96,165,250,0.12)",
            line=dict(color="#60a5fa", width=2),
        ))
        fig_radar.update_layout(
            title=dict(text="Maturité moyenne", font=dict(size=12, color="rgba(255,255,255,0.85)", family="DM Sans")),
            polar=dict(
                radialaxis=dict(visible=True, range=[0,100], tickfont=dict(size=8, color="rgba(255,255,255,0.25)"), gridcolor="rgba(255,255,255,0.07)", linecolor="rgba(255,255,255,0.07)"),
                angularaxis=dict(tickfont=dict(size=10, color="rgba(255,255,255,0.85)", family="DM Sans")),
                bgcolor="rgba(0,0,0,0)",
            ),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=50, b=20, l=40, r=40), height=320,
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig_radar, use_container_width=True, key="chart_radar_global")

with col_right:
    if monthly:
        fig_line = px.line(
            x=list(monthly.keys()), y=list(monthly.values()),
            labels={"x": "Mois", "y": "Diagnostics"},
            markers=True, color_discrete_sequence=["#60a5fa"],
        )
        fig_line.update_traces(marker=dict(size=7, color="#93c5fd", line=dict(width=2, color="#60a5fa")))
        fig_line.update_layout(
            title=dict(text="Évolution mensuelle", font=dict(size=12, color="rgba(255,255,255,0.85)", family="DM Sans")),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickfont=dict(color="rgba(255,255,255,0.6)", family="DM Sans"), gridcolor="rgba(255,255,255,0.06)", linecolor="rgba(255,255,255,0.1)"),
            yaxis=dict(tickfont=dict(color="rgba(255,255,255,0.6)", family="DM Sans"), gridcolor="rgba(255,255,255,0.06)", linecolor="rgba(255,255,255,0.1)"),
            margin=dict(t=50, b=20, l=20, r=20), height=320,
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig_line, use_container_width=True, key="chart_line_monthly")

if sectors_dict:
    fig_sector = px.pie(
        names=list(sectors_dict.keys()), values=list(sectors_dict.values()),
        color_discrete_sequence=["#2563eb","#7c3aed","#0891b2","#059669","#dc2626","#d97706","#db2777","#4f46e5"],
        hole=0.45,
    )
    fig_sector.update_traces(textfont=dict(color="rgba(255,255,255,0.8)", family="DM Sans"), marker=dict(line=dict(color="#060d1c", width=2)))
    fig_sector.update_layout(
        title=dict(text="Répartition par secteur", font=dict(size=12, color="rgba(255,255,255,0.85)", family="DM Sans")),
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(color="rgba(255,255,255,0.7)", family="DM Sans"), bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=50, b=20, l=20, r=20), height=320,
        font=dict(family="DM Sans"),
    )
    st.plotly_chart(fig_sector, use_container_width=True, key="chart_pie_sectors")

# ══════════════════════════════════════════════════════════════════════════
# 2. DIAGNOSTICS
# ══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">Historique des diagnostics</div>', unsafe_allow_html=True)


try:
    all_diags = get_all_diagnostics()
except DatabaseError as e:
    st.error(f"Impossible de charger les diagnostics : {e}")
    all_diags = []

if all_diags:
    col_search, col_stage, col_sector = st.columns([3, 2, 2])
    with col_search:
        search_query = st.text_input("🔍 Recherche par nom", placeholder="Nom de la startup...")
    with col_stage:
        stages_present = sorted(set(d.get("stage","") for d in all_diags if d.get("stage")))
        filter_stage = st.selectbox("Stage", ["Tous les stages"] + stages_present, key="filter_stage")
    with col_sector:
        sectors_present = sorted(set(d.get("sector","") for d in all_diags if d.get("sector")))
        filter_sector = st.selectbox("Secteur", ["Tous les secteurs"] + sectors_present, key="filter_sector")

    filtered_diags = all_diags
    if search_query.strip():
        q = search_query.strip().lower()
        filtered_diags = [d for d in filtered_diags if q in d.get("startup_name","").lower()]
    if filter_stage != "Tous les stages":
        filtered_diags = [d for d in filtered_diags if d.get("stage") == filter_stage]
    if filter_sector != "Tous les secteurs":
        filtered_diags = [d for d in filtered_diags if d.get("sector") == filter_sector]

    st.caption(f"{len(filtered_diags)} résultat(s) sur {len(all_diags)} diagnostics")

    for diag in filtered_diags:
        scores = diag.get("scores", {})
        avg_sc = int(sum(scores.values()) / len(scores)) if scores else 0
        sc_color = "#4ade80" if avg_sc >= 70 else ("#facc15" if avg_sc >= 40 else "#f87171")
        sector_tag = diag.get("sector","—")
        stage_tag  = diag.get("stage","—")
        created    = str(diag.get("created_at",""))[:10]

        st.markdown(f"""
<div style="background:linear-gradient(145deg,#0a1628 0%,#0d1b35 100%);
            border-radius:14px;padding:0.9rem 1.3rem;border:1px solid #1a2744;
            margin-bottom:4px;display:flex;justify-content:space-between;align-items:center;gap:12px;">
  <div style="flex:1;min-width:0;">
    <div style="font-size:0.9rem;font-weight:600;color:#e2e8f0;
                white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
      {diag.get('startup_name','—')}
    </div>
    <div style="display:flex;gap:5px;margin-top:4px;flex-wrap:wrap;">
      <span style="background:rgba(255,255,255,0.06);color:rgba(255,255,255,0.4);
                   border-radius:20px;padding:1px 9px;font-size:0.68rem;">{sector_tag}</span>
      <span style="background:rgba(37,99,235,0.18);color:#93c5fd;
                   border-radius:20px;padding:1px 9px;font-size:0.68rem;">{stage_tag}</span>
    </div>
  </div>
  <div style="text-align:right;flex-shrink:0;">
    <div style="font-family:'DM Mono',monospace;font-size:1.35rem;
                font-weight:500;color:{sc_color};">
      {avg_sc}<span style="font-size:0.72rem;color:rgba(255,255,255,0.2);"> /100</span>
    </div>
    <div style="font-size:0.65rem;color:rgba(255,255,255,0.2);margin-top:1px;">{created}</div>
  </div>
</div>""", unsafe_allow_html=True)

        _, b1, b2 = st.columns([7, 1.2, 0.9])
        with b1:
            if st.button("👁️ Détail", key=f"view_diag_{diag['id']}", use_container_width=True):
                st.session_state[f"expand_{diag['id']}"] = not st.session_state.get(f"expand_{diag['id']}", False)
        with b2:
            if is_admin() and st.button("🗑️", key=f"del_diag_{diag['id']}", use_container_width=True, help="Supprimer"):
                try:
                    delete_diagnostic(diag["id"])
                    st.success("Supprimé.")
                    st.rerun()
                except DatabaseError as e:
                    st.error(str(e))

        if st.session_state.get(f"expand_{diag['id']}"):
            try:
                detail = get_diagnostic_with_recs(diag["id"])
                if detail:
                    with st.expander("Détail complet", expanded=True):
                        d_scores = detail.get("scores", {})
                        if d_scores:
                            dims_d   = list(d_scores.keys())
                            vals_d   = list(d_scores.values())
                            fig_mini = go.Figure(go.Scatterpolar(
                                r=vals_d + [vals_d[0]], theta=dims_d + [dims_d[0]],
                                fill="toself",
                                fillcolor="rgba(96,165,250,0.12)",
                                line=dict(color="#60a5fa", width=1.5),
                            ))
                            fig_mini.update_layout(
                                polar=dict(
                                    radialaxis=dict(range=[0,100], tickfont=dict(size=8, color="rgba(255,255,255,0.25)"), gridcolor="rgba(255,255,255,0.07)", linecolor="rgba(255,255,255,0.07)"),
                                    angularaxis=dict(tickfont=dict(size=9, color="rgba(255,255,255,0.6)", family="DM Sans")),
                                    bgcolor="rgba(0,0,0,0)",
                                ),
                                paper_bgcolor="rgba(0,0,0,0)", height=400,
                                margin=dict(t=10, b=10, l=20, r=20),
                                font=dict(family="DM Sans"),
                            )
                            st.plotly_chart(fig_mini, use_container_width=True, key=f"chart_mini_{diag['id']}")

                        needs = detail.get("needs", [])
                        if needs:
                            st.caption("Besoins identifiés :")
                            st.write(", ".join(needs))

                        recs = detail.get("recommendations", [])
                        if recs:
                            st.caption("Recommandations :")
                            for rec in recs[:5]:
                                st.markdown(f"• **{rec.get('program_name','?')}** — score {rec.get('score',0):.0f}/100")

                        try:
                            pdf_bytes = generate_diagnostic_pdf(detail)
                            fname = f"dot_rapport_{detail.get('startup_name','startup').replace(' ','_').lower()}.pdf"
                            st.download_button(
                                "📄 Télécharger le rapport PDF",
                                data=pdf_bytes,
                                file_name=fname,
                                mime="application/pdf",
                                key=f"pdf_{diag['id']}",
                            )
                        except Exception as e:
                            st.warning(f"PDF indisponible : {e}")
            except DatabaseError as e:
                st.error(str(e))

else:
    st.info("Aucun diagnostic enregistré pour l'instant.")

# ══════════════════════════════════════════════════════════════════════════
# 3. PROGRAMMES
# ══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">Programmes — score moyen</div>', unsafe_allow_html=True)

try:
    top_programs = stats.get("top_programs", [])
    if top_programs:
        df_prog = pd.DataFrame(top_programs)
        if "avg_score" in df_prog.columns and "program_name" in df_prog.columns:
            df_prog = df_prog.sort_values("avg_score", ascending=False)
            fig_bar = px.bar(
                df_prog, x="program_name", y="avg_score",
                color="avg_score",
                color_continuous_scale=[[0,"#1e3a8a"],[0.5,"#2563eb"],[1,"#93c5fd"]],
                labels={"program_name": "Programme", "avg_score": "Score moyen"},
            )
            fig_bar.update_traces(marker_line_color="rgba(0,0,0,0)")
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(tickfont=dict(color="rgba(255,255,255,0.4)", family="DM Sans"), title=None, gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.1)"),
                yaxis=dict(tickfont=dict(color="rgba(255,255,255,0.4)", family="DM Sans"), range=[0, 100], gridcolor="rgba(255,255,255,0.07)", linecolor="rgba(255,255,255,0.1)"),
                coloraxis_showscale=False,
                margin=dict(t=20, b=40, l=20, r=20), height=300,
                font=dict(family="DM Sans"),
            )
            st.plotly_chart(fig_bar, use_container_width=True, key="chart_bar_programs")
    else:
        st.info("Pas encore de données suffisantes pour ce graphique.")
except Exception as e:
    st.error(f"Impossible de charger les données programmes : {e}")

# ══════════════════════════════════════════════════════════════════════════
# 4. GESTION DES PROGRAMMES (admin only)
# ══════════════════════════════════════════════════════════════════════════
if is_admin():
    st.markdown('<div class="section-title">Catalogue des programmes</div>', unsafe_allow_html=True)
    import csv
    from matcher import load_resources, _cached_resource_embeddings

    RESOURCES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources.csv")

    def _load_csv_raw() -> list:
        with open(RESOURCES_PATH, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _save_csv_raw(rows: list, fieldnames: list) -> None:
        with open(RESOURCES_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rows)
        load_resources.clear()
        _cached_resource_embeddings.clear()

    def _next_id(rows: list) -> str:
        existing = [int(r["id"].replace("R","")) for r in rows if r.get("id","").startswith("R") and r["id"][1:].isdigit()]
        return f"R{(max(existing) + 1):03d}" if existing else "R001"

    rows = _load_csv_raw()
    fieldnames = list(rows[0].keys()) if rows else []

    # ── Voir et supprimer ─────────────────────────────────────────────────
    with st.expander(f"📋 Voir et supprimer des programmes ({len(rows)} au total)", expanded=False):
        for row in rows:
            col_name, col_type, col_del = st.columns([4, 2, 1])
            with col_name:
                st.markdown(f"**{row.get('name','?')}**")
                st.caption(row.get('description','')[:120] + "…" if len(row.get('description','')) > 120 else row.get('description',''))
            with col_type:
                st.caption(f"ID: `{row.get('id','')}` · {row.get('type','')}")
                stages_str = row.get('stages','')
                st.caption(f"Stades: {stages_str}")
            with col_del:
                if st.button("🗑️", key=f"del_prog_{row['id']}", help=f"Supprimer {row.get('name','')}"):
                    st.session_state[f"confirm_del_{row['id']}"] = True
            if st.session_state.get(f"confirm_del_{row['id']}"):
                st.warning(f"Supprimer **{row.get('name','')}** ({row.get('id','')}) ? Cette action est irréversible.")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmer la suppression", key=f"confirm_yes_{row['id']}"):
                        rows = [r for r in rows if r["id"] != row["id"]]
                        _save_csv_raw(rows, fieldnames)
                        del st.session_state[f"confirm_del_{row['id']}"]
                        st.success(f"{row.get('name','')} supprimé.")
                        st.rerun()
                with c2:
                    if st.button("❌ Annuler", key=f"confirm_no_{row['id']}"):
                        del st.session_state[f"confirm_del_{row['id']}"]
                        st.rerun()
            st.divider()

    # ── Ajouter un programme ──────────────────────────────────────────────
    with st.expander("➕ Ajouter un nouveau programme", expanded=False):
        st.markdown("Tous les champs marqués **\*** sont obligatoires.")
        with st.form("add_programme_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                new_name = st.text_input("Nom du programme *")
            with c2:
                new_type = st.selectbox("Type *", ["program","mentorship","service","network","event","other"])
            with c3:
                new_url = st.text_input("URL *", placeholder="https://thedot.tn/...")

            new_description = st.text_area("Description *", height=100)
            new_ideal = st.text_area("Profil idéal", height=80, help="Qui profite le plus de ce programme ?")
            new_not_suited = st.text_area("Non adapté pour", height=60, help="Qui devrait éviter ce programme ?")
            new_sequencing = st.text_area("Note de séquencement", height=60, help="Quand postuler par rapport aux autres programmes ?")

            c1, c2 = st.columns(2)
            with c1:
                new_stages = st.multiselect("Stades éligibles *", ["ideation","pre-seed","seed","growth","scale"])
            with c2:
                new_needs = st.multiselect("Besoins couverts *", [
                    "acceleration","ai","branding","coaching","cohort","community","content_creation",
                    "content_production","design","diaspora_support","distribution","events",
                    "fiscal","hosting","incorporation","internationalization","investor_readiness",
                    "leadership","legal","legal_structuring","market_access","mentorship",
                    "networking","partnerships","product","recruitment","regional_support",
                    "scaling","soft_landing","strategy","tech_support","team_building",
                    "workspace","workspace_events",
                ])
            with st.expander("📖 Guide des besoins — que choisir ?", expanded=False):
                st.markdown("""
| Keyword | Quand l'utiliser |
|---------|-----------------|
| `acceleration` | Programme d'accélération structuré avec cohorte et mentors |
| `ai` | Accès à infrastructure ML, GPU, ou expertise IA/NLP |
| `branding` | Aide à l'identité visuelle, naming, pitch deck design |
| `coaching` | Accompagnement individuel régulier (1-on-1) |
| `cohort` | Programme en groupe avec d'autres startups (cohorte) |
| `community` | Accès à un réseau de pairs, événements communautaires |
| `content_creation` | Aide à la production de contenu marketing/social |
| `design` | Support en UX/UI ou design produit |
| `diaspora_support` | Programme spécifiquement conçu pour la diaspora tunisienne |
| `distribution` | Aide à trouver des canaux de vente / partenaires de distribution |
| `fiscal` | Conseil fiscal, optimisation taxes, comptabilité |
| `hosting` | Espace de travail physique fourni (bureau, poste de travail) |
| `incorporation` | Aide à créer la structure légale (SUARL, SARL, SA) |
| `internationalization` | Aide à l'expansion vers des marchés étrangers |
| `investor_readiness` | Préparation au pitch investisseur, due diligence, valorisation |
| `leadership` | Développement des compétences managériales du fondateur |
| `legal` | Conseil juridique général (contrats, PI, litiges) |
| `legal_structuring` | Structuration légale de la startup (statuts, pacte d'associés) |
| `market_access` | Mise en relation avec des clients ou partenaires commerciaux |
| `mentorship` | Accès à des mentors seniors (pas nécessairement 1-on-1) |
| `networking` | Événements et mise en relation avec l'écosystème |
| `partnerships` | Mise en relation avec des partenaires institutionnels ou SSOs |
| `product` | Aide au développement produit, MVP, roadmap |
| `recruitment` | Aide à recruter des talents (tech, business, etc.) |
| `regional_support` | Programme ciblant les régions hors hubs côtiers |
| `scaling` | Accompagnement pour passer à l'échelle (équipe, opérations) |
| `soft_landing` | Accueil et intégration dans l'écosystème local (diaspora) |
| `strategy` | Conseil en stratégie business, positionnement, pivot |
| `tech_support` | Accès à des outils tech, infra cloud, ou expertise technique |
| `team_building` | Aide à constituer et structurer l'équipe fondatrice |
| `workspace` | Espace de coworking ou bureau partagé |
| `workspace_events` | Accès aux salles de réunion, studios, espaces événements |
                """)

            c1, c2, c3 = st.columns(3)
            with c1:
                new_sectors = st.multiselect("Secteurs ciblés", [
                    "all","tech","fintech","healthtech","edtech","agritech","cleantech",
                    "commerce","industry","manufacturing","retail","saas","marketplace","other"
                ], default=["all"])
            with c2:
                new_diaspora = st.checkbox("Réservé aux fondateurs diaspora (diaspora_only)")
            with c3:
                new_intl = st.checkbox("Focus international (international_focus)")

            submitted = st.form_submit_button("✅ Ajouter le programme", use_container_width=True)
            if submitted:
                errors = []
                if not new_name.strip():    errors.append("Nom obligatoire")
                if not new_url.strip():     errors.append("URL obligatoire")
                if not new_description.strip(): errors.append("Description obligatoire")
                if not new_stages:          errors.append("Au moins un stade obligatoire")
                if not new_needs:           errors.append("Au moins un besoin obligatoire")
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    fresh_rows = _load_csv_raw()
                    fresh_fields = list(fresh_rows[0].keys()) if fresh_rows else fieldnames
                    new_row = {k: "" for k in fresh_fields}
                    new_row["id"]                = _next_id(fresh_rows)
                    new_row["name"]              = new_name.strip()
                    new_row["type"]              = new_type
                    new_row["description"]       = new_description.strip()
                    new_row["ideal_profile"]     = new_ideal.strip()
                    new_row["not_suited_for"]    = new_not_suited.strip()
                    new_row["sequencing_note"]   = new_sequencing.strip()
                    new_row["stages"]            = ",".join(new_stages)
                    new_row["needs"]             = ",".join(new_needs)
                    new_row["sectors"]           = ",".join(new_sectors) if new_sectors else "all"
                    new_row["diaspora_only"]     = "TRUE" if new_diaspora else "FALSE"
                    new_row["outside_hub_only"]  = "FALSE"
                    new_row["international_focus"] = "TRUE" if new_intl else "FALSE"
                    new_row["url"]               = new_url.strip()
                    fresh_rows.append(new_row)
                    _save_csv_raw(fresh_rows, fresh_fields)
                    # Invalider le cache Streamlit pour que le nouveau programme
                    # soit pris en compte immédiatement sans restart du serveur
                    load_resources.clear()
                    _cached_resource_embeddings.clear()
                    st.success(f"✅ Programme **{new_row['name']}** ({new_row['id']}) ajouté avec succès !")
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# 5. PARAMÈTRES DU MOTEUR (admin only)
# ══════════════════════════════════════════════════════════════════════════
if is_admin():
    st.markdown('<div class="section-title">Paramètres du moteur</div>', unsafe_allow_html=True)
    import app_settings as _settings

    current = _settings.load()

    # ── Vector store status + rebuild (outside form so button works standalone) ──
    st.markdown("##### Base de données vectorielle")

    # Recommendation banner
    _res_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources.csv")
    df_count = len(pd.read_csv(_res_path))

    if df_count < 30:
        _mode_label = "🟢 Pondération hybride — idéale"
        _mode_color = "info"
        _mode_advice = (
            f"Vous avez **{df_count} programmes**. "
            "À cette échelle, la pondération hybride est parfaite : elle calcule un score complet "
            "(règles métier + sémantique) pour chaque programme en quelques millisecondes. "
            "**Garder la base vectorielle désactivée.**"
        )
    elif df_count < 50:
        _mode_label = "🟡 Pondération hybride — encore suffisante"
        _mode_color = "warning"
        _mode_advice = (
            f"Vous avez **{df_count} programmes**. "
            "La pondération hybride reste rapide à cette taille, mais vous approchez du seuil. "
            "Vous pouvez commencer à initialiser la base vectorielle pour être prêt, "
            "mais **ne l'activez pas encore** — le score hybride est plus précis."
        )
    elif df_count < 200:
        _mode_label = "🟠 Base vectorielle — recommandée"
        _mode_color = "warning"
        _mode_advice = (
            f"Vous avez **{df_count} programmes**. "
            "À cette échelle, la recherche en mémoire commence à ralentir. "
            "**Initialisez et activez la base vectorielle ChromaDB** pour maintenir "
            "des temps de réponse rapides. Le score passera en mode similarité pure."
        )
    else:
        _mode_label = "🔴 Base vectorielle — obligatoire"
        _mode_color = "error"
        _mode_advice = (
            f"Vous avez **{df_count} programmes**. "
            "La pondération hybride en mémoire n'est plus viable à cette échelle. "
            "**La base vectorielle ChromaDB doit être activée** pour des performances acceptables."
        )

    # Display as a styled card
    st.markdown(f"**{_mode_label}** — {df_count} programmes dans le catalogue")
    if _mode_color == "info":
        st.info(_mode_advice, icon=None)
    elif _mode_color == "warning":
        st.warning(_mode_advice, icon=None)
    else:
        st.error(_mode_advice, icon=None)

    with st.expander("📊 Guide des seuils", expanded=False):
        st.markdown("""
| Catalogue | Mode recommandé | Raison |
|-----------|----------------|--------|
| **< 30 programmes** | Pondération hybride | Calcul instantané, score complet (règles + sémantique) |
| **30–50 programmes** | Hybride, préparer ChromaDB | Encore rapide, mais prévoir la transition |
| **50–200 programmes** | ChromaDB activé | Recherche vectorielle ANN plus rapide que O(n) |
| **200+ programmes** | ChromaDB obligatoire | O(log n) vs O(n) — différence de plusieurs secondes |

**Score hybride (OFF)** = `0.6 × règles_métier + 0.4 × sémantique_normalisé` → précis, intègre stade/besoins/secteur
**ChromaDB (ON)** = similarité cosine pure → rapide sur grand catalogue, perd la logique métier dans le score
        """)

    # ── RAG toggle (outside form so it controls show/hide immediately) ───────
    _rag_available = False
    _idx_ok = False
    try:
        from vector_store import index_exists, build_index
        from matcher import load_resources as _lr
        _rag_available = True
        _idx_ok = index_exists()
    except Exception:
        pass

    use_rag = st.toggle(
        "Activer la base de données vectorielle (RAG)",
        value=current.get("use_rag", False),
        disabled=not _rag_available,
        key="use_rag_toggle",
        help=(
            "OFF : score hybride = 0.6 × règles métier + 0.4 × sémantique — recommandé < 50 programmes. "
            "ON : recherche vectorielle ANN (ChromaDB) — recommandé 50+ programmes."
        ),
    )

    if not _rag_available:
        st.caption("ℹ️ Module vectoriel non disponible sur cette installation.")

    # ── Show ChromaDB section only when RAG is ON ─────────────────────────────
    if use_rag:
        st.markdown("##### Base vectorielle ChromaDB")
        col_rag_a, col_rag_b = st.columns([3, 1])
        with col_rag_a:
            if _idx_ok:
                st.success("✅ Index vectoriel disponible et à jour.")
            else:
                st.warning("⚠️ Index non initialisé — le moteur ne peut pas utiliser ChromaDB.")
        with col_rag_b:
            if st.button("⚡ Initialiser / Mettre à jour", use_container_width=True):
                with st.spinner("Construction de la base vectorielle…"):
                    build_index(_lr(), force=True)
                st.success("✅ Base vectorielle construite !")
                st.rerun()

    with st.form("engine_settings_form"):
        # ── Show hybrid sliders only when RAG is OFF ──────────────────────────
        if not use_rag:
            st.markdown("##### Pondération du matching")
            col1, col2 = st.columns(2)
            with col1:
                rule_w = st.slider(
                    "Priorité aux critères métier",
                    min_value=0.0, max_value=1.0, step=0.05,
                    value=float(current.get("rule_weight", 0.6)),
                    help="Part des règles métier (stade, besoins, secteur) dans le score.",
                )
            with col2:
                sem_w = st.slider(
                    "Priorité à la compréhension du contexte (IA)",
                    min_value=0.0, max_value=1.0, step=0.05,
                    value=float(current.get("semantic_weight", 0.4)),
                    help="Part de l'analyse sémantique IA dans le score.",
                )
            st.caption(f"Total : {round(rule_w + sem_w, 2)} (idéalement = 1.0)")
        else:
            rule_w = float(current.get("rule_weight", 0.6))
            sem_w  = float(current.get("semantic_weight", 0.4))

        st.markdown("##### Paramètres LLM")
        col3, col4 = st.columns(2)
        with col3:
            cand_limit = st.number_input(
                "Programmes envoyés au LLM",
                min_value=3, max_value=20, step=1,
                value=int(current.get("llm_candidate_limit", 10)),
                help="Nombre de programmes pré-sélectionnés transmis à l'IA pour le classement final.",
            )
        with col4:
            groq_to = st.number_input(
                "Délai d'attente Groq (secondes)",
                min_value=5, max_value=60, step=1,
                value=int(current.get("groq_timeout", 15)),
                help="Durée maximale d'attente de la réponse Groq avant bascule sur Ollama local.",
            )

        col_save, col_reset = st.columns(2)
        with col_save:
            if st.form_submit_button("💾 Enregistrer les paramètres", use_container_width=True):
                _settings.save({
                    "use_rag":             use_rag,
                    "rule_weight":         rule_w,
                    "semantic_weight":     sem_w,
                    "llm_candidate_limit": cand_limit,
                    "groq_timeout":        groq_to,
                })
                st.success("✅ Paramètres enregistrés.")
                st.rerun()
        with col_reset:
            if st.form_submit_button("🔄 Réinitialiser", use_container_width=True):
                _settings.reset()
                st.success("✅ Paramètres réinitialisés aux valeurs par défaut.")
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# 6. GESTION DES COMPTES (admin only)
# ══════════════════════════════════════════════════════════════════════════
if is_admin():
    st.markdown('<div class="section-title">Gestion des comptes</div>', unsafe_allow_html=True)
    user_management_ui()
