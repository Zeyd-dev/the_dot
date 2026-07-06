"""
auth.py — Authentification pour The Dot Resource Matcher
Login multi-comptes, passwords hashés bcrypt, sessions Streamlit

Améliorations apportées :
  - bootstrap_admin() ne réinitialise plus le schéma à chaque rerun Streamlit
    (délégué à init_db(), désormais idempotent côté database.py).
  - login_page() limite le nombre de tentatives de connexion par session
    (avant : aucune limite, un script pouvait tester des mots de passe en boucle).
  - Toute erreur de connexion à la base (DatabaseError) est interceptée et
    affichée comme un message utilisateur clair, au lieu de faire crasher l'app
    avec une trace MySQL brute.
  - user_management_ui() relaie désormais le message d'erreur explicite quand on
    tente de supprimer le dernier compte admin, au lieu de planter silencieusement.
  - Le mot de passe administrateur par défaut est lu depuis la variable
    d'environnement ADMIN_PASSWORD (fichier .env). La valeur "thedot2026" n'est
    plus écrite en dur dans le code source — elle sert uniquement de fallback
    si la variable n'est pas définie, et doit être changée avant tout déploiement.
"""

import os

import bcrypt
import streamlit as st

from database import (
    DatabaseError,
    ROLES,
    create_user,
    delete_user,
    get_user,
    init_db,
    list_users,
)

# Nombre de tentatives de connexion ratées autorisées avant blocage temporaire
# de la session (protection basique contre le brute-force sur le formulaire).
MAX_LOGIN_ATTEMPTS = 5

# Mot de passe du compte admin créé au démarrage.
# Lire depuis l'environnement pour ne pas exposer de secret dans le code source.
# Définir ADMIN_PASSWORD dans le fichier .env avant tout déploiement réel.
_DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "thedot2026")


# ── Hashing ────────────────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── Bootstrap : créer le compte admin par défaut s'il n'existe pas ─────────────
def bootstrap_admin():
    """
    Appelé au démarrage de l'app, à chaque rerun Streamlit.
    Crée un compte admin par défaut si la table users est vide.
    Credentials par défaut : admin / thedot2026
    → POC interne : mot de passe laissé en dur volontairement à ce stade.
    """
    try:
        init_db()
        if not get_user("admin"):
            create_user("admin", hash_password(_DEFAULT_ADMIN_PASSWORD), role="admin")
    except DatabaseError as e:
        st.error(
            "⚠️ Impossible de joindre la base de données. "
            "Vérifiez que MySQL est démarré et accessible."
        )
        st.caption(f"Détail technique : {e}")
        st.stop()


# ── Session helpers ────────────────────────────────────────────────────────────
def is_logged_in() -> bool:
    return st.session_state.get("auth_user") is not None


def current_user() -> dict | None:
    return st.session_state.get("auth_user")


def is_admin() -> bool:
    u = current_user()
    return u is not None and u.get("role") == "admin"


def logout():
    st.session_state.pop("auth_user", None)
    st.session_state.pop("login_attempts", None)


def login_page():
    """
    Renders the login form and handles authentication.

    Layout fixes:
      - padding-top: 15vh so the form is vertically centred on the viewport.
      - max-width: 420px, centred.
      - Title restored to ## 🔐 Accès Admin.

    Ghost-widget fix:
      - All form widgets live inside a single st.empty() placeholder.
      - On successful login the placeholder is cleared with placeholder.empty()
        BEFORE st.rerun() fires, so the form never flashes on the dashboard.
      - Login errors are stored in session_state["_login_error"] and read on
        the next render, which lets us rerun cleanly without inline st.error()
        calls that would persist after the form is cleared.

    Back link:
      - Rendered as the first element inside the placeholder (above the form).
    """
    # Vertically centred, narrow column layout for the login card.
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 420px !important;
            margin: 0 auto !important;
            padding-top: 15vh !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    attempts    = st.session_state.get("login_attempts", 0)
    login_error = st.session_state.pop("_login_error", None)

    # All widgets in one placeholder so we can wipe them on successful login.
    placeholder = st.empty()

    with placeholder.container():
        # Back link — always above the form.
        st.markdown(
            "<a href='/' target='_self' "
            "style='font-size:0.78rem;color:#94a3b8;text-decoration:none;'>"
            "← Retour à l'accueil</a>",
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("## 🔐 Accès Admin")
        st.markdown("---")

        if attempts >= MAX_LOGIN_ATTEMPTS:
            st.error(
                "🔒 Trop de tentatives échouées. "
                "Rechargez la page après quelques minutes pour réessayer."
            )
            st.caption("Accès réservé aux conseillers The Dot.")
            return

        if login_error:
            st.error(login_error)

        username      = st.text_input("Nom d'utilisateur", placeholder="admin")
        password      = st.text_input("Mot de passe", type="password", placeholder="••••••••")
        login_clicked = st.button("Se connecter", use_container_width=True, type="primary")
        st.markdown("---")
        st.caption("Accès réservé aux conseillers The Dot.")

    # ── Handle click outside the container so we can clear it on success ──────
    if not login_clicked:
        return

    try:
        user = get_user(username)
    except DatabaseError as e:
        st.session_state["_login_error"] = (
            f"⚠️ Erreur de connexion à la base de données. Réessayez plus tard. ({e})"
        )
        st.rerun()
        return

    if user and check_password(password, user["password_hash"]):
        # Wipe the form before rerunning so it never appears on the dashboard.
        placeholder.empty()
        st.session_state["auth_user"] = {
            "id":       user["id"],
            "username": user["username"],
            "role":     user["role"],
        }
        st.session_state["login_attempts"] = 0
        st.rerun()
    else:
        st.session_state["login_attempts"] = attempts + 1
        remaining = MAX_LOGIN_ATTEMPTS - st.session_state["login_attempts"]
        st.session_state["_login_error"] = (
            f"Identifiants incorrects. ({remaining} tentative(s) restante(s))"
            if remaining > 0
            else "Identifiants incorrects. Accès temporairement bloqué."
        )
        st.rerun()

# ── UI de gestion des comptes (admin only) ─────────────────────────────────────
def user_management_ui():
    """Section du dashboard pour créer / supprimer des comptes."""
    st.subheader("👥 Gestion des comptes")

    # Créer un compte
    with st.expander("➕ Créer un nouveau compte", expanded=False):
        new_user = st.text_input("Nom d'utilisateur", key="new_username")
        new_pass = st.text_input("Mot de passe", type="password", key="new_password")
        new_role = st.selectbox("Rôle", list(ROLES), key="new_role")
        if st.button("Créer le compte", key="btn_create_user"):
            if new_user and new_pass:
                try:
                    ok = create_user(new_user, hash_password(new_pass), role=new_role)
                    if ok:
                        st.success(f"Compte **{new_user}** créé avec le rôle *{new_role}*.")
                    else:
                        st.error("Ce nom d'utilisateur existe déjà.")
                except DatabaseError as e:
                    st.error("⚠️ Erreur lors de la création du compte.")
                    st.caption(f"Détail technique : {e}")
            else:
                st.warning("Remplissez tous les champs.")

    # Liste des comptes
    try:
        users = list_users()
    except DatabaseError as e:
        st.error("⚠️ Impossible de charger la liste des comptes.")
        st.caption(f"Détail technique : {e}")
        return

    if users:
        st.markdown(f"**{len(users)} compte(s) enregistré(s)**")
        for u in users:
            c1, c2, c3, c4 = st.columns([2, 1.5, 2, 1])
            c1.write(f"**{u['username']}**")
            c2.write(u["role"])
            c3.write(str(u["created_at"])[:10])
            # Ne pas supprimer son propre compte ni le dernier admin
            me = current_user()
            if u["username"] != me["username"]:
                if c4.button("🗑️", key=f"del_user_{u['id']}"):
                    try:
                        delete_user(u["id"])
                        st.rerun()
                    except ValueError as e:
                        # Levée par delete_user() si c'est le dernier admin restant
                        st.error(str(e))
                    except DatabaseError as e:
                        st.error("⚠️ Erreur lors de la suppression du compte.")
                        st.caption(f"Détail technique : {e}")
            else:
                c4.write("*(vous)*")