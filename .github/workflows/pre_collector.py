from __future__ import annotations
import argparse, csv, hashlib, json, os, re, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

POST_TERMS=("着順","払戻","配当","確定","result","payout","finish","rank")
RUN_ID=os.environ.get("GITHUB_RUN_ID") or str(uuid.uuid4())

def hbytes(b): return hashlib.sha256(b).hexdigest()
def hfile(p): return hbytes(p.read_bytes())

def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    with open(tmp,"wb") as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)

def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def assert_pre_columns(cols):
    for c in cols:
        low=c.lower()
        if any(t.lower() in low for t in POST_TERMS):
            raise RuntimeError(f"POST-like column prohibited: {c}")

def parse_kdreams_race_card(race_id,payload,prediction_timestamp):
    soup=BeautifulSoup(payload,"lxml")
    table=None
    for t in soup.find_all("table"):
        s=" ".join(t.stripped_strings)
        if "競走得点" in s and ("2連対率" in s or "2連 対率" in s):
            table=t; break
    if table is None:
        raise RuntimeError(f"{race_id}: entrant table not found")
    rows=[]
    for tr in table.find_all("tr"):
        text=[" ".join(x.stripped_strings) for x in tr.find_all(["td","th"])]
        # deliberately conservative: store row text only in raw-structured staging.
        # Feature extraction remains a separately frozen parser.
        if any(re.search(r"(?<!\d)[1-9](?!\d)", x) for x in text):
            rows.append({
                "race_id":race_id,
                "prediction_timestamp":prediction_timestamp,
                "row_text":" | ".join(text),
                "available_at":prediction_timestamp,
                "source_family":"kdreams_race_card"
            })
    if not rows:
        raise RuntimeError(f"{race_id}: no entrant-like rows")
    assert_pre_columns(rows[0].keys())
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--universe",required=True)
    ap.add_argument("--out",default="NEXTGEN_PRE_ARTIFACT")
    ap.add_argument("--limit",type=int,default=0)
    ap.add_argument("--prediction-timestamp",required=True,
                    help="ISO-8601 cutoff; all accepted features must be <= this time")
    args=ap.parse_args()

    pred=datetime.fromisoformat(args.prediction_timestamp.replace("Z","+00:00"))
    if pred.tzinfo is None: raise SystemExit("FAIL-CLOSED: prediction timestamp must include timezone")
    root=Path(args.out); raw=root/"00_raw"/"sha256"; audit=root/"audit"; stage=root/"10_staging"
    for d in (raw,audit,stage): d.mkdir(parents=True,exist_ok=True)

    rows=list(csv.DictReader(Path(args.universe).read_text(encoding="utf-8").splitlines()))
    if args.limit: rows=rows[:args.limit]
    s=requests.Session()
    s.headers.update({"User-Agent":"Mozilla/5.0 MultiverseResearch-NEXTGEN/1.0","Accept-Language":"ja,en;q=0.5"})
    prov=[]; staging=[]; failures=[]
    for i,r in enumerate(rows,1):
        rid,url=r["race_id"],r["url"]
        print(f"[NEXTGEN PRE {i:04d}/{len(rows):04d}] {rid}",flush=True)
        try:
            if "/result/" in url or "/payout" in url:
                raise RuntimeError("POST endpoint prohibited")
            resp=s.get(url,timeout=45,allow_redirects=True)
            if resp.status_code!=200: raise RuntimeError(f"HTTP {resp.status_code}")
            payload=bytes(resp.content)
            if not payload: raise RuntimeError("empty payload")
            dig=hbytes(payload); blob=raw/dig[:2]/f"{dig}.bin"
            if not blob.exists(): atomic(blob,payload)
            if hfile(blob)!=dig: raise RuntimeError("raw SHA persistence mismatch")
            retrieved=now_utc()
            # Historical replay caveat: retrieval time is NOT proof of historical availability.
            # Therefore source-derived available_at is not backfilled here.
            parsed=parse_kdreams_race_card(rid,payload,args.prediction_timestamp)
            staging.extend(parsed)
            prov.append({
                "race_id":rid,"source_url":url,"final_url":resp.url,
                "retrieved_at_utc":retrieved,"http_status":resp.status_code,
                "payload_sha256":dig,"byte_length":len(payload),
                "raw_blob_path":str(blob),"parser_version":"nextgen-pre-staging-v1",
                "acquisition_run_id":RUN_ID,
                "availability_proof":"NOT_YET_PROVEN_FOR_HISTORICAL_REPLAY",
                "eligible_for_model_training":False
            })
        except Exception as e:
            failures.append({"race_id":rid,"error":repr(e)})

    (audit/"provenance.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in prov),encoding="utf-8")
    (audit/"failures.json").write_text(json.dumps(failures,ensure_ascii=False,indent=2),encoding="utf-8")
    with open(stage/"PRE_STAGING.csv","w",newline="",encoding="utf-8") as f:
        fields=["race_id","prediction_timestamp","row_text","available_at","source_family"]
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n"); w.writeheader(); w.writerows(staging)

    report={
      "status":"PASS_STAGING_ONLY" if not failures else "FAIL-CLOSED",
      "races_requested":len(rows),"races_fetched":len(prov),"failed_races":len(failures),
      "training_eligibility":False,
      "reason":"Historical available_at proof not yet established. Staging cannot enter TRAIN.",
      "scoring_performed":False,"post_access":False
    }
    (root/"NEXTGEN_PRE_STAGING_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if failures: raise SystemExit(2)
if __name__=="__main__": main()
