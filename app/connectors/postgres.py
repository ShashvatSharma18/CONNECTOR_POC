import logging
import os
import re
import sqlite3
from typing import Any
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()
logger = logging.getLogger(__name__)


class DatabaseConnector:
    """Read-only relational database connector supporting SQLite and PostgreSQL URLs."""

    def __init__(self, db_url: str | None = None):
        self.db_url = (db_url or os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL") or "").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.db_url)

    def _get_connection(self):
        if not self.is_configured:
            # Fallback to local application SQLite database if unconfigured
            fallback_path = os.path.join(os.getcwd(), "data", "chat_history.db")
            if os.path.exists(fallback_path):
                return sqlite3.connect(fallback_path)
            raise HTTPException(500, "Database connector is not configured. Missing POSTGRES_URL.")

        url = self.db_url
        if url.startswith("sqlite:///") or url.endswith(".db") or url.endswith(".sqlite3") or os.path.exists(url):
            clean_path = url.replace("sqlite:///", "")
            return sqlite3.connect(clean_path)

        # For PostgreSQL URL (postgresql://user:pass@host:port/dbname)
        try:
            import psycopg2
            return psycopg2.connect(url)
        except ImportError:
            # If psycopg2 is not installed, return structured error
            raise HTTPException(
                500,
                "psycopg2 package is not installed. To connect to PostgreSQL, install psycopg2-binary or use a SQLite database.",
            )

    def get_status(self) -> dict[str, Any]:
        """Test database connection and return schema summary."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            return {
                "configured": True,
                "authenticated": True,
                "database_type": "SQLite" if not self.db_url.startswith("postgres") else "PostgreSQL",
                "table_count": len(tables),
                "tables": tables,
                "db_target": os.path.basename(self.db_url) if self.db_url else "local-db",
            }
        except Exception as exc:
            return {"configured": False, "authenticated": False, "error": str(exc)}

    def list_tables(self) -> list[str]:
        """List all user tables in the database."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def describe_table(self, table_name: str) -> list[dict[str, Any]]:
        """Return column names and types for a given table."""
        # Sanitize table name to prevent SQL injection
        if not re.match(r"^[A-Za-z0-9_]+$", table_name):
            raise HTTPException(400, "Invalid table name.")

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name});")
            cols = []
            for row in cursor.fetchall():
                cols.append({
                    "cid": row[0],
                    "name": row[1],
                    "type": row[2],
                    "notnull": bool(row[3]),
                    "default_value": row[4],
                    "pk": bool(row[5]),
                })
            return cols
        finally:
            conn.close()

    def execute_read_query(self, sql_query: str, limit: int = 50) -> dict[str, Any]:
        """Execute a strictly READ-ONLY SELECT query and return rows as dicts."""
        clean = sql_query.strip().rstrip(";")
        # Enforce read-only constraint
        forbidden = [r"\binsert\b", r"\bupdate\b", r"\bdelete\b", r"\bdrop\b", r"\balter\b", r"\bcreate\b", r"\btruncate\b", r"\bgrant\b", r"\brevoke\b"]
        for pattern in forbidden:
            if re.search(pattern, clean, re.I):
                raise HTTPException(400, f"Dangerous or modifying statement rejected: query must be strictly read-only SELECT.")

        if not re.match(r"^\s*SELECT\b", clean, re.I):
            raise HTTPException(400, "Only SELECT queries are supported.")

        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute(f"{clean} LIMIT {limit};")
            rows = cursor.fetchall()
            dict_rows = [dict(r) for r in rows]
            cols = list(dict_rows[0].keys()) if dict_rows else []
            return {
                "columns": cols,
                "row_count": len(dict_rows),
                "rows": dict_rows,
            }
        except Exception as exc:
            raise HTTPException(400, f"Database query error: {str(exc)}")
        finally:
            conn.close()


def get_database_connector() -> DatabaseConnector:
    return DatabaseConnector()
