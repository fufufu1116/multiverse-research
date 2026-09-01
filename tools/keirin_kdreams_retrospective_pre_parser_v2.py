#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json,re
from pathlib import Path
from bs4 import BeautifulSoup

def txt(n): return re.sub(r"\s+"," ",n.get_text(" ",strip=True)).strip() if n else ""
def sha256_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def parse_meta(soup):
    title=txt(soup.title)
    canonical=soup.find("link",rel="canonical")
    url=canonical.get("href") if canonical else ""
    m=re.search(r"/racedetail/(\d{12,})/",url)
    if not m: raise ValueError("FAIL-CLOSED: no racedetail race id")
    rid=m.group(1)
    dm=re.search(r"(20\d{2})年(\d{2})月(\d{2})日",title)
    rm=re.search(r"\b(\d{1,2})R\b",title)
    venue=title.split("競輪",1)[0].strip() if "競輪" in title else None
    if not dm or not rm or not venue: raise ValueError("FAIL-CLOSED: meta missing")
    return dict(race_id=rid,race_date=f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}",race_no=int(rm.group(1)),venue=venue,source_url=url)

def parse_pre(path):
    soup=BeautifulSoup(path.read_text(encoding="utf-8",errors="replace"),"html.parser")
    meta=parse_meta(soup)
    table=None
    for t in soup.find_all("table"):
        s=txt(t)
        if "選手名" in s and all(k in s for k in ("競走得点","S","B","逃","捲","差","マ")):
            table=t;break
    if table is None: raise ValueError("FAIL-CLOSED: PRE table missing")
    out=[]
    for tr in table.find_all("tr"):
        cells=[txt(x) for x in tr.find_all(["th","td"])]
        class_idx=next((i for i,x in enumerate(cells) if re.fullmatch(r"[SA][123]",x)),None)
        if class_idx is None or class_idx+9>=len(cells): continue
        style=cells[class_idx+1]
        if style not in ("逃","追","両"): continue
        rider_raw=cells[class_idx-1]
        car_candidates=[int(x) for x in cells[:class_idx-1] if re.fullmatch(r"[1-9]",x)]
        if not car_candidates: raise ValueError("FAIL-CLOSED: car missing")
        car=car_candidates[-1]
        try:
            score=float(cells[class_idx+3])
            vals=list(map(int,cells[class_idx+4:class_idx+10]))
        except Exception as e:
            raise ValueError(f"FAIL-CLOSED: feature parse car={car}: {e}")
        if len(vals)!=6: raise ValueError(f"FAIL-CLOSED: six PRE counts missing car={car}")
        S,B,nige,makuri,sashi,mark=vals
        out.append({**meta,"car_no":car,"rider_name_raw":rider_raw,"class":cells[class_idx],"style":style,
                    "competition_score":score,"S":S,"B":B,"nige":nige,"makuri":makuri,"sashi":sashi,"mark":mark,
                    "source_file_sha256":sha256_file(path),"evidence_role":"RETROSPECTIVE_PRE_DEVELOPMENT_ONLY"})
    by={r["car_no"]:r for r in out}
    if len(by)!=len(out): raise ValueError("FAIL-CLOSED: duplicate car")
    cars=sorted(by)
    if len(cars)<5 or cars!=list(range(1,max(cars)+1)): raise ValueError(f"FAIL-CLOSED: active-car continuity {cars}")
    return [by[c] for c in cars]

def main():
    ap=argparse.ArgumentParser();ap.add_argument("input_dir");ap.add_argument("pre_csv");ap.add_argument("receipt_json")
    a=ap.parse_args(); files=sorted(Path(a.input_dir).glob("*.html"))
    rows=[]; failures=[]
    for p in files:
        try: rows.extend(parse_pre(p))
        except Exception as e: failures.append({"file":p.name,"error":str(e)})
    fields=["race_id","race_date","venue","race_no","car_no","rider_name_raw","class","style","competition_score","S","B","nige","makuri","sashi","mark","source_url","source_file_sha256","evidence_role"]
    with open(a.pre_csv,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    receipt={"record":"KEIRIN_KDREAMS_RETROSPECTIVE_PRE_PARSE_RECEIPT_v2","status":"PASS_WITH_REJECTIONS" if failures else "PASS",
             "input_html_files":len(files),"successful_races":len({r["race_id"] for r in rows}),"pre_rows":len(rows),
             "rejected_files":len(failures),"failure_examples":failures[:20],"result_access":False,"payout_access":False,"network_access":False}
    Path(a.receipt_json).write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
