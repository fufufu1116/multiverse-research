"""Shared Engine authoritative task state store. Candidate-only.

SQLite task state is the sole workflow authority. Relay/provider receipts are evidence
inputs only and cannot mutate state without a fenced transition through this module.
"""
from __future__ import annotations
import json, sqlite3, time, uuid
import config

class LostLeaseError(Exception): pass
class InvalidTransitionError(Exception): pass

RECOVERABLE_ACTIVE_STATES = frozenset({
    'IN_IMPLEMENT', 'IN_LAB', 'LAB_FIX_REQUIRED', 'IN_AUDIT', 'AUDIT_FIX_REQUIRED'
})

def _conn():
    c=sqlite3.connect(config.DB_PATH, timeout=10); c.row_factory=sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA synchronous=FULL'); c.execute('PRAGMA busy_timeout=10000')
    return c

def init_schema():
    c=_conn()
    with c:
        c.execute('''CREATE TABLE IF NOT EXISTS tasks(
            id TEXT PRIMARY KEY, domain TEXT NOT NULL, task_type TEXT NOT NULL,
            goal TEXT NOT NULL, priority INTEGER NOT NULL, state TEXT NOT NULL,
            claimed_by TEXT, claim_generation INTEGER NOT NULL DEFAULT 0,
            lease_until REAL, result_json TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL, updated_at REAL NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
            actor TEXT NOT NULL, event_type TEXT NOT NULL, before_state TEXT NOT NULL,
            after_state TEXT NOT NULL, detail_json TEXT NOT NULL, created_at REAL NOT NULL)''')
    c.close()

def create_task(domain, goal, *, task_type='research', priority=0):
    init_schema(); tid='task-'+uuid.uuid4().hex[:16]; now=time.time(); c=_conn()
    with c:
        c.execute('INSERT INTO tasks(id,domain,task_type,goal,priority,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',
                  (tid,domain,task_type,goal,int(priority),'PENDING',now,now))
        c.execute('INSERT INTO events(task_id,actor,event_type,before_state,after_state,detail_json,created_at) VALUES(?,?,?,?,?,?,?)',
                  (tid,'shared_engine','TASK_CREATED','PENDING','PENDING','{}',now))
    c.close(); return tid

def get_task(task_id):
    init_schema(); c=_conn(); r=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone(); c.close()
    if r is None:return None
    d=dict(r); d['result']=json.loads(d.pop('result_json')); return d

def list_tasks():
    init_schema(); c=_conn(); rows=c.execute('SELECT * FROM tasks ORDER BY created_at').fetchall(); c.close(); out=[]
    for r in rows:
        d=dict(r); d['result']=json.loads(d.pop('result_json')); out.append(d)
    return out

def claim_next_task(worker_id, *, lease_seconds=None):
    init_schema(); lease_seconds=config.LEASE_SECONDS if lease_seconds is None else lease_seconds
    now=time.time(); c=_conn(); c.execute('BEGIN IMMEDIATE')
    try:
        r=c.execute("SELECT id FROM tasks WHERE state='PENDING' AND (claimed_by IS NULL OR lease_until<?) ORDER BY priority DESC,created_at LIMIT 1",(now,)).fetchone()
        if r is None: c.commit(); c.close(); return None
        tid=r['id']; c.execute('UPDATE tasks SET claimed_by=?,claim_generation=claim_generation+1,lease_until=?,updated_at=? WHERE id=?',
                               (worker_id,now+lease_seconds,now,tid)); c.commit(); c.close(); return tid
    except BaseException: c.rollback(); c.close(); raise

def reclaim_expired_task(task_id, worker_id, *, lease_seconds=None):
    """Take over one expired active task without changing its workflow state.

    This is deliberately explicit rather than folded into claim_next_task: a new task
    claimant must not accidentally steal an older active task. The generation bump
    fences every pre-crash worker/receipt application attempt.
    """
    init_schema(); lease_seconds=config.LEASE_SECONDS if lease_seconds is None else lease_seconds
    now=time.time(); c=_conn(); c.execute('BEGIN IMMEDIATE')
    try:
        r=c.execute('SELECT state,claimed_by,claim_generation,lease_until FROM tasks WHERE id=?',(task_id,)).fetchone()
        if r is None: raise KeyError(task_id)
        if r['state'] not in RECOVERABLE_ACTIVE_STATES: raise InvalidTransitionError(f"RECLAIM_STATE:{r['state']}")
        if r['claimed_by'] is None or r['lease_until'] is None or r['lease_until']>=now: raise LostLeaseError('task lease is not expired')
        new_generation=r['claim_generation']+1
        c.execute('UPDATE tasks SET claimed_by=?,claim_generation=?,lease_until=?,updated_at=? WHERE id=?',
                  (worker_id,new_generation,now+lease_seconds,now,task_id))
        c.execute('INSERT INTO events(task_id,actor,event_type,before_state,after_state,detail_json,created_at) VALUES(?,?,?,?,?,?,?)',
                  (task_id,worker_id,'LEASE_RECLAIMED',r['state'],r['state'],json.dumps({'prior_worker':r['claimed_by'],'generation':new_generation},sort_keys=True,separators=(',',':')),now))
        c.commit(); c.close(); return new_generation
    except BaseException: c.rollback(); c.close(); raise

def transition(task_id,new_state,*,actor,event_type,detail=None,result_update=None,release=False,fencing=None):
    init_schema(); c=_conn(); c.execute('BEGIN IMMEDIATE')
    try:
        r=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
        if r is None: raise KeyError(task_id)
        before=r['state']
        if new_state not in config.ALLOWED_TRANSITIONS.get(before,set()): raise InvalidTransitionError(f'{before}->{new_state}')
        if fencing is not None:
            worker,generation=fencing
            if r['claimed_by']!=worker or r['claim_generation']!=generation: raise LostLeaseError('stale fencing token')
        result=json.loads(r['result_json'])
        if result_update: result.update(result_update)
        now=time.time(); claimed=None if release else r['claimed_by']; lease=None if release else r['lease_until']
        c.execute('UPDATE tasks SET state=?,claimed_by=?,lease_until=?,result_json=?,updated_at=? WHERE id=?',
                  (new_state,claimed,lease,json.dumps(result,sort_keys=True,separators=(',',':')),now,task_id))
        c.execute('INSERT INTO events(task_id,actor,event_type,before_state,after_state,detail_json,created_at) VALUES(?,?,?,?,?,?,?)',
                  (task_id,actor,event_type,before,new_state,json.dumps(detail or {},sort_keys=True,separators=(',',':')),now))
        c.commit(); c.close(); return new_state
    except BaseException: c.rollback(); c.close(); raise
