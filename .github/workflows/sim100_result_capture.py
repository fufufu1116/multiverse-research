from __future__ import annotations

import csv, hashlib, io, json, os, re, time, uuid
from pathlib import Path
from urllib.parse import urlparse
import requests

EXPECTED_UNIVERSE_SHA256 = "95754e7ac17cb91b12f619504d1be5e8a4ddc4f0e3734fa59671aea2e17eb043"
EXPECTED_PREDICTION_LOCK_SHA256 = "bbabe47f75ee809cda2a2e9124be364b2213bbf343a4508c1be85039ecb85ca0"
EXPECTED_UNIVERSE_COUNT = 100

ROOT = Path("SIM100_RESULT_CAPTURE_ARTIFACT")
RAW = ROOT / "00_raw" / "sha256"
AUDIT = ROOT / "audit"
for d in (RAW, AUDIT):
    d.mkdir(parents=True, exist_ok=True)

RACES_PATH = Path(__file__).with_name("races.csv")
PRELOCK_ROOT = Path(os.environ.get("PRELOCK_ARTIFACT_DIR", "INPUT_PRELOCK"))
PRED_LOCK_PATH = PRELOCK_ROOT / "30_prediction_lock" / "SIM100_PREDICTION_LOCK.csv"
run_id = os.environ.get("GITHUB_RUN_ID") or str(uuid.uuid4())

def hbytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def hfile(p: Path) -> str:
    return hbytes(p.read_bytes())

def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def result_url_from_pre_url(pre_url: str) -> str:
    m = re.fullmatch(
        r"(https://keirin\.kdreams\.jp/gamboo/keirin-kaisai/race-card/)odds/"
        r"(\d{10})/(\d{14})/(\d{2})/3rentan/",
        pre_url,
    )
    if not m:
        raise RuntimeError(f"unsupported frozen URL shape: {pre_url}")
    return f"{m.group(1)}result/{m.group(2)}/{m.group(3)}/{m.group(4)}/"

def expected_identity_from_url(pre_url: str):
    m = re.search(r"/odds/(\d{10})/(\d{14})/(\d{2})/3rentan/$", pre_url)
    if not m:
        raise RuntimeError(f"cannot derive race identity from: {pre_url}")
    return m.group(1), m.group(2), m.group(3)

universe_bytes = RACES_PATH.read_bytes()
universe_sha = hbytes(universe_bytes)
if universe_sha != EXPECTED_UNIVERSE_SHA256:
    raise RuntimeError(f"UNIVERSE SHA MISMATCH {universe_sha} != {EXPECTED_UNIVERSE_SHA256}")

races = list(csv.DictReader(io.StringIO(universe_bytes.decode("utf-8"))))
if len(races) != EXPECTED_UNIVERSE_COUNT:
    raise RuntimeError(f"Universe count {len(races)} != {EXPECTED_UNIVERSE_COUNT}")
if len({r["race_id"] for r in races}) != EXPECTED_UNIVERSE_COUNT:
    raise RuntimeError("Universe does not contain exactly 100 unique race_id values")

if not PRED_LOCK_PATH.exists():
    raise RuntimeError(f"approved Prediction Lock missing: {PRED_LOCK_PATH}")
lock_sha = hfile(PRED_LOCK_PATH)
if lock_sha != EXPECTED_PREDICTION_LOCK_SHA256:
    raise RuntimeError(f"PREDICTION LOCK SHA MISMATCH {lock_sha} != {EXPECTED_PREDICTION_LOCK_SHA256}")

atomic_write(ROOT / "races.csv", universe_bytes)
atomic_write(ROOT / "SIM100_PREDICTION_LOCK.csv", PRED_LOCK_PATH.read_bytes())

session = requests.Session()
session.headers.update({
    "User-Agent":"Mozilla/5.0 MultiverseResearch-SIM100-ResultCapture/1.0",
    "Accept":"text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language":"ja,en-US;q=0.7,en;q=0.5",
})

provenance, status_rows, failures = [], [], []

for i, r in enumerate(races, 1):
    rid, pre_url = r["race_id"], r["url"]
    print(f"[RESULT/PAYOUT CAPTURE {i:03d}/100] {rid}", flush=True)
    try:
        expected_meeting, expected_day, expected_race = expected_identity_from_url(pre_url)
        url = result_url_from_pre_url(pre_url)
        prepared = session.prepare_request(requests.Request("GET", url))
        request_headers_sha256 = hbytes(json.dumps(
            {str(k).lower():str(v) for k,v in prepared.headers.items()},
            sort_keys=True, separators=(",",":")
        ).encode())

        response, last_exc = None, None
        for attempt in range(3):
            try:
                response = session.send(prepared, timeout=45, allow_redirects=True)
                if response.status_code == 200:
                    break
            except Exception as exc:
                last_exc = exc
            time.sleep(1.5*(attempt+1))

        if response is None:
            raise RuntimeError(f"network failure: {last_exc!r}")
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}")

        expected_fragment = f"/result/{expected_meeting}/{expected_day}/{expected_race}/"
        if expected_fragment not in urlparse(response.url).path:
            raise RuntimeError(f"unexpected final URL: {response.url}")

        payload = bytes(response.content)
        if not payload:
            raise RuntimeError("empty RESULT/PAYOUT payload")

        text = payload.decode(response.encoding or "utf-8", errors="ignore")
        if "結果・払戻金" not in text and "結果･払戻金" not in text:
            raise RuntimeError("RESULT/PAYOUT marker missing")
        if "レース結果確定までお待ちください" in text:
            raise RuntimeError("race result not finalized")

        digest = hbytes(payload)
        blob = RAW / digest[:2] / f"{digest}.bin"
        if not blob.exists():
            atomic_write(blob, payload)
        if blob.read_bytes()!=payload or hfile(blob)!=digest:
            raise RuntimeError("raw persistence mismatch")

        provenance.append({
            "race_id":rid,
            "source_url":url,
            "final_url":response.url,
            "retrieved_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "acquisition_run_id":str(run_id),
            "http_method":"GET",
            "http_status":response.status_code,
            "content_type":response.headers.get("Content-Type",""),
            "content_encoding_observed":response.headers.get("Content-Encoding",""),
            "canonical_payload_definition":"requests.Response.content (decompressed HTTP entity body)",
            "payload_sha256":digest,
            "byte_length":len(payload),
            "raw_blob_path":str(blob),
            "request_headers_sha256":request_headers_sha256,
            "redirect_chain":[{"status":x.status_code,"url":x.url} for x in response.history],
            "transport":f"requests/{requests.__version__}",
            "parser_version":"capture-only-no-result-parser-v1",
            "result_access":True,
            "payout_access":True,
            "scoring_performed":False,
        })
        status_rows.append({"race_id":rid,"status":"PASS","payload_sha256":digest,"byte_length":len(payload)})
    except Exception as exc:
        failures.append({"race_id":rid,"error":repr(exc)})
        status_rows.append({"race_id":rid,"status":"MISSING_OR_FAILED","error":repr(exc)})

(AUDIT/"provenance.jsonl").write_text(
    "".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in provenance),
    encoding="utf-8"
)
(AUDIT/"acquisition_status.json").write_text(json.dumps(status_rows,ensure_ascii=False,indent=2),encoding="utf-8")
(AUDIT/"failures.json").write_text(json.dumps(failures,ensure_ascii=False,indent=2),encoding="utf-8")

report = {
    "status":"PASS" if not failures else "FAIL-CLOSED",
    "phase":"RESULT_PAYOUT_RAW_CAPTURE",
    "universe_sha256":universe_sha,
    "prediction_lock_sha256":lock_sha,
    "universe_count":EXPECTED_UNIVERSE_COUNT,
    "successful_races":EXPECTED_UNIVERSE_COUNT-len(failures),
    "failed_races":len(failures),
    "replacement_races":0,
    "result_access":True,
    "payout_access":True,
    "result_parsing_performed":False,
    "payout_parsing_performed":False,
    "scoring_performed":False,
}
(ROOT/"SIM100_RESULT_CAPTURE_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))

manifest=[]
for p in sorted(x for x in ROOT.rglob("*") if x.is_file() and x.name!="ARTIFACT_MANIFEST.sha256"):
    manifest.append(f"{hfile(p)}  {p.relative_to(ROOT).as_posix()}")
(ROOT/"ARTIFACT_MANIFEST.sha256").write_text("\n".join(manifest)+"\n",encoding="utf-8")

if failures:
    raise SystemExit(2)
