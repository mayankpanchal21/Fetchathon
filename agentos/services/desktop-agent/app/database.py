import json
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from .config import settings

logger = logging.getLogger("agentos.database")


class TaskDatabase:
    def __init__(self, db_path=None):
        self.db_path = str(db_path or settings.db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    user_request TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requires_approval BOOLEAN DEFAULT 0,
                    current_step_index INTEGER DEFAULT 0,
                    steps_json TEXT NOT NULL,
                    logs_json TEXT NOT NULL,
                    verification_result TEXT,
                    error_details TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def save_task(self, task_dict: Dict[str, Any]):
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO tasks (
                    task_id, user_request, goal, status, requires_approval,
                    current_step_index, steps_json, logs_json, verification_result,
                    error_details, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    status=excluded.status,
                    requires_approval=excluded.requires_approval,
                    current_step_index=excluded.current_step_index,
                    steps_json=excluded.steps_json,
                    logs_json=excluded.logs_json,
                    verification_result=excluded.verification_result,
                    error_details=excluded.error_details,
                    updated_at=excluded.updated_at
            """, (
                task_dict["task_id"],
                task_dict["user_request"],
                task_dict["goal"],
                task_dict["status"],
                1 if task_dict.get("requires_approval") else 0,
                task_dict.get("current_step_index", 0),
                json.dumps(task_dict.get("steps", [])),
                json.dumps(task_dict.get("logs", [])),
                json.dumps(task_dict.get("verification_result", {})) if task_dict.get("verification_result") else None,
                task_dict.get("error_details"),
                task_dict.get("created_at", now),
                now
            ))
            conn.commit()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "task_id": row["task_id"],
                "user_request": row["user_request"],
                "goal": row["goal"],
                "status": row["status"],
                "requires_approval": bool(row["requires_approval"]),
                "current_step_index": row["current_step_index"],
                "steps": json.loads(row["steps_json"]),
                "logs": json.loads(row["logs_json"]),
                "verification_result": json.loads(row["verification_result"]) if row["verification_result"] else None,
                "error_details": row["error_details"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }

    def list_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            rows = cur.fetchall()
            tasks = []
            for row in rows:
                tasks.append({
                    "task_id": row["task_id"],
                    "user_request": row["user_request"],
                    "goal": row["goal"],
                    "status": row["status"],
                    "requires_approval": bool(row["requires_approval"]),
                    "current_step_index": row["current_step_index"],
                    "steps": json.loads(row["steps_json"]),
                    "logs": json.loads(row["logs_json"]),
                    "verification_result": json.loads(row["verification_result"]) if row["verification_result"] else None,
                    "error_details": row["error_details"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })
            return tasks


db = TaskDatabase()
