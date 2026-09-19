import sqlite3
import json
import uuid
import logging
import hashlib
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [CORE] - %(levelname)s - %(message)s")

class CoreStateEngine:
    """Candidate persistent state engine. Claims, verification receipts, and realized revenue are separate."""

    def __init__(self, db_path: str = "multiverse_core.db"):
        self.db_path=db_path
        self._init_db()

    def _get_time(self): return datetime.now(timezone.utc).isoformat()
    def _canonical(self,payload): return json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False)

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,title TEXT NOT NULL,troop TEXT,claimed_revenue INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'QUEUED',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
                    result TEXT,result_provider TEXT,verification_note TEXT,idempotency_key TEXT UNIQUE)""")
                conn.execute("""CREATE TABLE IF NOT EXISTS revenues (
                    id TEXT PRIMARY KEY,amount INTEGER NOT NULL,source_task_id TEXT NOT NULL UNIQUE,timestamp TEXT NOT NULL)""")
                conn.execute("""CREATE TABLE IF NOT EXISTS verification_receipts (
                    receipt_id TEXT PRIMARY KEY,task_id TEXT NOT NULL UNIQUE,verifier_id TEXT NOT NULL,
                    evidence_ref TEXT NOT NULL,verdict TEXT NOT NULL,timestamp TEXT NOT NULL)""")
                conn.execute("""CREATE TABLE IF NOT EXISTS provider_controls (
                    provider_id TEXT PRIMARY KEY,enabled INTEGER NOT NULL,reason TEXT,updated_at TEXT NOT NULL)""")
                conn.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT NOT NULL UNIQUE,event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,timestamp TEXT NOT NULL,prev_hash TEXT NOT NULL,entry_hash TEXT NOT NULL UNIQUE)""")
            self._migrate_schema()
            self.log_audit("SYSTEM_START",{"message":"CoreStateEngine booted"})
        except Exception as exc:
            logging.critical("Database initialization failed: %s",exc)
            raise SystemExit("System Halted due to Critical State Failure.")

    def _migrate_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            cols={r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
            for name,decl in {"claimed_revenue":"INTEGER DEFAULT 0","result":"TEXT","result_provider":"TEXT",
                              "verification_note":"TEXT","idempotency_key":"TEXT"}.items():
                if name not in cols: conn.execute(f"ALTER TABLE tasks ADD COLUMN {name} {decl}")
            if "revenue" in cols and "claimed_revenue" not in cols:
                conn.execute("UPDATE tasks SET claimed_revenue=COALESCE(revenue,0)")
            dup=conn.execute("""SELECT idempotency_key FROM tasks WHERE idempotency_key IS NOT NULL
                                GROUP BY idempotency_key HAVING COUNT(*)>1 LIMIT 1""").fetchone()
            if dup: raise RuntimeError("duplicate legacy idempotency_key; migration fails closed")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_tasks_idempotency_key ON tasks(idempotency_key) WHERE idempotency_key IS NOT NULL")
            rcols={r[1] for r in conn.execute("PRAGMA table_info(revenues)")}
            if "source_task_id" not in rcols:
                if "source_task" not in rcols: raise RuntimeError("unknown legacy revenues schema")
                conn.execute("ALTER TABLE revenues ADD COLUMN source_task_id TEXT")
                conn.execute("UPDATE revenues SET source_task_id=source_task")
            dup=conn.execute("""SELECT source_task_id FROM revenues WHERE source_task_id IS NOT NULL
                                GROUP BY source_task_id HAVING COUNT(*)>1 LIMIT 1""").fetchone()
            if dup: raise RuntimeError("duplicate legacy revenue source; migration fails closed")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_revenues_source_task_id ON revenues(source_task_id) WHERE source_task_id IS NOT NULL")
            acols={r[1] for r in conn.execute("PRAGMA table_info(audit_logs)")}
            needed={"seq","prev_hash","entry_hash"}
            if not needed.issubset(acols):
                rows=list(conn.execute("SELECT id,event_type,payload,timestamp FROM audit_logs ORDER BY timestamp,id"))
                conn.execute("ALTER TABLE audit_logs RENAME TO audit_logs_legacy")
                conn.execute("""CREATE TABLE audit_logs (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT NOT NULL UNIQUE,event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,timestamp TEXT NOT NULL,prev_hash TEXT NOT NULL,entry_hash TEXT NOT NULL UNIQUE)""")
                prev="GENESIS"
                for rid,event,payload,ts in rows:
                    canonical=payload if isinstance(payload,str) else self._canonical(payload)
                    digest=hashlib.sha256((prev+"|"+rid+"|"+event+"|"+canonical+"|"+ts).encode()).hexdigest()
                    conn.execute("INSERT INTO audit_logs (id,event_type,payload,timestamp,prev_hash,entry_hash) VALUES (?,?,?,?,?,?)",
                                 (rid,event,canonical,ts,prev,digest)); prev=digest
                conn.execute("DROP TABLE audit_logs_legacy")

    def _append_audit(self,conn,event_type,payload):
        rid=str(uuid.uuid4()); ts=self._get_time(); canonical=self._canonical(payload)
        row=conn.execute("SELECT entry_hash FROM audit_logs ORDER BY seq DESC LIMIT 1").fetchone()
        prev=row[0] if row else "GENESIS"
        digest=hashlib.sha256((prev+"|"+rid+"|"+event_type+"|"+canonical+"|"+ts).encode()).hexdigest()
        conn.execute("INSERT INTO audit_logs (id,event_type,payload,timestamp,prev_hash,entry_hash) VALUES (?,?,?,?,?,?)",
                     (rid,event_type,canonical,ts,prev,digest))

    def log_audit(self,event_type,payload):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE"); self._append_audit(conn,event_type,payload)

    def verify_audit_chain(self):
        with sqlite3.connect(self.db_path) as conn:
            prev="GENESIS"
            for rid,event,payload,ts,stored_prev,stored_hash in conn.execute(
                "SELECT id,event_type,payload,timestamp,prev_hash,entry_hash FROM audit_logs ORDER BY seq"):
                expected=hashlib.sha256((prev+"|"+rid+"|"+event+"|"+payload+"|"+ts).encode()).hexdigest()
                if stored_prev!=prev or stored_hash!=expected: return False
                prev=stored_hash
        return True

    def add_task(self,title,troop,revenue=0,idempotency_key=None):
        task_id=f"task_{uuid.uuid4().hex[:12]}"; now=self._get_time()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                if idempotency_key:
                    existing=conn.execute("SELECT id FROM tasks WHERE idempotency_key=?",(idempotency_key,)).fetchone()
                    if existing:return existing[0]
                conn.execute("""INSERT INTO tasks
                    (id,title,troop,claimed_revenue,status,created_at,updated_at,idempotency_key)
                    VALUES (?,?,?,?,?,?,?,?)""",(task_id,title,troop,revenue,"QUEUED",now,now,idempotency_key))
                self._append_audit(conn,"TASK_ADDED",{"task_id":task_id,"title":title,"troop":troop})
            return task_id
        except Exception as exc:
            logging.error("Task addition failed: %s",exc); return None

    def record_task_claim(self,task_id,result,provider_id):
        now=self._get_time()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                cur=conn.execute("""UPDATE tasks SET status='SUCCESS_CLAIMED',result=?,result_provider=?,updated_at=?
                                    WHERE id=? AND status='RUNNING'""",(result,provider_id,now,task_id))
                if cur.rowcount!=1:return False
                self._append_audit(conn,"TASK_RESULT_CLAIMED",{"task_id":task_id,"provider_id":provider_id})
            return True
        except Exception as exc:
            logging.error("Task claim failed: %s",exc); return False

    def apply_verification_receipt(self,task_id,receipt_id,verifier_id,evidence_ref,verdict):
        if not all([receipt_id,verifier_id,evidence_ref]) or verdict!="ACCEPT":
            return False
        if verifier_id in {"core","executor","mock_gemini"}:
            return False
        now=self._get_time()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                row=conn.execute("SELECT status,result_provider FROM tasks WHERE id=?",(task_id,)).fetchone()
                if not row or row[0]!="SUCCESS_CLAIMED" or verifier_id==row[1]: return False
                conn.execute("""INSERT INTO verification_receipts
                    (receipt_id,task_id,verifier_id,evidence_ref,verdict,timestamp) VALUES (?,?,?,?,?,?)""",
                    (receipt_id,task_id,verifier_id,evidence_ref,verdict,now))
                cur=conn.execute("""UPDATE tasks SET status='VERIFIED',verification_note=?,updated_at=?
                                    WHERE id=? AND status='SUCCESS_CLAIMED'""",(f"{verifier_id}:{evidence_ref}",now,task_id))
                if cur.rowcount!=1: raise RuntimeError("verification transition failed")
                self._append_audit(conn,"TASK_VERIFICATION_RECEIPT_ACCEPTED",
                    {"task_id":task_id,"receipt_id":receipt_id,"verifier_id":verifier_id,"evidence_ref":evidence_ref})
            return True
        except Exception as exc:
            logging.error("Verification receipt rejected: %s",exc); return False

    def realize_revenue_and_close(self,task_id,realized_amount):
        if realized_amount<0:return False
        now=self._get_time()
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                row=conn.execute("""SELECT t.status,v.receipt_id FROM tasks t
                    JOIN verification_receipts v ON v.task_id=t.id AND v.verdict='ACCEPT' WHERE t.id=?""",(task_id,)).fetchone()
                if not row or row[0]!="VERIFIED":return False
                if realized_amount>0:
                    conn.execute("INSERT INTO revenues (id,amount,source_task_id,timestamp) VALUES (?,?,?,?)",
                                 (f"rev_{uuid.uuid4().hex[:12]}",realized_amount,task_id,now))
                cur=conn.execute("UPDATE tasks SET status='CLOSED',updated_at=? WHERE id=? AND status='VERIFIED'",(now,task_id))
                if cur.rowcount!=1:raise RuntimeError("Task close transition failed")
                self._append_audit(conn,"TASK_CLOSED",{"task_id":task_id,"realized_amount":realized_amount,"receipt_id":row[1]})
            return True
        except Exception as exc:
            logging.error("Task close failed: %s",exc); return False

    def disable_provider(self,provider_id,reason):
        now=self._get_time()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("""INSERT INTO provider_controls(provider_id,enabled,reason,updated_at) VALUES (?,?,?,?)
                ON CONFLICT(provider_id) DO UPDATE SET enabled=0,reason=excluded.reason,updated_at=excluded.updated_at""",
                (provider_id,0,reason,now))
            self._append_audit(conn,"FAIL_CLOSED_PROVIDER_DISABLE",{"provider_id":provider_id,"reason":reason})

    def is_provider_enabled(self,provider_id):
        with sqlite3.connect(self.db_path) as conn:
            row=conn.execute("SELECT enabled FROM provider_controls WHERE provider_id=?",(provider_id,)).fetchone()
        return row is None or row[0]==1

    def get_state_snapshot(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory=sqlite3.Row
                tasks=[dict(r) for r in conn.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 100")]
                realized=conn.execute("SELECT COALESCE(SUM(amount),0) FROM revenues").fetchone()[0]
            return {"status":"observed","runtime":"OFF","tasks":tasks,"realized_revenue":realized}
        except Exception as exc:
            return {"status":"degraded","runtime":"OFF","error":str(exc)}
