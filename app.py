"""app.py — The Dot · Page d'accueil"""
import streamlit as st

st.set_page_config(page_title="The Dot", page_icon="🔵", layout="centered", initial_sidebar_state="collapsed")

import styles
st.markdown(styles.HIDE_SIDEBAR, unsafe_allow_html=True)

_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;background:#060d1c;}
.block-container{padding:0!important;max-width:100%!important;}
@keyframes pulse-dot{0%,100%{box-shadow:0 0 0 0 rgba(59,130,246,0.6);}50%{box-shadow:0 0 0 6px rgba(59,130,246,0);}}
@keyframes fade-up{from{opacity:0;transform:translateY(18px);}to{opacity:1;transform:translateY(0);}}
@keyframes card-in{from{opacity:0;transform:translateY(22px) scale(0.98);}to{opacity:1;transform:translateY(0) scale(1);}}
@keyframes arrow-nudge{0%,100%{transform:translateX(0);}50%{transform:translateX(4px);}}
.landing-wrap{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:3rem 2rem;
  background:radial-gradient(ellipse 80% 60% at 50% -10%,rgba(37,99,235,0.18) 0%,transparent 70%),
  linear-gradient(160deg,#060d1c 0%,#0d1f45 60%,#081428 100%);}
.landing-wrap::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:radial-gradient(rgba(96,165,250,0.07) 1px,transparent 1px);background-size:28px 28px;}
.landing-badge{position:relative;z-index:1;display:inline-flex;align-items:center;gap:8px;
  background:rgba(37,99,235,0.12);border:1px solid rgba(37,99,235,0.35);border-radius:30px;
  padding:6px 18px;font-size:0.72rem;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;
  color:#93c5fd;margin-bottom:1.8rem;animation:fade-up 0.6s ease both;}
.landing-dot{width:8px;height:8px;border-radius:50%;background:#3b82f6;animation:pulse-dot 2s ease-in-out infinite;}
.landing-title{position:relative;z-index:1;font-size:clamp(2.2rem,5vw,3.2rem);font-weight:700;color:#fff;
  letter-spacing:-0.04em;line-height:1.1;text-align:center;margin:0 0 1rem 0;animation:fade-up 0.65s 0.1s ease both;}
.landing-title span{color:#60a5fa;text-shadow:0 0 40px rgba(96,165,250,0.4);}
.landing-sub{position:relative;z-index:1;font-size:1.05rem;color:rgba(255,255,255,0.42);text-align:center;
  max-width:480px;line-height:1.65;margin:0 auto 3.5rem auto;animation:fade-up 0.65s 0.2s ease both;}
.cards-wrap{position:relative;z-index:1;display:flex;gap:1.5rem;flex-wrap:wrap;justify-content:center;width:100%;max-width:780px;}
.portal-card{flex:1;min-width:300px;max-width:370px;border-radius:22px;padding:2.2rem 2rem 1.8rem;
  cursor:pointer;text-decoration:none!important;
  transition:transform 0.22s ease,box-shadow 0.22s ease,border-color 0.22s ease;}
.portal-card *{text-decoration:none!important;}
.portal-card:hover{transform:translateY(-6px);}
.card-startup{background:linear-gradient(145deg,#0f2557 0%,#1a3a8c 100%);
  border:1px solid rgba(96,165,250,0.2);box-shadow:0 4px 28px rgba(37,99,235,0.18);
  animation:card-in 0.7s 0.25s ease both;}
.card-startup:hover{box-shadow:0 16px 48px rgba(37,99,235,0.38);border-color:rgba(96,165,250,0.55);}
.card-admin{background:linear-gradient(145deg,#1a0a2e 0%,#2d1060 100%);
  border:1px solid rgba(139,92,246,0.2);box-shadow:0 4px 28px rgba(109,40,217,0.15);
  animation:card-in 0.7s 0.35s ease both;}
.card-admin:hover{box-shadow:0 16px 48px rgba(109,40,217,0.32);border-color:rgba(139,92,246,0.55);}
.card-icon{width:50px;height:50px;border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:1.4rem;margin-bottom:1.3rem;}
.icon-startup{background:rgba(59,130,246,0.18);border:1px solid rgba(59,130,246,0.2);}
.icon-admin{background:rgba(139,92,246,0.18);border:1px solid rgba(139,92,246,0.2);}
.card-tag{display:inline-block;font-size:0.64rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;border-radius:20px;padding:3px 10px;margin-bottom:0.65rem;}
.tag-startup{background:rgba(59,130,246,0.15);color:#93c5fd;border:1px solid rgba(59,130,246,0.2);}
.tag-admin{background:rgba(139,92,246,0.15);color:#c4b5fd;border:1px solid rgba(139,92,246,0.2);}
.card-title{font-size:1.25rem;font-weight:700;color:#fff;margin:0 0 0.5rem 0;}
.card-desc{font-size:0.84rem;color:rgba(255,255,255,0.45);line-height:1.6;margin:0 0 1.6rem 0;}
.card-cta{display:inline-flex;align-items:center;gap:8px;font-size:0.82rem;font-weight:600;padding:9px 20px;border-radius:10px;border:none;cursor:pointer;}
.cta-startup{background:linear-gradient(135deg,#1d4ed8,#2563eb);color:#fff;box-shadow:0 2px 12px rgba(37,99,235,0.4);}
.cta-admin{background:linear-gradient(135deg,#6d28d9,#7c3aed);color:#fff;box-shadow:0 2px 12px rgba(109,40,217,0.35);}
.portal-card:hover .card-cta-arrow{animation:arrow-nudge 0.6s ease infinite;}
.landing-footer{position:relative;z-index:1;margin-top:3rem;font-size:0.7rem;color:rgba(255,255,255,0.18);letter-spacing:0.06em;text-align:center;}
.landing-footer a{color:rgba(255,255,255,0.28);text-decoration:none;}
</style>"""

_HTML = """<div class="landing-wrap">
  <div class="landing-badge"><div class="landing-dot"></div>Tunisia's Leading Startup Hub</div>
  <div class="landing-title">Welcome to<br><span>The Dot</span></div>
  <p class="landing-sub">Choisissez votre espace pour continuer.</p>
  <div class="cards-wrap">
    <a href="/Startup" class="portal-card card-startup" target="_self">
      <div class="card-icon icon-startup">&#x1F680;</div>
      <div class="card-tag tag-startup">Front office</div>
      <div class="card-title">Espace Startup</div>
      <p class="card-desc">Completez votre diagnostic en 3 minutes et decouvrez les programmes The Dot adaptes a votre stade de developpement.</p>
      <span class="card-cta cta-startup">Commencer le diagnostic <span class="card-cta-arrow">&#x2192;</span></span>
    </a>
    <a href="/Admin" class="portal-card card-admin" target="_self">
      <div class="card-icon icon-admin">&#x1F510;</div>
      <div class="card-tag tag-admin">Back office</div>
      <div class="card-title">Espace Administration</div>
      <p class="card-desc">Acces reserve aux conseillers The Dot. Consultez les diagnostics, analysez les tendances et gerez les comptes.</p>
      <span class="card-cta cta-admin">Connexion admin <span class="card-cta-arrow">&#x2192;</span></span>
    </a>
  </div>
  <div class="landing-footer">&#169; The Dot &middot; <a href="https://thedot.tn" target="_blank">thedot.tn</a></div>
</div>"""

st.markdown(_CSS + _HTML, unsafe_allow_html=True)
