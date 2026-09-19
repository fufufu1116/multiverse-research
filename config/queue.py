import sqlite3
import logging
from datetime import datetime, timezone
from core_state import CoreStateEngine

class DeterministicTaskQueue:
    def __init__(self, core: CoreStateEngine):
        self.core=core

    def _get_time(self):
        return datetime.now(timezone.utc).isoformat()

    def fetch_next_task(self):
        now=self._get_time()
        try:
            with sqlite3.connect(self.core.db_path, isolation_level=None) as conn:
                conn.execute("BEGIN IMMEDIATE")
                row=conn.execute("""SELECT id,title,troop FROM tasks WHERE status='QUEUED'
                                    ORDER BY created_at ASC,id ASC LIMIT 1""").fetchone()
                if not row:
                    conn.execute("COMMIT")
                    return None
                task_id,title,troop=row
                cur=conn.execute("""UPDATE tasks SET status='RUNNING',updated_at=?
                                    WHERE id=? AND status='QUEUED'""",(now,task_id))
                if cur.rowcount != 1:
                    conn.execute("ROLLBACK")
                    return None
                self.core._append_audit(conn,"TASK_STARTED",{"task_id":task_id})
                conn.execute("COMMIT")
            return {"id":task_id,"title":title,"troop":troop}
        except Exception as exc:
            logging.error("Task fetch failed: %s", exc)
            return None

    def mark_task_failed(self, task_id: str, reason: str):
        now=self._get_time()
        try:
            with sqlite3.connect(self.core.db_path) as conn:
                cur=conn.execute("""UPDATE tasks SET status='FAILED',updated_at=?
                                    WHERE id=? AND status='RUNNING'""",(now,task_id))
                if cur.rowcount != 1:
                    return False
                self.core._append_audit(conn,"TASK_FAILED",{"task_id":task_id,"reason":reason})
            return True
        except Exception as exc:
            logging.error("Failed to update task status: %s", exc)
            return False
