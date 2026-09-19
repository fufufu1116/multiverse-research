import sqlite3
import json
import uuid
import logging
from datetime import datetime, timezone

# ログ設定：システムの挙動をすべて監視・記録する
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [CORE] - %(levelname)s - %(message)s')

class CoreStateEngine:
    """
    MULTIVERSE Core Engine - Persistent State Management
    AIに一切依存せず、タスク・収益・監査ログを安全に永続化する心臓部
    """
    def __init__(self, db_path: str = "multiverse_core.db"):
        self.db_path = db_path
        self._init_db()

    def _get_time(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _init_db(self):
        """DBの初期化とテーブル作成。失敗時は即座にFail Closed（安全停止）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 1. 任務（タスク）管理テーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        troop TEXT,
                        revenue INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'QUEUED', -- QUEUED, RUNNING, SUCCESS, FAILED
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                ''')
                
                # 2. 収益・資産テーブル
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS revenues (
                        id TEXT PRIMARY KEY,
                        amount INTEGER NOT NULL,
                        source_task TEXT,
                        timestamp TEXT NOT NULL
                    )
                ''')
                
                # 3. 監査ログ（不変証跡・絶対に削除してはいけない履歴）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id TEXT PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        payload JSON,
                        timestamp TEXT NOT NULL
                    )
                ''')
                conn.commit()
                logging.info("【System】Core Database initialized successfully.")
                self.log_audit("SYSTEM_START", {"message": "CoreStateEngine booted."})
                
        except Exception as e:
            logging.critical(f"【Fail Closed】Database initialization failed: {e}")
            raise SystemExit("System Halted due to Critical State Failure.")

    def log_audit(self, event_type: str, payload: dict):
        """すべての重要アクションを不変の監査ログとして記録する"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO audit_logs (id, event_type, payload, timestamp) VALUES (?, ?, ?, ?)",
                    (str(uuid.uuid4()), event_type, json.dumps(payload), self._get_time())
                )
                conn.commit()
        except Exception as e:
            logging.error(f"Audit log failed: {e}")

    def add_task(self, title: str, troop: str, revenue: int) -> str:
        """安全なタスク追加"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        now = self._get_time()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO tasks (id, title, troop, revenue, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (task_id, title, troop, revenue, 'QUEUED', now, now)
                )
                conn.commit()
            self.log_audit("TASK_ADDED", {"task_id": task_id, "title": title, "troop": troop})
            logging.info(f"Task Added: {title} [{troop}]")
            return task_id
        except Exception as e:
            logging.error(f"Task addition failed: {e}")
            return None

    def complete_task_and_reflect_revenue(self, task_id: str):
        """タスク完了と収益の自動連動（アトミックなトランザクション処理）"""
        now = self._get_time()
        try:
            with sqlite3.connect(self.db_path) as conn:
                # トランザクション開始：タスク状態と収益追加を絶対に同時に行う
                cursor = conn.cursor()
                cursor.execute("SELECT title, revenue, status FROM tasks WHERE id = ?", (task_id,))
                row = cursor.fetchone()
                
                if not row:
                    raise ValueError("Task not found.")
                if row[2] == 'SUCCESS':
                    raise ValueError("Task is already completed.")

                title, revenue = row[0], row[1]

                # タスクを完了状態に更新
                cursor.execute("UPDATE tasks SET status = 'SUCCESS', updated_at = ? WHERE id = ?", (now, task_id))
                
                # 収益があれば資産テーブルへ追加
                if revenue > 0:
                    rev_id = f"rev_{uuid.uuid4().hex[:8]}"
                    cursor.execute(
                        "INSERT INTO revenues (id, amount, source_task, timestamp) VALUES (?, ?, ?, ?)",
                        (rev_id, revenue, title, now)
                    )
                
                conn.commit()
            
            self.log_audit("TASK_COMPLETED", {"task_id": task_id, "revenue_added": revenue})
            logging.info(f"Task Completed successfully. Revenue added: {revenue}")
            return True
        except Exception as e:
            logging.error(f"Task completion failed: {e}")
            return False

# ---------------------------------------------------------
# 【テスト稼働用モック】MacBookで実行した際のシミュレーション
# ---------------------------------------------------------
if __name__ == "__main__":
    # エンジン起動
    core = CoreStateEngine()
    
    # 司令官からの指示（フロントエンドからの入力を想定）
    t_id = core.add_task("AI自動検証環境の構築", "AI研究", 5000)
    
    # AIプロバイダーや部隊がタスクを完了したと報告した場合
    if t_id:
        core.complete_task_and_reflect_revenue(t_id)
