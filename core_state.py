import sqlite3
import json
import uuid
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [CORE] - %(levelname)s - %(message)s")

class CoreStateEngine:
    """Candidate persistent state engine. Provider claims never equal verification."""

    def __init__(self, db_path: str = "multiverse_core.db"):
        self.db_path = db_path
        self._init_db()

    def _get_time(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    troop TEXT,
                    claimed_revenue INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'QUEUED',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    result TEXT,
                    result_provider TEXT,
                    verification_note TEXT
                )""")
                conn.execute("""CREATE TABLE IF NOT EXISTS revenues (
                    id TEXT PRIMARY KEY,
                    amount INTEGER NOT NULL,
                    source_task_id TEXT NOT NULL UNIQUE,
                    timestamp TEXT NOT NULL
                )""")
                conn.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    payload JSON,
                    timestamp TEXT NOT NULL
                )""")
            self.log_audit("SYSTEM_START", {"message":"CoreStateEngine booted"})
        except Exception as exc:
            logging.critical("Database initialization failed: %s", exc)
            raise SystemExit("System Halted due to Critical State Failure.")

    def log_audit(self, event_type: str, payload: dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO audit_logs (id,event_type,payload,timestamp) VALUES (?,?,?,?)",
                         (str(uuid.uuid4()), event_type, json.dumps(payload), self._get_time()))

    def add_task(self, title: str, troop: str, revenue: int = 0) -> str | None:
        task_id=f"task_{uuid.uuid4().hex[:12]}"
        now=self._get_time()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""INSERT INTO tasks
                    (id,title,troop,claimed_revenue,status,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?)""",
                    (task_id,title,troop,revenue,"QUEUED",now,now))
            self.log_audit("TASK_ADDED",{"task_id":task_id,"title":title,"troop":troop})
            return task_id
        except Exception as exc:
            logging.error("Task addition failed: %s", exc)
            return None

    def record_task_claim(self, task_id: str, result: str, provider_id: str) -> bool:
        now=self._get_time()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur=conn.execute("""UPDATE tasks SET status='SUCCESS_CLAIMED',result=?,result_provider=?,updated_at=?
                    WHERE id=? AND status='RUNNING'""",(result,provider_id,now,task_id))
                if cur.rowcount != 1:
                    return False
            self.log_audit("TASK_RESULT_CLAIMED",{"task_id":task_id,"provider_id":provider_id})
            return True
        except Exception as exc:
            logging.error("Task claim recording failed: %s", exc)
            return False

    def verify_task(self, task_id: str, verification_note: str) -> bool:
        """Records verification only. Does not realize money."""
        now=self._get_time()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur=conn.execute("""UPDATE tasks SET status='VERIFIED',verification_note=?,updated_at=?
                    WHERE id=? AND status='SUCCESS_CLAIMED'""",(verification_note,now,task_id))
                if cur.rowcount != 1:
                    return False
            self.log_audit("TASK_VERIFIED",{"task_id":task_id,"note":verification_note})
            return True
        except Exception as exc:
            logging.error("Task verification failed: %s", exc)
            return False

    def realize_revenue_and_close(self, task_id: str, realized_amount: int) -> bool:
        """Only VERIFIED tasks may be closed; actual amount is explicit, never copied from a claim."""
        if realized_amount < 0:
            return False
        now=self._get_time()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur=conn.cursor()
                cur.execute("SELECT status FROM tasks WHERE id=?",(task_id,))
                row=cur.fetchone()
                if not row or row[0] != "VERIFIED":
                    return False
                if realized_amount > 0:
                    cur.execute("INSERT INTO revenues (id,amount,source_task_id,timestamp) VALUES (?,?,?,?)",
                                (f"rev_{uuid.uuid4().hex[:12]}",realized_amount,task_id,now))
                cur.execute("UPDATE tasks SET status='CLOSED',updated_at=? WHERE id=? AND status='VERIFIED'",(now,task_id))
                if cur.rowcount != 1:
                    raise RuntimeError("Task close transition failed")
            self.log_audit("TASK_CLOSED",{"task_id":task_id,"realized_amount":realized_amount})
            return True
        except Exception as exc:
            logging.error("Task close failed: %s", exc)
            return False

    def get_state_snapshot(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory=sqlite3.Row
                tasks=[dict(r) for r in conn.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 100")]
                realized=conn.execute("SELECT COALESCE(SUM(amount),0) FROM revenues").fetchone()[0]
            return {"status":"observed","runtime":"OFF","tasks":tasks,"realized_revenue":realized}
        except Exception as exc:
            return {"status":"degraded","runtime":"OFF","error":str(exc)}
