#!/usr/bin/env python3
"""Review-only generator for the Phase C v17 Step1 single-paste transport.

This file does not perform OAuth, GitHub API calls, production mutation, or Runtime activation.
It deterministically packages an already-reviewed Step1 payload supplied as a local file.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import zlib
from pathlib import Path

EXPECTED_DECODED_LEN = 4687
EXPECTED_DECODED_SHA256 = "bbb4dfc09f669dcba4b8a223b641e9fa81b7ccebda3d72b216d97e3177184b74"
EXPECTED_B64_LEN = 6252
EXPECTED_B64_SHA256 = "f7c353761edf26a0ddeb25a129a7b152a16cf587bf5b620b6421863aa25418b2"
EXPECTED_CHUNK_HASHES = (
    "6e1ca4a34325f5cc8169f8a48100c1f0db46ed5ed2b3ebc3e03b6a3ace8494bd",
    "2cb9655f64eacf65ebbf7df0db10021626ffcfecc4c286bcb7c090cd9f95d09f",
    "cb0a608788378b2778a6f498089f09d445cc55d5c4d5c3688c9a7fd2aa1d334a",
    "a82ff588dbf023634b91caa138186e6b9dacd8049cd8147de20ef2f5b2375ae4",
    "cf498ec4bf0188455fa4386eaaf96388d1d0936e76edad9186c6d5bd4a2b51a4",
    "6176a57e1829d53e12cbaa7e898226cc4b1eaca48778dbc39bcf0d9b593e1ec1",
    "d2e1df752ec73d10662009b38f18dcb5316f7443de22d6fba9dfcceaf7c9858d",
    "90b25ed739ea8a4727fb13320a9038ed48951f55718bd7c1722c4927e9ad1eb3",
    "3e6b2a2f38bc8c0caf614a483787552eced3b9e563c32053ea897827a5b87316",
    "243fa4861f7e83f49f85dbeb495ea03775465b271559dea66ae89d82c72562e8",
    "a1b4e5504f45b919d62a554fce54567b762f754be2b5abc50b4dab2c1b94f869",
    "4c641d73dbb4c5c0af380182dcce508ff6c6b888bf27c0fdbd5528f104b97592",
    "9c7e90df065e8c28ce6b236253994244a9e68fdebf877ae8020535c1e9b04b77",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_payload(raw: bytes) -> str:
    if len(raw) != EXPECTED_DECODED_LEN or sha256(raw) != EXPECTED_DECODED_SHA256:
        raise SystemExit("decoded Step1 invariant mismatch")
    b64 = base64.b64encode(raw).decode("ascii")
    if len(b64) != EXPECTED_B64_LEN or sha256(b64.encode()) != EXPECTED_B64_SHA256:
        raise SystemExit("base64 Step1 invariant mismatch")
    chunks = [b64[i:i + 512] for i in range(0, len(b64), 512)]
    if len(chunks) != 13:
        raise SystemExit("chunk count mismatch")
    for i, (chunk, expected) in enumerate(zip(chunks, EXPECTED_CHUNK_HASHES)):
        if len(chunk) != (108 if i == 12 else 512) or sha256(chunk.encode()) != expected:
            raise SystemExit(f"chunk {i:02d} invariant mismatch")
    return b64


def build_action(b64: str) -> str:
    # The live action deliberately reconstructs the complete reviewed payload in memory,
    # verifies its frozen length/hash, writes the decoded script exclusively to tmpfs,
    # verifies it again, then sources it. No OAuth or production action is embedded here.
    packed = base64.b64encode(zlib.compress(b64.encode("ascii"), 9)).decode("ascii")
    py = (
        "import base64,hashlib,os,stat,sys,zlib;"
        "p=sys.argv[1];x=sys.argv[2].encode('ascii');"
        "b=zlib.decompress(base64.b64decode(x));"
        f"assert len(b)=={EXPECTED_B64_LEN} and hashlib.sha256(b).hexdigest()=='{EXPECTED_B64_SHA256}';"
        "d=base64.b64decode(b,validate=True);"
        f"assert len(d)=={EXPECTED_DECODED_LEN} and hashlib.sha256(d).hexdigest()=='{EXPECTED_DECODED_SHA256}';"
        "fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400);"
        "f=os.fdopen(fd,'wb');f.write(d);f.flush();os.fsync(f.fileno());f.close();"
        "s=os.lstat(p);assert stat.S_ISREG(s.st_mode) and (s.st_mode&0o777)==0o400 and s.st_uid==os.getuid();"
        f"assert hashlib.sha256(open(p,'rb').read()).hexdigest()=='{EXPECTED_DECODED_SHA256}'"
    )
    target = "/dev/shm/multiverse-r1-stage1-phase-c-transport-step1.sh"
    action = (
        f"PHASE_C_STEP1_V17_PACKED='{packed}'; "
        f"/usr/local/python/current/bin/python -B -c \"{py}\" '{target}' \"$PHASE_C_STEP1_V17_PACKED\" && "
        "unset PHASE_C_STEP1_V17_PACKED && . '/dev/shm/multiverse-r1-stage1-phase-c-transport-step1.sh'"
    )
    return action


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("payload", type=Path)
    ap.add_argument("--metadata", action="store_true")
    args = ap.parse_args()
    raw = args.payload.read_bytes()
    b64 = verify_payload(raw)
    action = build_action(b64)
    if args.metadata:
        print(json.dumps({"action_bytes": len(action.encode()), "action_sha256": sha256(action.encode())}, sort_keys=True))
    else:
        print(action, end="")


if __name__ == "__main__":
    main()
