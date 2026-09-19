import logging
import hashlib
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from core_state import CoreStateEngine
from config.queue import DeterministicTaskQueue
from config.fail_closed import FailClosedEnforcer
from config.executor import TaskExecutor

app = FastAPI(title="MULTIVERSE Core API", version="2.0-candidate")
core = CoreStateEngine()
queue = DeterministicTaskQueue(core)
fail_closed = FailClosedEnforcer(core)
executor = TaskExecutor(core, queue, fail_closed)

class ChatPayload(BaseModel):
    schema_version: str
    text: str
    checksum: str | None = None
    idempotency_key: str | None = None

class TaskPayload(BaseModel):
    schema_version: str
    title: str
    troop: str
    revenue: int = 0
    checksum: str | None = None
    idempotency_key: str | None = None

def require_checksum(payload, fields: dict):
    if not payload.checksum:
        raise HTTPException(status_code=400, detail="checksum required")
    canonical=json.dumps(fields,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    expected=hashlib.sha256(canonical.encode()).hexdigest()
    if payload.checksum.lower()!=expected:
        raise HTTPException(status_code=400, detail="checksum mismatch")

def require_schema(version: str):
    if version != "1.0":
        raise HTTPException(status_code=400, detail="Unsupported schema version.")

@app.post("/api/chat")
async def receive_chat(payload: ChatPayload):
    require_schema(payload.schema_version)
    require_checksum(payload,{"schema_version":payload.schema_version,"text":payload.text,"idempotency_key":payload.idempotency_key})
    task_id = core.add_task(payload.text, "司令塔", 0, payload.idempotency_key)
    if not task_id:
        raise HTTPException(status_code=500, detail="Task intake failed.")
    return {"status": "queued", "task_id": task_id, "message": "指示を任務として受け付けました。"}

@app.post("/api/task")
async def receive_task(payload: TaskPayload):
    require_schema(payload.schema_version)
    require_checksum(payload,{"schema_version":payload.schema_version,"title":payload.title,"troop":payload.troop,"revenue":payload.revenue,"idempotency_key":payload.idempotency_key})
    task_id = core.add_task(payload.title, payload.troop, payload.revenue, payload.idempotency_key)
    if not task_id:
        raise HTTPException(status_code=500, detail="Task intake failed.")
    return {"status": "queued", "task_id": task_id}

@app.get("/api/state")
async def get_state():
    return core.get_state_snapshot()

@app.get("/api/health")
async def get_health():
    return {"status": "candidate", "runtime": "OFF", "core_storage": "available"}
