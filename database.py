"""
database.py — PostgreSQL (Supabase) data layer for The Dot Resource Matcher

Migrated from MySQL to PostgreSQL to support Supabase free-tier hosting.
The public API is identical — same function signatures, same return shapes.

Setup:
  1. Go to Supabase → Settings → Database → Connection string → URI
  2. Copy the URI and set it as DATABASE_URL in your .env file
  3. Run the app — tables are created automatically on first launch
"""

import json
import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

ROLES = ("admin", "viewer")


class DatabaseError(Exception):
    """Wrapped DB error shown cleanly in the UI instead of a raw psycopg2 trace."""
    pass


# ── Connection pool ────────────────────────────────────────────────────────────
_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise DatabaseError(
                "DATABASE_URL is not set. "
                "Copy it from Supabase → Settings → Database → URI and add it to .env"
            )
        try:
            _pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=DATABASE_URL,
                sslmode="require",
            )
        except psycopg2.Error as e:
            raise DatabaseError(f"Cannot connect to database: {e}") from e
    return _pool


@contextmanager
def get_cursor(dictionary: bool = True, commit: bool = False):
    """
    Central context manager for all DB operations.
    Always uses RealDictCursor so rows are accessed as row["column"].
    """
    conn = None
    cursor = None
    try:
        conn = _get_pool().getconn()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cursor
        if commit:
            conn.commit()
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        raise DatabaseError(str(e)) from e
    finally:
        if cursor:
            cursor.close()
        if conn:
            _get_pool().putconn(conn)


# ── Schema ─────────────────────────────────────────────────────────────────────
SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id            SERIAL PRIMARY KEY,
        username      VARCHAR(80)  NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role          VARCHAR(10)  NOT NULL DEFAULT 'viewer'
                      CHECK(role IN ('admin', 'viewer')),
        created_at    TIMESTAMP DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS diagnostics (
        id              SERIAL PRIMARY KEY,
        startup_name    VARCHAR(120),
        sector          VARCHAR(80),
        stage           VARCHAR(40),
        is_diaspora     SMALLINT DEFAULT 0,
        outside_tunis   SMALLINT DEFAULT 0,
        team_size       INT DEFAULT 1,
        has_product     SMALLINT DEFAULT 0,
        has_clients     SMALLINT DEFAULT 0,
        has_revenue     SMALLINT DEFAULT 0,
        is_incorporated SMALLINT DEFAULT 0,
        has_startup_act SMALLINT DEFAULT 0,
        is_ai           SMALLINT DEFAULT 0,
        scores          JSONB,
        needs           JSONB,
        created_at      TIMESTAMP DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recommendations (
        id            SERIAL PRIMARY KEY,
        diagnostic_id INT NOT NULL,
        program_id    VARCHAR(20),
        program_name  VARCHAR(120),
        score         FLOAT,
        priority      VARCHAR(30),
        reasons       JSONB,
        FOREIGN KEY (diagnostic_id) REFERENCES diagnostics(id) ON DELETE CASCADE
    )
    """,
]

_schema_initialized = False


def init_db(force: bool = False):
    """Create tables if they don't exist. Idempotent."""
    global _schema_initialized
    if _schema_initialized and not force:
        return
    with get_cursor(commit=True) as cursor:
        for statement in SCHEMA_STATEMENTS:
            cursor.execute(statement)
    _schema_initialized = True


# ── Users ──────────────────────────────────────────────────────────────────────
def get_user(username: str):
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        return cursor.fetchone()


def create_user(username: str, password_hash: str, role: str = "viewer") -> bool:
    if role not in ROLES:
        raise ValueError(f"Invalid role: {role!r}. Expected one of {ROLES}.")
    try:
        with get_cursor(commit=True) as cursor:
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                (username, password_hash, role),
            )
        return True
    except DatabaseError as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            return False
        raise


def list_users():
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT id, username, role, created_at FROM users ORDER BY created_at DESC"
        )
        return cursor.fetchall()


def count_admins() -> int:
    with get_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'admin'")
        return int(cursor.fetchone()["total"] or 0)


def delete_user(user_id: int):
    with get_cursor() as cursor:
        cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        target = cursor.fetchone()
        if target is None:
            return
        if target["role"] == "admin":
            cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'admin'")
            if int(cursor.fetchone()["total"] or 0) <= 1:
                raise ValueError("Cannot delete the last admin account.")

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
            RETURNING id
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
        diag_id = cursor.fetchone()["id"]

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
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return {}


def _parse_list(raw) -> list:
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return []
    return []


def get_all_diagnostics():
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, startup_name, sector, stage, is_diaspora, outside_tunis,
                   team_size, has_product, has_clients, has_revenue,
                   is_incorporated, has_startup_act, is_ai, scores, needs, created_at
            FROM diagnostics
            ORDER BY created_at DESC
            """
        )
        rows = [dict(r) for r in cursor.fetchall()]

    for row in rows:
        row["scores"] = _parse_scores(row["scores"])
        row["needs"]  = _parse_list(row["needs"])
    return rows


def get_diagnostic_with_recs(diag_id: int):
    with get_cursor() as cursor:
        cursor.execute("SELECT * FROM diagnostics WHERE id = %s", (diag_id,))
        diag = cursor.fetchone()
        if not diag:
            return None
        diag = dict(diag)
        diag["scores"] = _parse_scores(diag["scores"])
        diag["needs"]  = _parse_list(diag["needs"])

        cursor.execute(
            "SELECT * FROM recommendations WHERE diagnostic_id = %s ORDER BY score DESC",
            (diag_id,),
        )
        recs = [dict(r) for r in cursor.fetchall()]
        for r in recs:
            r["reasons"] = _parse_list(r["reasons"])

        diag["recommendations"] = recs
        return diag


def delete_diagnostic(diag_id: int):
    with get_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM diagnostics WHERE id = %s", (diag_id,))


# ── Stats ──────────────────────────────────────────────────────────────────────
def get_stats() -> dict:
    stats = {}
    dims = ["Team", "Legal", "Product", "Traction", "Funding", "Market", "Branding"]

    with get_cursor() as cursor:
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

        # PostgreSQL date functions (replaces MySQL DATE_FORMAT / DATE_SUB)
        cursor.execute(
            """
            SELECT TO_CHAR(created_at, 'YYYY-MM') AS month, COUNT(*) AS count
            FROM diagnostics
            WHERE created_at >= NOW() - INTERVAL '12 months'
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
                ROUND((AVG(has_product)     * 100)::NUMERIC, 1) AS pct_product,
                ROUND((AVG(has_clients)     * 100)::NUMERIC, 1) AS pct_clients,
                ROUND((AVG(has_revenue)     * 100)::NUMERIC, 1) AS pct_revenue,
                ROUND((AVG(is_incorporated) * 100)::NUMERIC, 1) AS pct_incorporated,
                ROUND((AVG(has_startup_act) * 100)::NUMERIC, 1) AS pct_startup_act,
                ROUND((AVG(is_diaspora)     * 100)::NUMERIC, 1) AS pct_diaspora
            FROM diagnostics
            """
        )
        raw_pct = cursor.fetchone()
        stats["percentages"] = (
            {k: float(v or 0) for k, v in raw_pct.items()} if raw_pct else {}
        )

    return stats
