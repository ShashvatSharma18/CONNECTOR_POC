import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "chat_history.sqlite3"


class ChatHistoryDB:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    rich_cards TEXT,
                    sources_accessed TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id);"
            )
            # Add summary_block and suggested_followups columns if missing
            try:
                conn.execute("ALTER TABLE chat_messages ADD COLUMN summary_block TEXT;")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE chat_messages ADD COLUMN suggested_followups TEXT;")
            except Exception:
                pass
            conn.commit()

    def create_session(self, title: str = "New Chat") -> dict[str, Any]:
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO chat_sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, title, now, now),
            )
            conn.commit()
        return {
            "id": session_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
        }

    def list_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT s.id, s.title, s.created_at, s.updated_at,
                       COUNT(m.id) as message_count
                FROM chat_sessions s
                LEFT JOIN chat_messages m ON s.id = m.session_id
                GROUP BY s.id
                ORDER BY s.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._get_connection() as conn:
            session = conn.execute(
                "SELECT * FROM chat_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if not session:
                return None

            messages = conn.execute(
                "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()

            parsed_messages = []
            for m in messages:
                msg_dict = dict(m)
                if msg_dict.get("rich_cards"):
                    try:
                        msg_dict["rich_cards"] = json.loads(msg_dict["rich_cards"])
                    except Exception:
                        msg_dict["rich_cards"] = []
                else:
                    msg_dict["rich_cards"] = []

                if msg_dict.get("sources_accessed"):
                    try:
                        msg_dict["sources_accessed"] = json.loads(msg_dict["sources_accessed"])
                    except Exception:
                        msg_dict["sources_accessed"] = []
                else:
                    msg_dict["sources_accessed"] = []

                if msg_dict.get("summary_block"):
                    try:
                        msg_dict["summary_block"] = json.loads(msg_dict["summary_block"])
                    except Exception:
                        msg_dict["summary_block"] = None
                else:
                    msg_dict["summary_block"] = None

                if msg_dict.get("suggested_followups"):
                    try:
                        msg_dict["suggested_followups"] = json.loads(msg_dict["suggested_followups"])
                    except Exception:
                        msg_dict["suggested_followups"] = []
                else:
                    msg_dict["suggested_followups"] = []

                parsed_messages.append(msg_dict)

            res = dict(session)
            res["messages"] = parsed_messages
            return res

    def update_session_title(self, session_id: str, title: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cur = conn.execute(
                "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, now, session_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def delete_session(self, session_id: str) -> bool:
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            conn.commit()
            return cur.rowcount > 0

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        rich_cards: list[dict[str, Any]] | None = None,
        sources_accessed: list[dict[str, Any]] | None = None,
        msg_id: str | None = None,
        summary_block: dict[str, Any] | None = None,
        suggested_followups: list[str] | None = None,
    ) -> dict[str, Any]:
        message_id = msg_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        time_str = datetime.now(timezone.utc).strftime("%I:%M %p")

        cards_json = json.dumps(rich_cards) if rich_cards else None
        sources_json = json.dumps(sources_accessed) if sources_accessed else None
        summary_json = json.dumps(summary_block) if summary_block else None
        followups_json = json.dumps(suggested_followups) if suggested_followups else None

        with self._get_connection() as conn:
            # Touch session updated_at
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
            conn.execute(
                """
                INSERT INTO chat_messages (id, session_id, role, content, rich_cards, sources_accessed, summary_block, suggested_followups, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (message_id, session_id, role, content, cards_json, sources_json, summary_json, followups_json, time_str, now),
            )
            conn.commit()

        return {
            "id": message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "rich_cards": rich_cards or [],
            "sources_accessed": sources_accessed or [],
            "summary_block": summary_block,
            "suggested_followups": suggested_followups or [],
            "timestamp": time_str,
            "created_at": now,
        }


db = ChatHistoryDB()
