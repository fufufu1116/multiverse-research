import hashlib
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    task_id: str
    source: str
    media_type: str
    sha256: str
    captured_at: str


class EvidenceBus:
    """Local deterministic evidence store. Integrity is not semantic truth."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        with sqlite3.connect(db_path) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS evidence_objects (
                evidence_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                source TEXT NOT NULL,
                media_type TEXT NOT NULL,
                content BLOB NOT NULL,
                sha256 TEXT NOT NULL,
                captured_at TEXT NOT NULL
            )""")

    def put(self, *, task_id: str, source: str, content: bytes, media_type: str = "application/octet-stream") -> EvidenceRecord:
        if not task_id or not source or not media_type or not isinstance(content, bytes):
            raise ValueError("task_id/source/media_type and bytes content required")
        digest = hashlib.sha256(content).hexdigest()
        evidence_id = f"ev_{uuid.uuid4().hex[:16]}"
        captured_at = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("""INSERT INTO evidence_objects
                (evidence_id,task_id,source,media_type,content,sha256,captured_at)
                VALUES (?,?,?,?,?,?,?)""",
                (evidence_id,task_id,source,media_type,content,digest,captured_at))
        return EvidenceRecord(evidence_id, task_id, source, media_type, digest, captured_at)

    def get_verified(self, evidence_id: str) -> tuple[EvidenceRecord, bytes]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""SELECT evidence_id,task_id,source,media_type,content,sha256,captured_at
                                  FROM evidence_objects WHERE evidence_id=?""", (evidence_id,)).fetchone()
        if not row:
            raise KeyError("evidence not found")
        content = bytes(row[4])
        digest = hashlib.sha256(content).hexdigest()
        if digest != row[5]:
            raise RuntimeError("evidence integrity mismatch")
        return EvidenceRecord(row[0], row[1], row[2], row[3], row[5], row[6]), content

    def ref(self, evidence_id: str) -> str:
        self.get_verified(evidence_id)
        return f"evidence://{evidence_id}"
