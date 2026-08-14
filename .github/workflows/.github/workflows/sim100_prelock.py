from __future__ import annotations
import csv, hashlib, io, json, os, re, sys, time, uuid
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

EXPECTED_UNIVERSE_SHA256 = "95754e7ac17cb91b12f619504d1be5e8a4ddc4f0e3734fa59671aea2e17eb043"
MARGIN = 0.35

ROOT = Path("SIM100_PRELOCK_ARTIFACT")
RAW = ROOT / "00_raw" / "sha256"
PRE_DIR = ROOT / "10_pre"
LOCK_DIR = ROOT / "30_prediction_lock"
AUDIT_DIR = ROOT / "audit"
for d in (RAW, PRE_DIR, LOCK_DIR, AUDIT_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Exact frozen Universe bytes loaded from a separate immutable file.
RACES_PATH = Path(__file__).with_name("races.csv")
RACES_CSV_BYTES = RACES_PATH.read_bytes()
RACES_CSV = RACES_CSV_BYTES.decode("utf-8")

POST = ("result","finish","rank","着順","払戻","payout","配当","失格","落車","棄権","確定着順","払戻金")
PRE_COLS = [
    "race_id","car_no","score","S","B","nige","makuri","sashi","mark",
    "win_rate","top2_rate","top3_rate","line_id","line_position","line_size",
    "num_lines","leading_competition","initiative_clarity","makuri_threat",
    "second_pressure","collapse_proxy"
]
PRE_ALLOWED = set(PRE_COLS)

VIEW_SLUG = {
    "pre": "3rentan",
    "exacta": "2shatan",
    "quinella": "2shahuku",
    "trio": "3renhuku",
}
VIEW_MARKER = {
    "pre": "競走得点",
    "exacta": "2車単",
    "quinella": "2車複",
    "trio": "3連複",
}

run_id = os.environ.get("GITHUB_RUN_ID") or str(uuid.uuid4())

def hbytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def hfile(p: Path) -> str:
    return hbytes(p.read_bytes())

def atomic_write(path: Path, b: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(b); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def immutable_csv(df: pd.DataFrame, path: Path):
    if path.exists():
        raise RuntimeError(f"immutable output already exists: {path}")
    tmp = Path(str(path)+".tmp")
    df.to_csv(tmp,index=False,lineterminator="\n")
    os.replace(tmp,path)
    Path(str(path)+".sha256").write_text(hfile(path)+"  "+path.name+"\n",encoding="utf-8")

def txt(n):
    return re.sub(r"\s+"," ",n.get_text(" ",strip=True)).strip() if n else ""

def assert_pre(df: pd.DataFrame):
    bad=set(df.columns)-PRE_ALLOWED
    if bad:
        raise RuntimeError(f"PRE unauthorized fields: {sorted(bad)}")
    for c in df.columns:
        if any(x.lower() in c.lower() for x in POST):
            raise RuntimeError(f"POST leakage in PRE column: {c}")
    if df.duplicated(["race_id","car_no"]).any():
        raise RuntimeError("duplicate race/car")
    if df["race_id"].nunique() > 100:
        raise RuntimeError("race count exceeds frozen universe")

def z(s):
    x=pd.to_numeric(s).astype(float)
    sd=x.std(ddof=0)
    return (x-x.mean())/(sd if sd else 1.0)

def softmax(x):
    x=x-x.max()
    e=np.exp(x)
    return e/e.sum()

class HybridV2:
    # Frozen coefficient formula.
    def probabilities(self,r):
        assert_pre(r)
        s=(
            .46*z(r.score)+.10*z(r.win_rate)+.10*z(r.top2_rate)+.06*z(r.top3_rate)
            +.05*z(r.makuri)+.04*z(r.sashi)+.03*z(r.nige)+.02*z(r.mark)
            +.10*z(r.line_size)-.035*r.line_position+.045*(r.line_position==1)
            +.055*z(r.makuri_threat)+.045*z(r.second_pressure)
            +.035*r.initiative_clarity-.045*r.collapse_proxy-.020*r.leading_competition
        )
        o=r[["race_id","car_no"]].copy()
        o["p_win"]=softmax(s.to_numpy(float))
        o["w"]=np.exp(s-s.max())
        return o

    def events(self,r,od):
        from itertools import permutations
        p=self.probabilities(r)
        cars=p.car_no.astype(int).tolist()
        w=p.w.to_numpy(float)
        J={}
        for a,b,c in permutations(range(len(cars)),3):
            J[(cars[a],cars[b],cars[c])] = (
                w[a]/w.sum()
                * w[b]/(w.sum()-w[a])
                * w[c]/(w.sum()-w[a]-w[b])
            )
        rows=[]
        for x in od.itertuples(index=False):
            combo=tuple(map(int,str(x.combination).split("-")))
            q=0.0
            if x.ticket_type=="exacta" and len(combo)==2:
                q=sum(v for k,v in J.items() if k[:2]==combo)
            elif x.ticket_type=="quinella" and len(combo)==2:
                q=sum(v for k,v in J.items() if set(k[:2])==set(combo))
            elif x.ticket_type=="trio" and len(combo)==3:
                q=sum(v for k,v in J.items() if set(k)==set(combo))
            if q>0:
                fair=1/q
                req=fair*(1+MARGIN)
                market=float(x.market_odds)
                rows.append(dict(
                    race_id=x.race_id,ticket_type=x.ticket_type,
                    combination=x.combination,probability=q,
                    fair_odds=fair,required_odds=req,market_odds=market,
                    ev=q*market-1,value_score=market/req,
                    gate_result="BET" if market>=req else "NO_BET",
                    virtual_stake=100 if market>=req else 0,
                    price_type=x.price_type,
                    price_timestamp=getattr(x,"price_timestamp",None)
                ))
        return pd.DataFrame(rows)

class PreOnlyETL:
    def __init__(self):
        self.s=requests.Session()
        self.s.headers.update({
            "User-Agent":"Mozilla/5.0 MultiverseResearch-SIM100/1.0",
            "Accept":"text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language":"ja,en-US;q=0.7,en;q=0.5",
        })
        self.provenance=[]

    def fetch_view(self,rid,base_url,view):
        slug=VIEW_SLUG[view]
        url=re.sub(r"/3rentan/$", f"/{slug}/", base_url)
        if url==base_url and view!="pre":
            raise RuntimeError(f"{rid}/{view}: URL routing failed")
        prep=self.s.prepare_request(requests.Request("GET",url))
        rhash=hbytes(json.dumps(
            {str(k).lower():str(v) for k,v in prep.headers.items()},
            sort_keys=True,separators=(",",":")
        ).encode())
        last=None
        for attempt in range(3):
            try:
                resp=self.s.send(prep,timeout=45,allow_redirects=True)
                last=resp
                if resp.status_code==200:
                    break
            except Exception:
                if attempt==2: raise
            time.sleep(1.5*(attempt+1))
        resp=last
        if resp is None or resp.status_code!=200:
            raise RuntimeError(f"{rid}/{view}: HTTP {getattr(resp,'status_code',None)}")
        if f"/{slug}/" not in urlparse(resp.url).path:
            raise RuntimeError(f"{rid}/{view}: unexpected final URL {resp.url}")
        payload=bytes(resp.content)
        if not payload:
            raise RuntimeError(f"{rid}/{view}: empty payload")
        text=payload.decode(resp.encoding or "utf-8",errors="ignore")
        if VIEW_MARKER[view] not in text:
            raise RuntimeError(f"{rid}/{view}: expected marker missing")
        digest=hbytes(payload)
        blob=RAW/digest[:2]/f"{digest}.bin"
        if not blob.exists():
            atomic_write(blob,payload)
        if blob.read_bytes()!=payload or hfile(blob)!=digest:
            raise RuntimeError(f"{rid}/{view}: raw persistence mismatch")
        self.provenance.append({
            "original_race_id":rid,
            "market_view":view,
            "source_url":url,
            "final_url":resp.url,
            "retrieved_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
            "acquisition_run_id":str(run_id),
            "http_method":"GET",
            "http_status":resp.status_code,
            "content_type":resp.headers.get("Content-Type",""),
            "content_encoding_observed":resp.headers.get("Content-Encoding",""),
            "canonical_payload_definition":"requests.Response.content (decompressed HTTP entity body)",
            "response_payload_sha256":digest,
            "byte_length":len(payload),
            "raw_blob_path":str(blob),
            "request_headers_sha256":rhash,
            "redirect_chain":[{"status":r.status_code,"url":r.url} for r in resp.history],
            "transport":f"requests/{requests.__version__}",
            "parser_version":"sim100-preonly-v2",
            "discrepancy_flag":False,
        })
        return payload

    def entrants(self,rid,payload):
        soup=BeautifulSoup(payload,"lxml")
        candidate=None
        for t in soup.find_all("table"):
            s=txt(t)
            if (
                "直近4ヶ月" in s
                and "競走得点" in s
                and ("2連 対率" in s or "2連対率" in s)
                and ("3連 対率" in s or "3連対率" in s)
            ):
                candidate=t
                break
        if candidate is None:
            raise RuntimeError(f"{rid}: entrant table not found")

        rows=[]
        for tr in candidate.find_all("tr"):
            cs=[txt(c) for c in tr.find_all(["td","th"])]
            profile_idx=next(
                (
                    i for i,c in enumerate(cs)
                    if re.search(r"/\d{1,2}/\d{2,3}$", c.replace(" ",""))
                ),
                None
            )
            if profile_idx is None:
                continue

            before=cs[max(0,profile_idx-3):profile_idx]
            car_candidates=[
                int(x)
                for c in before
                for x in re.findall(r"(?<!\d)([1-9])(?!\d)",c)
            ]
            if not car_candidates:
                continue
            car=car_candidates[-1]

            after=cs[profile_idx+1:]
            if len(after)<17:
                continue

            def num(s):
                s=s.replace(",","").replace("%","")
                if not re.fullmatch(r"-?\d+(?:\.\d+)?",s):
                    return None
                return float(s)

            vals=[num(x) for x in after[3:17]]
            if any(v is None for v in vals):
                continue

            score=vals[0]
            S,B,nige,makuri,sashi,mark,w,se,th,out,wr,t2,t3=vals[1:]
            rows.append(dict(
                race_id=rid,car_no=car,score=score,S=S,B=B,nige=nige,
                makuri=makuri,sashi=sashi,mark=mark,
                win_rate=wr,top2_rate=t2,top3_rate=t3
            ))

        d=(
            pd.DataFrame(rows)
            .drop_duplicates("car_no")
            .sort_values("car_no")
        )
        if not 5<=len(d)<=9:
            raise RuntimeError(f"{rid}: entrant count {len(d)}")
        return d,soup

    def scenario(self,d,soup):
        # Frozen parser/feature construction preserved from prior runner.
        valid=set(d.car_no.astype(int))
        body=soup.get_text(" ",strip=True)
        cand=[]
        for p in re.findall(r"(?<!\d)([1-9](?:\s*(?:-|－|→)\s*[1-9])+)(?!\d)",body):
            a=[int(x) for x in re.findall(r"[1-9]",p)]
            if len(a)>=2 and set(a)<=valid and a not in cand:
                cand.append(a)
        used=set(); lines=[]
        for a in sorted(cand,key=len,reverse=True):
            if not used.intersection(a):
                lines.append(a); used.update(a)
        for c in sorted(valid-used):
            lines.append([c])
        info={}
        for lid,a in enumerate(lines):
            for pos,c in enumerate(a):
                info[c]=(lid,pos,len(a))
        d=d.copy()
        d["line_id"]=d.car_no.map(lambda c:info[c][0])
        d["line_position"]=d.car_no.map(lambda c:info[c][1])
        d["line_size"]=d.car_no.map(lambda c:info[c][2])
        d["num_lines"]=len(lines)
        heads=pd.DataFrame([d[d.car_no==a[0]].iloc[0] for a in lines])
        active=int(((heads.B>=5)|(heads.nige>=3)).sum())
        comp=max(0,active-1)
        bs=sorted(heads.B.astype(float),reverse=True)
        clarity=(bs[0]-bs[1])/bs[0] if len(bs)>1 and bs[0]>0 else 1.0
        d["leading_competition"]=comp
        d["initiative_clarity"]=np.clip(clarity,0,1)
        d["makuri_threat"]=d.makuri+.5*d.B
        d["second_pressure"]=0.0
        m=d.line_position==1
        d.loc[m,"second_pressure"]=d.loc[m,"sashi"]+.5*d.loc[m,"mark"]
        d["collapse_proxy"]=comp*(1-np.clip(clarity,0,1))
        out=d[PRE_COLS].copy()
        assert_pre(out)
        return out

    def odds(self,rid,payload,expected_type):
        soup=BeautifulSoup(payload,"lxml")
        rows=[]

        entrants,_ = self.entrants(rid,payload)
        active=set(entrants.car_no.astype(int))

        if expected_type in ("exacta","quinella"):
            found={}
            for t in soup.find_all("table",class_="odds_table"):
                trs=t.find_all("tr")
                if len(trs)<3:
                    continue

                header_cells=trs[0].find_all(["td","th"])
                cols=[]
                for cell in header_cells:
                    v=txt(cell)
                    if re.fullmatch(r"[1-9]",v):
                        cols.append(int(v))
                if not cols:
                    continue

                for tr in trs[2:]:
                    cells=tr.find_all(["td","th"])
                    values=[txt(c).replace(",","") for c in cells]
                    if not values or not re.fullmatch(r"[1-9]",values[0]):
                        continue
                    rcar=int(values[0])

                    for ccar,ov in zip(cols,values[1:1+len(cols)]):
                        if rcar not in active or ccar not in active:
                            continue
                        if not re.fullmatch(r"\d+(?:\.\d+)?",ov):
                            continue
                        combo=(rcar,ccar)
                        if len(set(combo))<2:
                            continue
                        if expected_type=="quinella":
                            combo=tuple(sorted(combo))
                        found[combo]=float(ov)

            expected=(
                len(active)*(len(active)-1)
                if expected_type=="exacta"
                else len(active)*(len(active)-1)//2
            )
            if len(found)!=expected:
                raise RuntimeError(
                    f"{rid}/{expected_type}: odds coverage {len(found)}/{expected}"
                )

            for combo,odd in sorted(found.items()):
                rows.append(dict(
                    race_id=rid,ticket_type=expected_type,
                    combination="-".join(map(str,combo)),
                    market_odds=odd,
                    price_timestamp=None,
                    price_type="B_CLOSING_PRICE"
                ))

        elif expected_type=="trio":
            found={}
            for t in soup.find_all("table",class_="odds_table"):
                trs=t.find_all("tr")
                if len(trs)<2:
                    continue

                first=txt(trs[0])
                if not re.fullmatch(r"[1-9]",first):
                    continue
                a=int(first)
                current_b=None

                for tr in trs[2:]:
                    values=[
                        txt(c).replace(",","")
                        for c in tr.find_all(["td","th"])
                    ]

                    if (
                        len(values)>=3
                        and re.fullmatch(r"[1-9]",values[0])
                        and re.fullmatch(r"[1-9]",values[1])
                    ):
                        current_b=int(values[0])
                        c=int(values[1])
                        ov=values[2]
                    elif (
                        len(values)>=2
                        and current_b is not None
                        and re.fullmatch(r"[1-9]",values[0])
                    ):
                        c=int(values[0])
                        ov=values[1]
                    else:
                        continue

                    if not re.fullmatch(r"\d+(?:\.\d+)?",ov):
                        continue

                    combo=tuple(sorted((a,current_b,c)))
                    if len(set(combo))<3 or not set(combo)<=active:
                        continue
                    found[combo]=float(ov)

            n=len(active)
            expected=n*(n-1)*(n-2)//6
            if len(found)!=expected:
                raise RuntimeError(
                    f"{rid}/trio: odds coverage {len(found)}/{expected}"
                )

            for combo,odd in sorted(found.items()):
                rows.append(dict(
                    race_id=rid,ticket_type="trio",
                    combination="-".join(map(str,combo)),
                    market_odds=odd,
                    price_timestamp=None,
                    price_type="B_CLOSING_PRICE"
                ))
        else:
            raise RuntimeError(f"{rid}: unsupported odds type {expected_type}")

        d=pd.DataFrame(rows)
        if d.empty:
            raise RuntimeError(f"{rid}/{expected_type}: odds unavailable")
        return d

# -------- Exact Universe verification --------
universe_bytes=RACES_CSV_BYTES
observed_universe_sha=hbytes(universe_bytes)
if observed_universe_sha != EXPECTED_UNIVERSE_SHA256:
    raise RuntimeError(
        f"UNIVERSE SHA MISMATCH {observed_universe_sha} != {EXPECTED_UNIVERSE_SHA256}"
    )
races=list(csv.DictReader(io.StringIO(RACES_CSV)))
if len(races)!=100 or len({r["race_id"] for r in races})!=100:
    raise RuntimeError("Universe must contain exactly 100 unique races")
atomic_write(ROOT/"races.csv", universe_bytes)

etl=PreOnlyETL()
pre_frames=[]
odds_frames=[]
failures=[]
acquisition_status=[]

for i,r in enumerate(races,1):
    rid=r["race_id"]; base=r["url"]
    print(f"[SIM100 PRE {i:03d}/100] {rid}",flush=True)
    try:
        payloads={}
        hashes={}
        for view in ("pre","exacta","quinella","trio"):
            payloads[view]=etl.fetch_view(rid,base,view)
            hashes[view]=hbytes(payloads[view])
            time.sleep(0.20)
        if len(set(hashes.values())) != 4:
            raise RuntimeError(f"{rid}: duplicate market-view payload hash")
        entrants,soup=etl.entrants(rid,payloads["pre"])
        pre_frames.append(etl.scenario(entrants,soup))
        odds_frames.extend([
            etl.odds(rid,payloads["exacta"],"exacta"),
            etl.odds(rid,payloads["quinella"],"quinella"),
            etl.odds(rid,payloads["trio"],"trio"),
        ])
        acquisition_status.append({
            "race_id":rid,"status":"PASS",
            "pre_sha256":hashes["pre"],"exacta_sha256":hashes["exacta"],
            "quinella_sha256":hashes["quinella"],"trio_sha256":hashes["trio"]
        })
    except Exception as e:
        failures.append({"race_id":rid,"error":repr(e)})
        acquisition_status.append({"race_id":rid,"status":"MISSING_OR_FAILED","error":repr(e)})

(AUDIT_DIR/"provenance.jsonl").write_text(
    "".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in etl.provenance),
    encoding="utf-8"
)
(AUDIT_DIR/"acquisition_status.json").write_text(
    json.dumps(acquisition_status,ensure_ascii=False,indent=2),encoding="utf-8"
)
(AUDIT_DIR/"failures.json").write_text(
    json.dumps(failures,ensure_ascii=False,indent=2),encoding="utf-8"
)

# Strictly no substitution. If any race failed, preserve evidence and stop before Prediction Lock.
if failures:
    report={
        "status":"FAIL-CLOSED",
        "phase":"PRE_INGEST",
        "universe_sha256":observed_universe_sha,
        "universe_count":100,
        "successful_races":100-len(failures),
        "failed_races":len(failures),
        "replacement_races":0,
        "result_access":False,
        "payout_access":False,
        "prediction_lock_created":False,
    }
    (ROOT/"SIM100_PRELOCK_REPORT.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"
    )
    print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(2)

pre=pd.concat(pre_frames,ignore_index=True)
odds=pd.concat(odds_frames,ignore_index=True)
assert_pre(pre)
if pre["race_id"].nunique()!=100 or odds["race_id"].nunique()!=100:
    raise RuntimeError("100-race PRE/ODDS coverage not achieved")

immutable_csv(pre,PRE_DIR/"PRE_TABLE.csv")
immutable_csv(odds,PRE_DIR/"ODDS_TABLE.csv")

# Prediction Lock; RESULT/PAYOUT do not exist anywhere in this runner.
engine=HybridV2()
frames=[]
for i,(rid,rdf) in enumerate(pre.groupby("race_id",sort=False),1):
    print(f"[PRED LOCK {i:03d}/100] {rid}",flush=True)
    ev=engine.events(rdf,odds[odds.race_id==rid])
    if ev.empty:
        raise RuntimeError(f"{rid}: no modelled odds")
    frames.append(ev)
pred=pd.concat(frames,ignore_index=True)
if pred["race_id"].nunique()!=100:
    raise RuntimeError("Prediction lock must cover exactly 100 races")

lock_path=LOCK_DIR/"SIM100_PREDICTION_LOCK.csv"
immutable_csv(pred,lock_path)
lock_sha=hfile(lock_path)
lock_meta={
    "status":"PREDICTION_LOCKED",
    "sha256":lock_sha,
    "race_count":100,
    "universe_sha256":observed_universe_sha,
    "margin":MARGIN,
    "result_access":False,
    "payout_access":False,
    "scoring_performed":False,
    "price_quality":"B_CLOSING_PRICE",
}
(LOCK_DIR/"SIM100_PREDICTION_LOCK.json").write_text(
    json.dumps(lock_meta,ensure_ascii=False,indent=2),encoding="utf-8"
)

report={
    "status":"PASS",
    "phase":"PREDICTION_LOCK_COMPLETE",
    "universe_sha256":observed_universe_sha,
    "universe_count":100,
    "successful_races":100,
    "failed_races":0,
    "replacement_races":0,
    "pre_table_sha256":hfile(PRE_DIR/"PRE_TABLE.csv"),
    "odds_table_sha256":hfile(PRE_DIR/"ODDS_TABLE.csv"),
    "prediction_lock_sha256":lock_sha,
    "result_access":False,
    "payout_access":False,
    "scoring_performed":False,
}
(ROOT/"SIM100_PRELOCK_REPORT.json").write_text(
    json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8"
)
print(json.dumps(report,ensure_ascii=False,indent=2))

# Manifest, excluding itself.
manifest=[]
for p in sorted(x for x in ROOT.rglob("*") if x.is_file() and x.name!="ARTIFACT_MANIFEST.sha256"):
    manifest.append(f"{hfile(p)}  {p.relative_to(ROOT).as_posix()}")
(ROOT/"ARTIFACT_MANIFEST.sha256").write_text("\n".join(manifest)+"\n",encoding="utf-8")
