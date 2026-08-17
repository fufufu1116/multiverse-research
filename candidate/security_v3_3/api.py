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

# === ORACLE V2 COMPAT START ===
import os as _os
import tempfile as _tempfile
import fcntl as _fcntl


def _mv33_atomic_json_write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = _tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with _os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, sort_keys=True)
            f.flush()
            _os.fsync(f.fileno())
        _os.replace(tmp, path)
    finally:
        if _os.path.exists(tmp):
            _os.unlink(tmp)


class KeyProvider:
    def __init__(self, provider):
        if not callable(provider):
            raise TypeError("provider must be callable")
        self._provider = provider

    def get_key(self):
        key = self._provider()
        if not isinstance(key, (bytes, bytearray)):
            raise TypeError("provider must return bytes")
        return bytes(key)

    def __call__(self):
        return self.get_key()


# Preserve existing vault implementation and add provider access.
_OriginalSyntheticHoldoutVault = SyntheticHoldoutVault

class SyntheticHoldoutVault(_OriginalSyntheticHoldoutVault):
    def open_with_provider(self, provider):
        # Provider failure occurs before any state mutation.
        if hasattr(provider, "get_key"):
            key = provider.get_key()
        else:
            key = provider()
        return self.open(key)


class AuthenticatedRequestGate:
    def __init__(self, path, secret):
        self.path = Path(path)
        if not isinstance(secret, (bytes, bytearray)) or not secret:
            raise ValueError("secret required")
        self.secret = bytes(secret)

    def _state(self):
        if not self.path.exists():
            return {"accepted": 0}
        try:
            x = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(x, dict):
                raise ValueError
            return x
        except Exception:
            raise ValueError("authentication state corrupted")

    def accept(self, msg, sig):
        if not isinstance(msg, (bytes, bytearray)):
            raise TypeError("msg must be bytes")
        if not isinstance(sig, str) or len(sig) != 64:
            raise ValueError("malformed signature")

        if not Authenticator.verify(self.secret, bytes(msg), sig):
            raise ValueError("authentication failed")

        state = self._state()
        state["accepted"] = int(state.get("accepted", 0)) + 1
        _mv33_atomic_json_write(self.path, state)
        return True


class AuditedHoldoutGate:
    def __init__(self, path, key, audit_path):
        self.path = Path(path)
        self.key = bytes(key)
        self.audit_path = Path(audit_path)
        self.lock_path = Path(str(self.path) + ".lock")

    def _locked(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        f = self.lock_path.open("a+")
        _fcntl.flock(f.fileno(), _fcntl.LOCK_EX)
        return f

    def initialize(self, payload):
        if not isinstance(payload, bytes):
            raise TypeError("payload must be bytes")

        lock = self._locked()
        try:
            if self.path.exists():
                raise ValueError("gate already initialized")

            nonce = 1
            stream = hashlib.sha256(self.key + str(nonce).encode()).digest()
            ct = bytes(b ^ stream[i % len(stream)] for i, b in enumerate(payload))
            mac = hmac.new(
                self.key,
                str(nonce).encode() + ct,
                hashlib.sha256
            ).hexdigest()

            _mv33_atomic_json_write(self.path, {
                "nonce": nonce,
                "open_count": 0,
                "ciphertext": ct.hex(),
                "mac": mac,
            })
        finally:
            _fcntl.flock(lock.fileno(), _fcntl.LOCK_UN)
            lock.close()

    def state(self):
        if not self.path.exists():
            raise ValueError("gate not initialized")
        return json.loads(self.path.read_text(encoding="utf-8"))

    def open_once(self, key):
        key = bytes(key)

        lock = self._locked()
        try:
            state = self.state()

            if int(state.get("open_count", 0)) != 0:
                raise PermissionError("holdout already opened")

            nonce = int(state["nonce"])
            ct = bytes.fromhex(state["ciphertext"])
            expected = hmac.new(
                key,
                str(nonce).encode() + ct,
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected, state["mac"]):
                raise ValueError("key mismatch")

            stream = hashlib.sha256(key + str(nonce).encode()).digest()
            payload = bytes(
                b ^ stream[i % len(stream)]
                for i, b in enumerate(ct)
            )

            # Commit exactly-once state while lock is held.
            state["open_count"] = 1
            state["nonce"] = nonce + 1
            _mv33_atomic_json_write(self.path, state)

            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            with self.audit_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "event": "OPEN",
                    "open_count": 1,
                    "nonce_before": nonce,
                    "nonce_after": nonce + 1,
                }, sort_keys=True) + "\n")
                f.flush()
                _os.fsync(f.fileno())

            return payload
        finally:
            _fcntl.flock(lock.fileno(), _fcntl.LOCK_UN)
            lock.close()


_OriginalAppendOnlyLedger = AppendOnlyLedger

class AppendOnlyLedger(_OriginalAppendOnlyLedger):
    def __init__(self, path, anchor_path=None):
        super().__init__(path)
        self.anchor_path = Path(anchor_path) if anchor_path is not None else None

    def append(self, data):
        super().append(data)
        if self.anchor_path is not None:
            self.anchor_path.parent.mkdir(parents=True, exist_ok=True)
            self.anchor_path.write_text(self.anchor(), encoding="utf-8")

    def verify(self):
        if not super().verify():
            return False

        if self.anchor_path is not None and self.anchor_path.exists():
            committed_anchor = self.anchor_path.read_text(
                encoding="utf-8"
            ).strip()
            if committed_anchor != self.anchor():
                return False

        return True


class HoldoutMembershipRegistry:
    def __init__(self, path, authority_secret):
        self.path = Path(path)
        if not isinstance(authority_secret, (bytes, bytearray)) or not authority_secret:
            raise ValueError("authority secret required")
        self.authority_secret = bytes(authority_secret)

    def _load(self):
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def commit(self, members, authority_secret):
        if not hmac.compare_digest(
            bytes(authority_secret),
            self.authority_secret
        ):
            raise PermissionError("invalid authority")

        if not isinstance(members, (list, tuple)) or not members:
            raise ValueError("members required")

        vals = list(members)
        if len(vals) != len(set(vals)):
            raise ValueError("duplicate membership")

        current = self._load()
        if current:
            if current.get("members") == vals:
                return vals
            raise PermissionError("membership already committed")

        digest = hashlib.sha256(
            json.dumps(vals, separators=(",", ":")).encode()
        ).hexdigest()

        _mv33_atomic_json_write(self.path, {
            "members": vals,
            "commitment_sha256": digest,
        })
        return vals

    def members(self):
        data = self._load()
        if "members" not in data:
            raise ValueError("membership not committed")
        return list(data["members"])

    def replace(self, members):
        raise PermissionError("authoritative membership is immutable")

    def assert_disjoint(self, other):
        mine = set(self.members())
        overlap = mine.intersection(other)
        if overlap:
            raise ValueError(
                "HOLDOUT overlap detected: " + ",".join(sorted(overlap))
            )
        return True


class FoldRegistry:
    def __init__(self, path, min_train=None, min_valid=None):
        self.path = Path(path)
        self.min_train = min_train
        self.min_valid = min_valid

    def _load(self):
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {}

    def _save(self, data):
        _mv33_atomic_json_write(self.path, data)

    def bind(
        self,
        fold_id,
        version,
        train_end,
        valid_start,
        embargo,
        train_start=None,
        valid_end=None,
    ):
        folds = self._load()

        if fold_id in folds:
            raise ValueError(f"Fold '{fold_id}' already registered")

        if not isinstance(embargo, int) or embargo < 0:
            raise ValueError("invalid embargo")

        if train_start is not None:
            if train_start > train_end:
                raise ValueError("reverse train chronology")
            train_n = train_end - train_start + 1
            if self.min_train is not None and train_n < self.min_train:
                raise ValueError("training fold below minimum size")

        if valid_end is not None:
            if valid_start > valid_end:
                raise ValueError("reverse validation chronology")
            valid_n = valid_end - valid_start + 1
            if self.min_valid is not None and valid_n < self.min_valid:
                raise ValueError("validation fold below minimum size")

        # Require full embargo gap.
        if valid_start < train_end + embargo + 1:
            raise ValueError("Embargo overlap detected")

        folds[fold_id] = {
            "fold_id": fold_id,
            "version": version,
            "train_start": train_start,
            "train_end": train_end,
            "valid_start": valid_start,
            "valid_end": valid_end,
            "embargo": embargo,
        }
        self._save(folds)

    def get(self, fold_id):
        folds = self._load()
        if fold_id not in folds:
            raise KeyError(fold_id)
        return folds[fold_id]


class FamilyManifest:
    def __init__(self, path, authority_token, floors=None):
        self.path = Path(path)
        self.authority_token = authority_token
        self._requested_floors = dict(floors or {})

        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            existing = data.get("floors", {})
            if self._requested_floors and existing and existing != self._requested_floors:
                raise PermissionError("authoritative floors mismatch")

    def _load(self):
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {}

    def _save(self, data):
        _mv33_atomic_json_write(self.path, data)

    def commit(self, sha, authority_token):
        if authority_token != self.authority_token:
            raise ValueError("Invalid authority token")

        data = self._load()
        existing_sha = data.get("sha")

        if existing_sha is not None and existing_sha != sha:
            raise ValueError("Manifest already committed to different sha")

        if "floors" not in data:
            data["floors"] = dict(self._requested_floors)
        elif self._requested_floors and data["floors"] != self._requested_floors:
            raise PermissionError("authoritative floors cannot change")

        data["sha"] = sha
        self._save(data)
        return sha

    def assert_meets(self, metrics):
        data = self._load()
        floors = data.get("floors", self._requested_floors)

        for floor_name, floor_value in floors.items():
            metric_name = (
                floor_name[4:]
                if floor_name.startswith("min_")
                else floor_name
            )
            if metric_name not in metrics:
                raise ValueError(f"missing metric: {metric_name}")
            if metrics[metric_name] < floor_value:
                raise ValueError(
                    f"{metric_name} below authoritative floor"
                )

        return True

    def mask_floor(self, name, value):
        raise PermissionError("authoritative floors cannot be masked")


class PayoutEngine:
    @staticmethod
    def _validate_ticket(ticket, size):
        if not isinstance(ticket, (tuple, list)) or len(ticket) != size:
            raise ValueError(f"ticket must contain exactly {size} runners")
        if len(set(ticket)) != size:
            raise ValueError("ticket runners must be distinct")
        return tuple(ticket)

    @staticmethod
    def _validate_winners(winners, size):
        if not isinstance(winners, (tuple, list)):
            raise TypeError("winners must be list/tuple")

        out = []
        for w in winners:
            if not isinstance(w, (tuple, list)) or len(w) != size:
                raise ValueError("malformed winning combination")
            if len(set(w)) != size:
                raise ValueError("winning runners must be distinct")
            out.append(tuple(w))
        return out

    @staticmethod
    def settle_exacta(bet, winners):
        b = PayoutEngine._validate_ticket(bet, 2)
        ws = PayoutEngine._validate_winners(winners, 2)
        return b in ws

    @staticmethod
    def settle_quinella(bet, winners):
        b = PayoutEngine._validate_ticket(bet, 2)
        ws = PayoutEngine._validate_winners(winners, 2)
        target = frozenset(b)
        return any(frozenset(w) == target for w in ws)

    @staticmethod
    def settle_trio(bet, winners):
        b = PayoutEngine._validate_ticket(bet, 3)
        ws = PayoutEngine._validate_winners(winners, 3)
        target = frozenset(b)
        return any(frozenset(w) == target for w in ws)

# === ORACLE V2 COMPAT END ===
