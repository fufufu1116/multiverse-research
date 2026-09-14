import hashlib
import hmac
import json
from pathlib import Path


class SyntheticHoldoutVault:
    def __init__(self, path, key: bytes):
        self.path = Path(path)
        self.key = key
        self._load()

    def _load(self):
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.burn_count = data.get("burn_count", 0)
            self.nonce = data.get("nonce", 1)
            self.ciphertext = data.get("ciphertext", "")
            self.mac = data.get("mac", "")
        else:
            self.burn_count = 0
            self.nonce = 1
            self.ciphertext = ""
            self.mac = ""

    def state(self) -> dict:
        self._load()
        return {"burn_count": self.burn_count, "nonce": self.nonce}

    def seal(self, payload: bytes):
        if not isinstance(payload, bytes):
            raise TypeError("Payload must be bytes")
        stream = hashlib.sha256(self.key + str(self.nonce).encode()).digest()
        ct = bytes(b ^ stream[i % len(stream)] for i, b in enumerate(payload))
        self.ciphertext = ct.hex()
        self.mac = hmac.new(self.key, str(self.nonce).encode() + ct, hashlib.sha256).hexdigest()
        data = {
            "burn_count": self.burn_count,
            "nonce": self.nonce,
            "ciphertext": self.ciphertext,
            "mac": self.mac,
        }
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def open(self, key: bytes) -> bytes:
        self._load()
        if not self.ciphertext or not self.mac:
            raise ValueError("Vault is unsealed")
        ct = bytes.fromhex(self.ciphertext)
        expected_mac = hmac.new(key, str(self.nonce).encode() + ct, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_mac, self.mac):
            raise ValueError("Decryption failed: key mismatch")
        stream = hashlib.sha256(key + str(self.nonce).encode()).digest()
        return bytes(b ^ stream[i % len(stream)] for i, b in enumerate(ct))


class Authenticator:
    @staticmethod
    def sign(secret: bytes, msg: bytes) -> str:
        return hmac.new(secret, msg, hashlib.sha256).hexdigest()

    @staticmethod
    def verify(secret: bytes, msg: bytes, sig: str) -> bool:
        expected = hmac.new(secret, msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)


class PersistentCounter:
    def __init__(self, path):
        self.path = Path(path)

    def value(self) -> int:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data.get("value", 0)
        return 0

    def increment(self) -> int:
        val = self.value() + 1
        self.path.write_text(json.dumps({"value": val}), encoding="utf-8")
        return val


class AppendOnlyLedger:
    def __init__(self, path):
        self.path = Path(path)

    def _read_records(self) -> list:
        if not self.path.exists():
            return []
        content = self.path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        return [json.loads(line) for line in content.splitlines() if line.strip()]

    def append(self, data: str):
        records = self._read_records()
        idx = len(records)
        prev_hash = records[-1]["hash"] if records else "0" * 64
        h = hashlib.sha256(f"{idx}:{prev_hash}:{data}".encode("utf-8")).hexdigest()
        record = {"index": idx, "data": data, "prev_hash": prev_hash, "hash": h}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")

    def anchor(self) -> str:
        records = self._read_records()
        return records[-1]["hash"] if records else ""

    def verify(self) -> bool:
        records = self._read_records()
        expected_prev = "0" * 64
        for idx, rec in enumerate(records):
            if rec.get("index") != idx:
                return False
            if rec.get("prev_hash") != expected_prev:
                return False
            data = rec.get("data", "")
            h = hashlib.sha256(f"{idx}:{expected_prev}:{data}".encode("utf-8")).hexdigest()
            if rec.get("hash") != h:
                return False
            expected_prev = h
        return True

    def update(self, idx: int, data: str):
        raise PermissionError("Ledger is append-only")

    def delete(self, idx: int):
        raise PermissionError("Ledger is append-only")


class FoldRegistry:
    def __init__(self, path):
        self.path = Path(path)

    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {}

    def _save(self, data: dict):
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def bind(self, fold_id: str, version: str, train_end: int, valid_start: int, embargo: int):
        folds = self._load()
        if fold_id in folds:
            raise ValueError(f"Fold '{fold_id}' already registered")
        if valid_start < train_end + embargo:
            raise ValueError("Embargo overlap detected")
        folds[fold_id] = {
            "fold_id": fold_id,
            "version": version,
            "train_end": train_end,
            "valid_start": valid_start,
            "embargo": embargo,
        }
        self._save(folds)

    def get(self, fold_id: str) -> dict:
        folds = self._load()
        if fold_id not in folds:
            raise KeyError(f"Fold '{fold_id}' not found")
        return folds[fold_id]


class PhaseRegistry:
    def __init__(self, path):
        self.path = Path(path)

    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {}

    def _save(self, data: dict):
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def preregister(self, phase: str, candidate_id: str):
        phases = self._load()
        if phase in phases:
            raise ValueError(f"Phase '{phase}' already preregistered")
        phases[phase] = candidate_id
        self._save(phases)

    def execute(self, phase: str, candidate_id: str) -> bool:
        phases = self._load()
        if phase not in phases:
            raise ValueError(f"Phase '{phase}' not preregistered")
        if phases[phase] != candidate_id:
            raise ValueError(f"Candidate '{candidate_id}' mismatch")
        return True


class FamilyManifest:
    def __init__(self, path, authority_token: str):
        self.path = Path(path)
        self.authority_token = authority_token

    def commit(self, sha: str, authority_token: str) -> str:
        if authority_token != self.authority_token:
            raise ValueError("Invalid authority token")
        data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        committed_sha = data.get("sha")
        if committed_sha is not None:
            if committed_sha != sha:
                raise ValueError("Manifest already committed to different sha")
            return sha
        data["sha"] = sha
        self.path.write_text(json.dumps(data), encoding="utf-8")
        return sha


class MarketEvidence:
    REQUIRED_KEYS = {"race_id", "market", "asof_ts", "source", "runner_ids", "odds", "parser_fingerprint"}

    @staticmethod
    def validate(evidence: dict) -> bool:
        if not isinstance(evidence, dict):
            raise TypeError("Evidence must be a dict")
        if set(evidence.keys()) != MarketEvidence.REQUIRED_KEYS:
            raise ValueError("Incomplete or invalid evidence structure")
        runners = evidence.get("runner_ids")
        if not isinstance(runners, (list, tuple)):
            raise TypeError("runner_ids must be list/tuple")
        if len(runners) != len(set(runners)):
            raise ValueError("runner_ids contains duplicates")
        return True


class PayoutEngine:
    @staticmethod
    def settle_exacta(bet, winners) -> bool:
        if not isinstance(bet, (tuple, list)) or len(bet) != 2:
            raise ValueError("Bet must be exact pair")
        if bet[0] == bet[1]:
            raise ValueError("Bet runners must be distinct")
        if not isinstance(winners, (tuple, list)):
            raise TypeError("Winners must be a list or tuple")
        for w in winners:
            if not isinstance(w, (tuple, list)) or len(w) != 2:
                raise ValueError("Each winning pair must have length 2")
        return tuple(bet) in [tuple(w) for w in winners]


class SourceGuard:
    def __init__(self, path, expected_schema: str, expected_parser_fingerprint: str):
        self.path = Path(path)
        self.expected_schema = expected_schema
        self.expected_parser_fingerprint = expected_parser_fingerprint

    def _save(self, data: dict):
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def is_quarantined(self) -> bool:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data.get("quarantined", False)
        return False

    def ingest(self, data: dict, schema: str, parser_fingerprint: str) -> bool:
        if self.is_quarantined():
            raise ValueError("Source is quarantined")
        if schema != self.expected_schema or parser_fingerprint != self.expected_parser_fingerprint:
            self._save({"quarantined": True})
            raise ValueError("Schema/parser mismatch; source quarantined")
        return True


class PersistentKillSwitch:
    def __init__(self, path):
        self.path = Path(path)

    def is_killed(self) -> bool:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data.get("killed", False)
        return False

    def trigger(self, reason: str):
        self.path.write_text(json.dumps({"killed": True, "reason": reason}), encoding="utf-8")

    def assert_open(self):
        if self.is_killed():
            raise ValueError("Kill switch is triggered")


class ProvenanceLedger:
    def __init__(self, path):
        self.path = Path(path)

    def _load(self) -> list:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def record(self, event_id: str, event_type: str, amount: float, ref: str):
        events = self._load()
        existing_ids = {e["event_id"] for e in events}
        if event_id in existing_ids:
            raise ValueError(f"Event '{event_id}' already exists")
        if event_type == "refund":
            if ref not in existing_ids:
                raise ValueError(f"Referenced event '{ref}' not found for refund")
        record_data = {
            "event_id": event_id,
            "event_type": event_type,
            "amount": amount,
            "ref": ref,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record_data, sort_keys=True) + "\n")

    def events(self) -> list:
        return self._load()

    def verify(self) -> bool:
        events = self._load()
        seen = set()
        for e in events:
            eid = e.get("event_id")
            etype = e.get("event_type")
            ref = e.get("ref")
            if not eid or eid in seen:
                return False
            if etype == "refund" and ref not in seen:
                return False
            seen.add(eid)
        return True
