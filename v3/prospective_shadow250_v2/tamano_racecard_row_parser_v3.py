#!/usr/bin/env python3
"""
Shadow250-v2 Tamano deterministic PRE row parser v3.

Candidate-only, NOT ACTIVE.

Live source validation proved that the allowed PRE clips do not expose a usable
meeting/event date string. Therefore v3 binds race_date to official transport
provenance instead of inventing an in-PDF date:
- official https://www.tamano-keirin.jp/wp-content/uploads/... PDF URL;
- URL basename begins with the exact YYYYMMDD race_date;
- caller-supplied raw SHA-256 must exactly match the bytes parsed;
- upstream selection rule must require this URL to be an exact href discovered
  through the frozen Tamano /racepdf/ discovery path.

All PRE-region, row geometry, active-entry, class/program, and five predictive
field ownership semantics are unchanged from parser v2.
"""
import fitz, re, unicodedata, hashlib
import pandas as pd
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse

W, H, TOL = 1190.55, 841.88, 1.0
PRE_CLIPS = {0: fitz.Rect(610.0, 0.0, W, H), 1: fitz.Rect(0.0, 0.0, W, 720.0)}
POST_SENTINELS = ["成績表","払戻","発売金額","２車単","2車単","３連単","3連単","ワイド","着順","風速","合計"]
PREFS=["北海道","青森","岩手","宮城","秋田","山形","福島","茨城","栃木","群馬","埼玉","千葉","東京","神奈川","新潟","富山","石川","福井","山梨","長野","岐阜","静岡","愛知","三重","滋賀","京都","大阪","兵庫","奈良","和歌山","鳥取","島根","岡山","広島","山口","徳島","香川","愛媛","高知","福岡","佐賀","長崎","熊本","大分","宮崎","鹿児島","沖縄"]
CAR_MAP={chr(0xE523+i):i for i in range(1,8)}
WITHDRAW_TOKENS=("欠場","欠","除外","取消","欠車")
TAMANO_HOST="www.tamano-keirin.jp"
PDF_PREFIX="/wp-content/uploads/"

RACE_SPECS=[]
for b in range(4): RACE_SPECS.append((0,609.6,1+b,220+147.4*b,345+147.4*b))
for b in range(4):
    RACE_SPECS.append((1,0.0,5+b,38+164.4*b,165+164.4*b))
    RACE_SPECS.append((1,603.8,9+b,38+164.4*b,165+164.4*b))
RACE_SPECS=sorted(RACE_SPECS,key=lambda x:x[2])

class FailClosed(RuntimeError): pass

def norm(s):
    s=unicodedata.normalize("NFKC",str(s)); s=unicodedata.normalize("NFC",s)
    return "".join(ch for ch in s if not ch.isspace())

def rider_key(name,pref,term):
    return hashlib.sha256(f"{norm(name)}|{norm(pref)}|{int(term)}".encode()).hexdigest()

def _validate_transport_binding(path,race_date,source_url,expected_raw_sha256):
    try: expected=date.fromisoformat(str(race_date))
    except Exception: raise FailClosed("REJECT_RACE_DATE invalid external ISO date")
    u=urlparse(str(source_url))
    if u.scheme!="https" or u.netloc!=TAMANO_HOST or u.fragment or u.query:
        raise FailClosed("REJECT_TRANSPORT_BINDING origin/query")
    if not u.path.startswith(PDF_PREFIX) or not u.path.lower().endswith(".pdf"):
        raise FailClosed("REJECT_TRANSPORT_BINDING pdf path")
    basename=unquote(u.path.rsplit("/",1)[-1])
    yyyymmdd=expected.strftime("%Y%m%d")
    if not basename.startswith(yyyymmdd):
        raise FailClosed(f"REJECT_TRANSPORT_BINDING basename={basename} expected_prefix={yyyymmdd}")
    if not re.fullmatch(r"[0-9a-f]{64}",str(expected_raw_sha256)):
        raise FailClosed("REJECT_TRANSPORT_BINDING invalid expected sha256")
    raw=Path(path).read_bytes(); got=hashlib.sha256(raw).hexdigest()
    if got!=str(expected_raw_sha256):
        raise FailClosed(f"REJECT_TRANSPORT_BINDING raw sha mismatch got={got}")
    return expected.isoformat(),got,basename

def _validate_template_and_pre_clips(doc):
    if len(doc)!=2: raise FailClosed("REJECT_TEMPLATE pages")
    for p in doc:
        if abs(p.rect.width-W)>TOL or abs(p.rect.height-H)>TOL: raise FailClosed("REJECT_TEMPLATE dimensions")
    clip_text={}
    for pi,rect in PRE_CLIPS.items():
        text=norm(doc[pi].get_text("text",clip=rect)); hits={s:text.count(norm(s)) for s in POST_SENTINELS}
        if any(hits.values()): raise FailClosed(f"HALT_POST_SENTINEL page={pi+1} hits={hits}")
        clip_text[pi]=text
    return clip_text

def _race_block_words(words,ox,ymin,ymax): return [w for w in words if ox<=w[0]<=ox+590 and ymin<=w[1]<=ymax]

def _field_size(block_words):
    text=norm("".join(w[4] for w in sorted(block_words,key=lambda z:(z[1],z[0]))))
    vals=[int(x) for x in re.findall(r"[\(（](\d)車立[\)）]",text)]
    if vals!=[7]: raise FailClosed(f"REJECT_FIELD_SIZE values={vals}")
    return 7

def _program_label(block_words):
    candidates=[]
    for wg in block_words:
        tg=norm(wg[4])
        if "級" not in tg: continue
        m=re.fullmatch(r"([ASL])級",tg)
        if m: candidates.append(m.group(1)); continue
        left=[]; gy=(wg[1]+wg[3])/2
        for w in block_words:
            t=norm(w[4])
            if t not in {"A","S","L"}: continue
            wy=(w[1]+w[3])/2
            if abs(wy-gy)<=8 and w[2]<=wg[0]+4 and wg[0]-w[2]<=45: left.append((wg[0]-w[2],t))
        if left: left.sort(); candidates.append(left[0][1])
    unique=sorted(set(candidates))
    if len(unique)!=1: raise FailClosed(f"REJECT_PROGRAM_LABEL candidates={candidates}")
    return unique[0]

def _validate_program_classes(program,classes):
    s=set(classes)
    if program=="S": ok=bool(s) and s<={"SS","S1","S2"}; variant="S"
    elif program=="A":
        if s=={"A3"}: ok=True; variant="A3"
        elif bool(s) and s<={"A1","A2"}: ok=True; variant="A12"
        else: ok=False; variant=None
    elif program=="L": ok=(s=={"L1"}); variant="L1"
    else: ok=False; variant=None
    if not ok: raise FailClosed(f"PRE_INELIGIBLE_SOURCE_GAP class_program program={program} classes={sorted(s)}")
    return variant

def _current_row_status(words,ox,cy):
    strip=[w for w in words if ox+70<=w[0]<=ox+330 and cy-6<=w[1]<=cy+15]
    text=norm("".join(w[4] for w in sorted(strip,key=lambda z:(z[1],z[0])))); hits=[t for t in WITHDRAW_TOKENS if t in text]
    if hits: raise FailClosed(f"PRE_INELIGIBLE_SOURCE_GAP current-entry status={hits}")
    return "ACTIVE_PENDING_RACE_CARDINALITY_GATE"

def parse_tamano_pdf(path,race_date,source_url,expected_raw_sha256):
    race_date,raw_sha,basename=_validate_transport_binding(path,race_date,source_url,expected_raw_sha256)
    doc=fitz.open(path); _validate_template_and_pre_clips(doc)
    rows=[]; race_meta={}
    for pi,ox,rno,ymin,ymax in RACE_SPECS:
        words=doc[pi].get_text("words",clip=PRE_CLIPS[pi]); block=_race_block_words(words,ox,ymin,ymax)
        size=_field_size(block); program=_program_label(block)
        cars=sorted((CAR_MAP[w[4]],w) for w in words if w[4] in CAR_MAP and ox+75<=w[0]<=ox+90 and ymin<=w[1]<=ymax)
        if [c for c,_ in cars]!=list(range(1,8)): raise FailClosed(f"PRE_INELIGIBLE_SOURCE_GAP car_glyph race={rno}")
        if len(cars)!=size: raise FailClosed(f"PRE_INELIGIBLE_SOURCE_GAP active_count race={rno} field_size={size} cars={len(cars)}")
        race_rows=[]
        for car,wcar in cars:
            cy=wcar[1]; _current_row_status(words,ox,cy)
            def ws(xlo,xhi,ylo,yhi): return [w for w in words if ox+xlo<=w[0]<=ox+xhi and cy+ylo<=w[1]<=cy+yhi]
            ct="".join(norm(w[4]) for w in sorted(ws(104,114,-4,13),key=lambda z:(z[1],z[0]))); ct="".join(ch for ch in ct if ch in "ASL0123456789")
            m=re.search(r"(SS|S[12]|A[123]|L1)",ct)
            if not m: raise FailClosed(f"REJECT_CLASS race={rno} car={car}")
            cls=m.group(1)
            nw=[w for w in ws(112,195,0,10) if re.search(r"[\u3400-\u9fff々ヶ]",w[4])]
            if not nw: raise FailClosed(f"REJECT_NAME race={rno} car={car}")
            name=norm(max(nw,key=lambda w:(len(norm(w[4])),w[2]-w[0]))[4])
            pt=norm("".join(w[4] for w in sorted(ws(203,246,-1,10),key=lambda z:z[0]))); pref=term=None
            for pr in sorted(PREFS,key=len,reverse=True):
                if pt.startswith(pr) and re.fullmatch(r"\d{1,3}",pt[len(pr):]): pref=pr; term=int(pt[len(pr):]); break
            if pref is None: raise FailClosed(f"REJECT_PREF_TERM race={rno} car={car}")
            score=next((float(norm(w[4])) for w in ws(337,366,-4,5) if re.fullmatch(r"\d{2,3}\.\d{2}",norm(w[4]))),None)
            if score is None: raise FailClosed(f"REJECT_SCORE race={rno} car={car}")
            qr=None
            for w in ws(338,366,3,13):
                t=norm(w[4])
                if re.fullmatch(r"(?:\d\.\d{3}|\.\d{3})",t): qr=float(t if not t.startswith(".") else "0"+t); break
            if qr is None or not 0<=qr<=1: raise FailClosed(f"REJECT_RATE race={rno} car={car}")
            def intfield(a,b):
                for w in ws(a,b,-1,10):
                    t=norm(w[4])
                    if re.fullmatch(r"\d{1,2}",t): return int(t)
                return None
            S=intfield(412,423); B=intfield(423,434)
            if S is None or B is None: raise FailClosed(f"REJECT_SB race={rno} car={car}")
            rid=f"{race_date.replace('-','')}_61_tamano_{rno:02d}R"
            race_rows.append(dict(race_id=rid,race_date=race_date,venue="玉野",venue_code="61",race_no=rno,car_no=car,
                rider_id=rider_key(name,pref,term),rider_name=name,prefecture=pref,term=term,
                **{"class":cls,"score":score,"S":S,"B":B,"quinella_rate":qr,"withdrawn":False,
                   "active_status_basis":"FIELD_SIZE_7+CAR_ANCHOR_7+COMPLETE_CURRENT_ROW+NO_CURRENT_STATUS_TOKEN",
                   "transport_event_day_binding":"OFFICIAL_DISCOVERY_EXACT_HREF_DATE_PREFIX+RAW_SHA256",
                   "transport_pdf_raw_sha256":raw_sha,"transport_pdf_basename":basename}))
        variant=_validate_program_classes(program,[r["class"] for r in race_rows])
        for r in race_rows: r["race_program"]=variant
        race_meta[rno]={"program":variant,"field_size":size}; rows.extend(race_rows)
    df=pd.DataFrame(rows).sort_values(["race_no","car_no"]).reset_index(drop=True)
    if len(df)!=84 or df.race_id.nunique()!=12: raise FailClosed("REJECT_COVERAGE")
    for rno,g in df.groupby("race_no"):
        if g.car_no.tolist()!=list(range(1,8)): raise FailClosed(f"REJECT_CAR_SET {rno}")
        if g.rider_id.duplicated().any(): raise FailClosed(f"REJECT_DUP_RIDER {rno}")
        if len(g)!=race_meta[rno]["field_size"]: raise FailClosed(f"PRE_INELIGIBLE_SOURCE_GAP active_count_final {rno}")
    return df

def synthetic_tests():
    good=[("S",["SS","S1","S2"],"S"),("S",["S2"]*7,"S"),("A",["A1","A2"],"A12"),("A",["A3"]*7,"A3"),("L",["L1"]*7,"L1")]
    for p,c,want in good: assert _validate_program_classes(p,c)==want
    bad=[("A",["A3","A2"]),("A",["A1","S2"]),("S",["S2","A1"]),("L",["L1","A3"]),("A",["L1"])]
    for p,c in bad:
        try: _validate_program_classes(p,c); raise AssertionError((p,c))
        except FailClosed: pass
    # Transport binding negatives that do not require network.
    import tempfile
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"abc"); f.flush(); sha=hashlib.sha256(b"abc").hexdigest()
        day,got,base=_validate_transport_binding(f.name,"2026-07-24","https://www.tamano-keirin.jp/wp-content/uploads/2026/07/20260724-1.pdf",sha)
        assert day=="2026-07-24" and got==sha and base=="20260724-1.pdf"
        for bad_url in ["http://www.tamano-keirin.jp/wp-content/uploads/20260724.pdf","https://evil.example/wp-content/uploads/20260724.pdf","https://www.tamano-keirin.jp/wp-content/uploads/20260725.pdf"]:
            try: _validate_transport_binding(f.name,"2026-07-24",bad_url,sha); raise AssertionError(bad_url)
            except FailClosed: pass
    return {"status":"PASS","network_used":False}

if __name__=="__main__":
    import argparse,json
    ap=argparse.ArgumentParser(); ap.add_argument("--synthetic",action="store_true"); ap.add_argument("--pdf"); ap.add_argument("--race-date"); ap.add_argument("--source-url"); ap.add_argument("--raw-sha256")
    args=ap.parse_args()
    if args.synthetic: print(json.dumps(synthetic_tests(),ensure_ascii=False))
    elif all([args.pdf,args.race_date,args.source_url,args.raw_sha256]): print(parse_tamano_pdf(args.pdf,args.race_date,args.source_url,args.raw_sha256).to_json(orient="records",force_ascii=False))
    else: raise SystemExit("FAIL_CLOSED use --synthetic or --pdf ... --race-date ... --source-url ... --raw-sha256 ...")
