"""
database.py — Couche d'accès MySQL pour The Dot Resource Matcher
Gère : connexion, initialisation du schéma, CRUD diagnostics, utilisateurs

Améliorations apportées :
  - Connexions ouvertes/fermées via un context manager (`with get_cursor() as cursor`),
    qui garantit la fermeture même en cas d'exception (avant : risque de connexions
    MySQL non fermées si une erreur survenait entre l'ouverture et le close()).
  - init_db() ne s'exécute plus qu'une seule fois par process (avant : ré-exécutée à
    chaque rerun Streamlit via bootstrap_admin(), donc à chaque clic).
  - Le schéma SQL est découpé en instructions explicites plutôt que par split(";"),
    ce qui évite qu'un futur ";" dans une donnée ne casse l'initialisation.
  - Toutes les fonctions exposent désormais les erreurs MySQL sous forme de
    DatabaseError (exception dédiée), que l'UI peut intercepter pour afficher un
    message propre au lieu de crasher l'application.
  - delete_user() refuse désormais de supprimer le dernier compte admin restant.
  - ROLES centralise les rôles valides (au lieu de les dupliquer entre le schéma
    SQL et les composants d'UI).
"""

import json
import os
from contextlib import contextmanager
from datetime import datetime

import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()

# ── Configuration connexion ────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "dot_matcher"),
}

# Rôles valides — référencés à la fois par le schéma SQL et par l'UI,
# pour éviter toute désynchronisation entre les deux.
ROLES = ("admin", "viewer")


class DatabaseError(Exception):
    """Erreur d'accès à la base, destinée à être affichée proprement par l'UI
    plutôt que de remonter une trace MySQL brute jusqu'à l'utilisateur final."""
    pass


# ── Pool de connexions ─────────────────────────────────────────────────────────
# Un pool évite d'ouvrir une connexion TCP neuve à chaque requête (ce qui était
# le cas avant : get_connection() était appelée — et donc une nouvelle connexion
# créée — dans chacune des ~15 fonctions de ce module). Le pool est initialisé
# une seule fois et réutilisé pour toute la durée de vie du process Streamlit.
_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        try:
            _pool = pooling.MySQLConnectionPool(
                pool_name="dot_matcher_pool",
                pool_size=5,
                **DB_CONFIG,
            )
        except mysql.connector.Error as e:
            raise DatabaseError(f"Impossible de joindre la base de données : {e}") from e
    return _pool


@contextmanager
def get_cursor(dictionary: bool = False, commit: bool = False):
    """
    Context manager central pour toute interaction avec la base.
    Garantit la fermeture du curseur et de la connexion même en cas d'exception,
    et convertit les erreurs MySQL en DatabaseError exploitable par l'UI.

    Usage :
        with get_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cursor.fetchone()
    """
    conn = None
    cursor = None
    try:
        conn = _get_pool().get_connection()
        cursor = conn.cursor(dictionary=dictionary)
        yield cursor
        if commit:
            conn.commit()
    except mysql.connector.Error as e:
        if conn is not None:
            conn.rollback()
        raise DatabaseError(str(e)) from e
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


# ── Initialisation du schéma ───────────────────────────────────────────────────
# Découpé en instructions explicites plutôt que str.split(";") sur un bloc unique :
# un ";" dans une valeur par défaut ou un futur commentaire ne casse plus le script.
SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        username      VARCHAR(80)  NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role          ENUM('admin', 'viewer') NOT NULL DEFAULT 'viewer',
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS diagnostics (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        startup_name    VARCHAR(120),
        sector          VARCHAR(80),
        stage           VARCHAR(40),
        is_diaspora     TINYINT(1) DEFAULT 0,
        outside_tunis   TINYINT(1) DEFAULT 0,
        team_size       INT DEFAULT 1,
        has_product     TINYINT(1) DEFAULT 0,
        has_clients     TINYINT(1) DEFAULT 0,
        has_revenue     TINYINT(1) DEFAULT 0,
        is_incorporated TINYINT(1) DEFAULT 0,
        has_startup_act TINYINT(1) DEFAULT 0,
        is_ai           TINYINT(1) DEFAULT 0,
        scores          JSON,
        needs           JSON,
        created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recommendations (
        id            INT AUTO_INCREMENT PRIMARY KEY,
        diagnostic_id INT NOT NULL,
        program_id    VARCHAR(20),
        program_name  VARCHAR(120),
        score         FLOAT,
        priority      VARCHAR(30),
        reasons       JSON,
        FOREIGN KEY (diagnostic_id) REFERENCES diagnostics(id) ON DELETE CASCADE
    )
    """,
]

# Garde-fou process-local : évite de ré-exécuter CREATE TABLE IF NOT EXISTS à
# chaque rerun Streamlit (bootstrap_admin() est appelée à chaque interaction).
_schema_initialized = False


def init_db(force: bool = False):
    """Crée les tables si elles n'existent pas. Idempotent côté SQL (IF NOT EXISTS),
    mais on évite quand même de refaire l'aller-retour réseau à chaque clic."""
    global _schema_initialized
    if _schema_initialized and not force:
        return
    with get_cursor(commit=True) as cursor:
        for statement in SCHEMA_STATEMENTS:
            cursor.execute(statement)
    _schema_initialized = True


# ── Utilisateurs ───────────────────────────────────────────────────────────────
def get_user(username: str):
    with get_cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        return cursor.fetchone()


def create_user(username: str, password_hash: str, role: str = "viewer") -> bool:
    if role not in ROLES:
        raise ValueError(f"Rôle invalide : {role!r}. Attendu l'un de {ROLES}.")
    try:
        with get_cursor(commit=True) as cursor:
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                (username, password_hash, role),
            )
        return True
    except DatabaseError as e:
        # Conflit d'unicité sur username (le plus probable) -> on signale juste
        # un échec de création, sans remonter le détail SQL à l'UI.
        if "Duplicate entry" in str(e):
            return False
        raise


def list_users():
    with get_cursor(dictionary=True) as cursor:
        cursor.execute(
            "SELECT id, username, role, created_at FROM users ORDER BY created_at DESC"
        )
        return cursor.fetchall()


def count_admins() -> int:
    with get_cursor(dictionary=True) as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'admin'")
        return int(cursor.fetchone()["total"] or 0)


def delete_user(user_id: int):
    """Supprime un compte, sauf s'il s'agit du dernier administrateur restant —
    ce qui bloquerait définitivement l'accès au dashboard d'administration."""
    with get_cursor(dictionary=True) as cursor:
        cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        target = cursor.fetchone()
        if target is None:
            return  # déjà supprimé / inexistant : rien à faire

        if target["role"] == "admin":
            cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'admin'")
            if int(cursor.fetchone()["total"] or 0) <= 1:
                raise ValueError(
                    "Impossible de supprimer le dernier compte administrateur."
                )

    with get_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))


# ── Diagnostics ────────────────────────────────────────────────────────────────
def save_diagnostic(profile: dict, scores: dict, needs: list, recommendations: list) -> int:
    with get_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO diagnostics
                (startup_name, sector, stage, is_diaspora, outside_tunis,
                 team_size, has_product, has_clients, has_revenue,
                 is_incorporated, has_startup_act, is_ai, scores, needs)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                profile.get("startup_name", ""),
                profile.get("sector", ""),
                profile.get("stage", ""),
                int(profile.get("is_diaspora", False)),
                int(profile.get("outside_tunis", False)),
                profile.get("team_size", 1),
                int(profile.get("has_product", False)),
                int(profile.get("has_clients", False)),
                int(profile.get("has_revenue", False)),
                int(profile.get("is_incorporated", False)),
                int(profile.get("has_startup_act", False)),
                int(profile.get("is_ai", False)),
                json.dumps(scores),
                json.dumps(needs),
            ),
        )
        diag_id = cursor.lastrowid

        for rec in recommendations:
            cursor.execute(
                """
                INSERT INTO recommendations
                    (diagnostic_id, program_id, program_name, score, priority, reasons)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (
                    diag_id,
                    rec.get("id", ""),
                    rec.get("name", ""),
                    rec.get("score", 0),
                    rec.get("priority", ""),
                    json.dumps(rec.get("reasons", [])),
                ),
            )

    return diag_id


def _parse_scores(raw) -> dict:
    """Normalise les scores JSON — gère str, dict, et None."""
    if raw is None:
        return {}
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
    if isinstance(raw, dict):
        return raw
    return {}


def _parse_list(raw) -> list:
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(raw, list):
        return raw
    return []


def get_all_diagnostics():
    with get_cursor(dictionary=True) as cursor:
        cursor.execute(
            """
            SELECT id, startup_name, sector, stage, is_diaspora, outside_tunis,
                   team_size, has_product, has_clients, has_revenue,
                   is_incorporated, has_startup_act, is_ai, scores, needs, created_at
            FROM diagnostics
            ORDER BY created_at DESC
            """
        )
        rows = cursor.fetchall()

    for row in rows:
        row["scores"] = _parse_scores(row["scores"])
        row["needs"] = _parse_list(row["needs"])
    return rows


def get_diagnostic_with_recs(diag_id: int):
    with get_cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM diagnostics WHERE id = %s", (diag_id,))
        diag = cursor.fetchone()
        if not diag:
            return None

        diag["scores"] = _parse_scores(diag["scores"])
        diag["needs"] = _parse_list(diag["needs"])

        cursor.execute(
            "SELECT * FROM recommendations WHERE diagnostic_id = %s ORDER BY score DESC",
            (diag_id,),
        )
        recs = cursor.fetchall()
        for r in recs:
            r["reasons"] = _parse_list(r["reasons"])

        diag["recommendations"] = recs
        return diag


def delete_diagnostic(diag_id: int):
    with get_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM diagnostics WHERE id = %s", (diag_id,))


# ── Statistiques agrégées ──────────────────────────────────────────────────────
def get_stats() -> dict:
    stats = {}
    dims = ["Team", "Legal", "Product", "Traction", "Funding", "Market", "Branding"]

    with get_cursor(dictionary=True) as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM diagnostics")
        stats["total_diagnostics"] = int(cursor.fetchone()["total"] or 0)

        cursor.execute("SELECT COUNT(DISTINCT startup_name) AS total FROM diagnostics")
        stats["unique_startups"] = int(cursor.fetchone()["total"] or 0)

        cursor.execute(
            """
            SELECT stage, COUNT(*) AS count
            FROM diagnostics
            GROUP BY stage
            ORDER BY count DESC
            """
        )
        stats["by_stage"] = [
            {"stage": r["stage"], "count": int(r["count"])} for r in cursor.fetchall()
        ]

        cursor.execute(
            """
            SELECT sector, COUNT(*) AS count
            FROM diagnostics
            WHERE sector IS NOT NULL AND sector != ''
            GROUP BY sector
            ORDER BY count DESC
            LIMIT 8
            """
        )
        stats["by_sector"] = [
            {"sector": r["sector"], "count": int(r["count"])} for r in cursor.fetchall()
        ]

        cursor.execute(
            """
            SELECT program_name, COUNT(*) AS count, AVG(score) AS avg_score
            FROM recommendations
            GROUP BY program_name
            ORDER BY count DESC
            """
        )
        stats["top_programs"] = [
            {
                "program_name": r["program_name"],
                "count": int(r["count"]),
                "avg_score": float(r["avg_score"] or 0),
            }
            for r in cursor.fetchall()
        ]

        # ── Maturité moyenne — clés en majuscules dans la DB ──────────────
        cursor.execute("SELECT scores FROM diagnostics")
        all_score_rows = cursor.fetchall()
        if all_score_rows:
            totals = {d: 0.0 for d in dims}
            count = 0
            for row in all_score_rows:
                s = _parse_scores(row["scores"])
                if s:
                    for d in dims:
                        totals[d] += float(s.get(d, 0) or 0)
                    count += 1
            stats["avg_scores"] = {
                d: round(totals[d] / count, 1) if count else 0 for d in dims
            }
        else:
            stats["avg_scores"] = {}

        cursor.execute(
            """
            SELECT DATE_FORMAT(created_at, '%%Y-%%m') AS month, COUNT(*) AS count
            FROM diagnostics
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
            GROUP BY month
            ORDER BY month ASC
            """
        )
        stats["monthly_trend"] = [
            {"month": str(r["month"]), "count": int(r["count"])}
            for r in cursor.fetchall()
        ]

        cursor.execute(
            """
            SELECT
                ROUND(AVG(has_product)     * 100, 1) AS pct_product,
                ROUND(AVG(has_clients)     * 100, 1) AS pct_clients,
                ROUND(AVG(has_revenue)     * 100, 1) AS pct_revenue,
                ROUND(AVG(is_incorporated) * 100, 1) AS pct_incorporated,
                ROUND(AVG(has_startup_act) * 100, 1) AS pct_startup_act,
                ROUND(AVG(is_diaspora)     * 100, 1) AS pct_diaspora
            FROM diagnostics
            """
        )
        raw_pct = cursor.fetchone()
        stats["percentages"] = (
            {k: float(v or 0) for k, v in raw_pct.items()} if raw_pct else {}
        )

    return stats