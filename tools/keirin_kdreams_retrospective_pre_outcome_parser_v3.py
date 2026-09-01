#!/usr/bin/env python3
"""Research-only offline parser for saved KDreams racedetail HTML.

Reads two semantically separated regions from the same immutable HTML artifact:
1) PRE table: the table headed by `直近4ヶ月の成績` / `競走得点`.
2) OUTCOME label: the dedicated result table headed by `着 順` / `車 番` / `選手名`.

The parser never reads payout tables into output and fail-closes on ambiguous/dead-heat
or active-car mismatches. Intended for retrospective development only.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, re
from pathlib import Path
from bs4 import BeautifulSoup


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_file(p: Path):
    soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
    title = clean(soup.title.get_text(" ", strip=True))
    canonical = soup.find("link", rel="canonical")
    url = canonical.get("href") if canonical else ""
    m = re.search(r"/racedetail/(\d+)/", url)
    if not m:
        raise ValueError("FAIL-CLOSED:no_race_id")
    race_id = m.group(1)
    dm = re.search(r"(20\d{2})年(\d{2})月(\d{2})日", title)
    rm = re.search(r" (\d{1,2})R ", title)
    if not dm or not rm:
        raise ValueError("FAIL-CLOSED:race_metadata")
    race_date = "-".join(dm.groups())
    race_no = int(rm.group(1))
    venue = title.split("競輪")[0]

    pre_table = None
    for t in soup.find_all("table"):
        tt = clean(t.get_text(" ", strip=True))
        if "直近4ヶ月の成績" in tt and "競走得点" in tt and "2連 対率" in tt:
            pre_table = t
            break
    if pre_table is None:
        raise ValueError("FAIL-CLOSED:no_pre_table")

    pre = []
    for tr in pre_table.find_all("tr"):
        cells = [clean(x.get_text(" ", strip=True)) for x in tr.find_all(["th", "td"])]
        ci = next((i for i,c in enumerate(cells) if re.fullmatch(r"[SA][123]", c)), None)
        if ci is None or ci < 1:
            continue
        cars = [int(c) for c in cells[:ci-1] if re.fullmatch(r"[1-9]", c)]
        if not cars:
            continue
        car_no = cars[-1]
        rider = cells[ci-1]
        style = cells[ci+1] if ci+1 < len(cells) and cells[ci+1] in ("逃","追","両") else None
        si = next((i for i in range(ci+1, len(cells)) if re.fullmatch(r"\d{2,3}\.\d{2}", cells[i])), None)
        if si is None:
            continue
        score = float(cells[si])
        vals = []
        for c in cells[si+1:]:
            if re.fullmatch(r"\d{1,2}", c):
                vals.append(int(c))
                if len(vals) == 6:
                    break
        if len(vals) != 6:
            continue
        S,B,nige,makuri,sashi,mark = vals
        pre.append({"race_id":race_id,"race_date":race_date,"venue":venue,"race_no":race_no,
                    "car_no":car_no,"rider_name_raw":rider,"class":cells[ci],"style":style,
                    "competition_score":score,"S":S,"B":B,"nige":nige,"makuri":makuri,
                    "sashi":sashi,"mark":mark,"source_url":url,
                    "evidence_role":"RETROSPECTIVE_PRE_DEVELOPMENT_ONLY"})
    by_car = {r["car_no"]: r for r in pre}
    pre = [by_car[k] for k in sorted(by_car)]
    if len(pre) < 5:
        raise ValueError(f"FAIL-CLOSED:pre_rows={len(pre)}")

    result_table = None
    for t in soup.find_all("table"):
        rows = t.find_all("tr")
        if not rows:
            continue
        hdr = clean(rows[0].get_text(" ", strip=True))
        if "着 順" in hdr and "車 番" in hdr and "選手名" in hdr and "級 班" not in hdr and "払戻" not in hdr:
            result_table = t
    if result_table is None:
        raise ValueError("FAIL-CLOSED:no_result_table")
    pairs = []
    for tr in result_table.find_all("tr")[1:]:
        cells = [clean(x.get_text(" ", strip=True)) for x in tr.find_all(["th", "td"])]
        ints = [int(c) for c in cells[:5] if re.fullmatch(r"[1-9]", c)]
        if len(ints) >= 2:
            pairs.append((ints[0], ints[1]))
    # Duplicate finishing positions indicate dead heat/ambiguity for ordered-label training.
    pos = [p for p,_ in pairs]
    if len(pos) != len(set(pos)):
        raise ValueError("FAIL-CLOSED:duplicate_finish_position")
    order = dict(pairs)
    top3 = [order.get(1), order.get(2), order.get(3)]
    if any(x is None for x in top3):
        raise ValueError("FAIL-CLOSED:top3_missing")
    active = set(by_car)
    if not set(top3).issubset(active):
        raise ValueError("FAIL-CLOSED:top3_not_in_pre_active_cars")
    outcome = {"race_id":race_id,"race_date":race_date,"venue":venue,"race_no":race_no,
               "finish_1":top3[0],"finish_2":top3[1],"finish_3":top3[2],
               "evidence_role":"RETROSPECTIVE_OUTCOME_LABEL_ONLY","payout_fields_included":False,
               "source_url":url}
    return pre, outcome


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("input_dir"); ap.add_argument("pre_csv"); ap.add_argument("outcome_jsonl"); ap.add_argument("receipt_json")
    a=ap.parse_args(); files=sorted(Path(a.input_dir).glob("*.html")); pre_rows=[]; outcomes=[]; rejects=[]
    for p in files:
        try:
            pre,out=parse_file(p); h=sha256(p)
            for r in pre: r["source_file_sha256"]=h
            out["source_file_sha256"]=h
            pre_rows.extend(pre); outcomes.append(out)
        except Exception as e:
            rejects.append({"file":p.name,"reason":str(e)})
    fields=["race_id","race_date","venue","race_no","car_no","rider_name_raw","class","style","competition_score","S","B","nige","makuri","sashi","mark","source_url","source_file_sha256","evidence_role"]
    with open(a.pre_csv,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(pre_rows)
    with open(a.outcome_jsonl,"w",encoding="utf-8") as f:
        for x in outcomes: f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n")
    receipt={"record":"KEIRIN_RETROSPECTIVE_PRE_OUTCOME_PARSE_RECEIPT_v3","input_files":len(files),"successful_races":len(outcomes),"rejected_files":len(rejects),"pre_rows":len(pre_rows),"rejects":rejects[:50],"result_used_as_feature":False,"payout_read_into_output":False,"network_access":False}
    Path(a.receipt_json).write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=="__main__": main()
