import sqlite3
import logging
from datetime import datetime, timezone
from core_state import CoreStateEngine

class DeterministicTaskQueue:
    """
    MULTIVERSE - Deterministic Task Queue
    AIに依存せず、SQLiteのトランザクションを用いてタスクの排他制御・二重起動防止を行う
    """
    def __init__(self, core: CoreStateEngine):
        self.core = core

    def _get_time(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def fetch_next_task(self):
        """次に実行すべきタスクを取得し、他プロセスが触れないようロック（RUNNING状態へ移行）する"""
        now = self._get_time()
        
        try:
            with sqlite3.connect(self.core.db_path) as conn:
                cursor = conn.cursor()
                
                # 待機中（QUEUED）のタスクを古い順に1つ探す
                cursor.execute('''
                    SELECT id, title, troop FROM tasks 
                    WHERE status = 'QUEUED' 
                    ORDER BY created_at ASC LIMIT 1
                ''')
                row = cursor.fetchone()
                
                if not row:
                    return None # 実行待ちのタスクなし
                
                task_id, title, troop = row
                
                # 状態を 'RUNNING' に変更し、同じタスクの二重起動を物理的に防ぐ
                cursor.execute('''
                    UPDATE tasks 
                    SET status = 'RUNNING', updated_at = ?
                    WHERE id = ? AND status = 'QUEUED'
                ''', (now, task_id))
                
                if cursor.rowcount == 0:
                    return None # わずかな差で他の処理に取られた場合
                
                conn.commit()
            
            logging.info(f"Task Fetched & Locked: [{task_id}] {title} (Troop: {troop})")
            return {"id": task_id, "title": title, "troop": troop}
            
        except Exception as e:
            logging.error(f"Task fetch failed: {e}")
            # エラー時はFailClosedを呼び出すのが理想的
            return None

    def mark_task_failed(self, task_id: str, reason: str):
        """タスク実行失敗時（AIのエラー等）に安全にFAILED状態へ移す"""
        now = self._get_time()
        try:
            with sqlite3.connect(self.core.db_path) as conn:
                conn.execute(
                    "UPDATE tasks SET status = 'FAILED', updated_at = ? WHERE id = ?",
                    (now, task_id)
                )
                conn.commit()
            self.core.log_audit("TASK_FAILED", {"task_id": task_id, "reason": reason})
            logging.warning(f"Task {task_id} marked as FAILED.")
        except Exception as e:
            logging.error(f"Failed to update task status: {e}")
