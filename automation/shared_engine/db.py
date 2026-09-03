"""Shared Engine authoritative task state store. Candidate-only.

SQLite task state is the sole workflow authority. Relay/provider receipts are evidence
inputs only and cannot mutate state without a fenced transition through this module.
"""
from __future__ import annotations
import json, math, sqlite3, time, uuid
import config

class LostLeaseError(Exception): pass
class InvalidTransitionError(Exception): pass

RECOVERABLE_ACTIVE_STATES = frozenset({
    'IN_IMPLEMENT', 'IN_LAB', 'LAB_FIX_REQUIRED', 'IN_AUDIT', 'AUDIT_FIX_REQUIRED',
    'BLOCKED_TECHNICAL'
})
RELEASE_SAFE_STATES = frozenset({'PENDING','FAILED_CLOSED','OWNER_GATE','DONE','ROLLED_BACK'})

def _validated_worker_id(worker_id):
    if (not isinstance(worker_id,str) or not worker_id.strip() or
            len(worker_id)>config.WORKER_ID_MAX_LENGTH):
        raise ValueError('WORKER_ID_BOUNDED_NONEMPTY_REQUIRED')
    return worker_id

def _validated_generation(generation):
    # Python bool and integral floats compare equal to ints (True == 1, 1.0 == 1).
    # Fencing tokens must preserve exact type/identity semantics, not numeric coercion.
    if isinstance(generation,bool) or not isinstance(generation,int) or generation <= 0:
        raise LostLeaseError('invalid fencing generation')
    return generation

def _validated_lease_seconds(lease_seconds):
    lease_seconds=config.LEASE_SECONDS if lease_seconds is None else lease_seconds
    if (isinstance(lease_seconds,bool) or not isinstance(lease_seconds,(int,float)) or
            not math.isfinite(float(lease_seconds)) or lease_seconds<=0 or
            lease_seconds>config.LEASE_MAX_SECONDS):
        raise ValueError('LEASE_SECONDS_BOUNDED_FINITE_REQUIRED')
    return float(lease_seconds)

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

def assert_unexpired_fence(task_id, worker_id, generation):
    """Fail closed unless worker/generation still owns an unexpired task lease."""
    init_schema(); worker_id=_validated_worker_id(worker_id); generation=_validated_generation(generation); now=time.time(); c=_conn()
    try:
        r=c.execute('SELECT claimed_by,claim_generation,lease_until FROM tasks WHERE id=?',(task_id,)).fetchone()
    finally:
        c.close()
    if r is None: raise KeyError(task_id)
    if r['claimed_by']!=worker_id or r['claim_generation']!=generation: raise LostLeaseError('stale fencing token')
    if r['lease_until'] is None or r['lease_until']<=now: raise LostLeaseError('task lease expired')
    return True

def claim_next_task(worker_id, *, lease_seconds=None):
    init_schema(); worker_id=_validated_worker_id(worker_id); lease_seconds=_validated_lease_seconds(lease_seconds)
    c=_conn(); c.execute('BEGIN IMMEDIATE')
    try:
        now=time.time()
        r=c.execute("SELECT id FROM tasks WHERE state='PENDING' AND (claimed_by IS NULL OR lease_until<?) ORDER BY priority DESC,created_at LIMIT 1",(now,)).fetchone()
        if r is None: c.commit(); c.close(); return None
        tid=r['id']; c.execute('UPDATE tasks SET claimed_by=?,claim_generation=claim_generation+1,lease_until=?,updated_at=? WHERE id=?',
                               (worker_id,now+lease_seconds,now,tid)); c.commit(); c.close(); return tid
    except BaseException: c.rollback(); c.close(); raise

def claim_task(task_id, worker_id, *, lease_seconds=None):
    """Claim exactly one requested PENDING task without mutating any other queue item."""
    init_schema(); worker_id=_validated_worker_id(worker_id); lease_seconds=_validated_lease_seconds(lease_seconds)
    c=_conn(); c.execute('BEGIN IMMEDIATE')
    try:
        now=time.time()
        r=c.execute('SELECT state,claimed_by,lease_until FROM tasks WHERE id=?',(task_id,)).fetchone()
        if r is None: raise KeyError(task_id)
        if r['state']!='PENDING': raise InvalidTransitionError(f"CLAIM_STATE:{r['state']}")
        if r['claimed_by'] is not None and (r['lease_until'] is None or r['lease_until']>=now):
            raise LostLeaseError('task is already claimed')
        c.execute('UPDATE tasks SET claimed_by=?,claim_generation=claim_generation+1,lease_until=?,updated_at=? WHERE id=?',
                  (worker_id,now+lease_seconds,now,task_id))
        generation=c.execute('SELECT claim_generation FROM tasks WHERE id=?',(task_id,)).fetchone()['claim_generation']
        c.commit(); c.close(); return generation
    except BaseException: c.rollback(); c.close(); raise

def renew_lease(task_id, worker_id, generation, *, lease_seconds=None):
    """Extend a healthy recoverable lease without changing ownership or generation.

    Renewal cannot resurrect an expired lease and cannot operate on pending/terminal
    states. BLOCKED_TECHNICAL remains owned and recoverable, so a healthy blocker may
    renew while a dead blocker can later be reclaimed with a generation bump.
    The authoritative clock sample is taken only after the SQLite writer transaction
    is acquired, so lock wait cannot turn a pre-expiry observation into a post-expiry
    resurrection. Expired work must reclaim with generation bump.
    """
    init_schema(); worker_id=_validated_worker_id(worker_id); generation=_validated_generation(generation); lease_seconds=_validated_lease_seconds(lease_seconds)
    c=_conn(); c.execute('BEGIN IMMEDIATE')
    try:
        now=time.time()
        r=c.execute('SELECT state,claimed_by,claim_generation,lease_until FROM tasks WHERE id=?',(task_id,)).fetchone()
        if r is None: raise KeyError(task_id)
        if r['state'] not in RECOVERABLE_ACTIVE_STATES: raise InvalidTransitionError(f"RENEW_STATE:{r['state']}")
        if r['claimed_by']!=worker_id or r['claim_generation']!=generation: raise LostLeaseError('stale fencing token')
        if r['lease_until'] is None or r['lease_until']<=now: raise LostLeaseError('task lease expired')
        new_until=max(float(r['lease_until']),now+lease_seconds)
        c.execute('UPDATE tasks SET lease_until=?,updated_at=? WHERE id=?',(new_until,now,task_id))
        c.execute('INSERT INTO events(task_id,actor,event_type,before_state,after_state,detail_json,created_at) VALUES(?,?,?,?,?,?,?)',
                  (task_id,worker_id,'LEASE_RENEWED',r['state'],r['state'],json.dumps({'generation':generation,'lease_until':new_until},sort_keys=True,separators=(',',':')),now))
        c.commit(); c.close(); return new_until
    except BaseException: c.rollback(); c.close(); raise

def reclaim_expired_task(task_id, worker_id, *, lease_seconds=None):
    """Take over one expired recoverable task without changing its workflow state."""
    init_schema(); worker_id=_validated_worker_id(worker_id); lease_seconds=_validated_lease_seconds(lease_seconds)
    c=_conn(); c.execute('BEGIN IMMEDIATE')
    try:
        now=time.time()
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
    """Perform one workflow transition only with a live fencing token.

    Durable provenance is derived from authority, not caller labels: event actor is the
    exact fenced worker and event_type is the canonical state transition. Caller-supplied
    component/event labels survive only as declared metadata.
    """
    init_schema(); c=_conn(); c.execute('BEGIN IMMEDIATE')
    try:
        r=c.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
        if r is None: raise KeyError(task_id)
        before=r['state']
        if new_state not in config.ALLOWED_TRANSITIONS.get(before,set()): raise InvalidTransitionError(f'{before}->{new_state}')
        if release and new_state not in RELEASE_SAFE_STATES: raise InvalidTransitionError(f'RELEASE_TARGET:{new_state}')
        if fencing is None: raise LostLeaseError('fencing token required')
        now=time.time()
        worker,generation=fencing; worker=_validated_worker_id(worker); generation=_validated_generation(generation)
        if r['claimed_by']!=worker or r['claim_generation']!=generation: raise LostLeaseError('stale fencing token')
        if r['lease_until'] is None or r['lease_until']<=now: raise LostLeaseError('task lease expired')
        result=json.loads(r['result_json'])
        if result_update: result.update(result_update)
        claimed=None if release else r['claimed_by']; lease=None if release else r['lease_until']
        event_detail=dict(detail or {})
        event_detail['declared_actor']=actor
        event_detail['declared_event_type']=event_type
        event_detail['fencing_worker']=worker
        canonical_event_type=f'STATE_TRANSITION:{before}->{new_state}'
        c.execute('UPDATE tasks SET state=?,claimed_by=?,lease_until=?,result_json=?,updated_at=? WHERE id=?',
                  (new_state,claimed,lease,json.dumps(result,sort_keys=True,separators=(',',':')),now,task_id))
        c.execute('INSERT INTO events(task_id,actor,event_type,before_state,after_state,detail_json,created_at) VALUES(?,?,?,?,?,?,?)',
                  (task_id,worker,canonical_event_type,before,new_state,json.dumps(event_detail,sort_keys=True,separators=(',',':')),now))
        c.commit(); c.close(); return new_state
    except BaseException: c.rollback(); c.close(); raise
