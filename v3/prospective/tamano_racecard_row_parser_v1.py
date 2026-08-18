#!/usr/bin/env python3
import fitz,re,unicodedata,hashlib,pandas as pd
PREFS=["北海道","青森","岩手","宮城","秋田","山形","福島","茨城","栃木","群馬","埼玉","千葉","東京","神奈川","新潟","富山","石川","福井","山梨","長野","岐阜","静岡","愛知","三重","滋賀","京都","大阪","兵庫","奈良","和歌山","鳥取","島根","岡山","広島","山口","徳島","香川","愛媛","高知","福岡","佐賀","長崎","熊本","大分","宮崎","鹿児島","沖縄"]
CAR_MAP={chr(0xE523+i):i for i in range(1,8)}
RACE_SPECS=[]
for b in range(4): RACE_SPECS.append((0,609.6,1+b,220+147.4*b,345+147.4*b))
for b in range(4):
    RACE_SPECS.append((1,0.0,5+b,38+164.4*b,165+164.4*b))
    RACE_SPECS.append((1,603.8,9+b,38+164.4*b,165+164.4*b))
RACE_SPECS=sorted(RACE_SPECS,key=lambda x:x[2])
def norm(s):
    s=unicodedata.normalize("NFKC",str(s)); s=unicodedata.normalize("NFC",s)
    return "".join(ch for ch in s if not ch.isspace())
def rider_key(name,pref,term):
    return hashlib.sha256(f"{norm(name)}|{norm(pref)}|{int(term)}".encode()).hexdigest()
def parse_tamano_pdf(path,race_date):
    doc=fitz.open(path)
    if len(doc)!=2: raise RuntimeError("REJECT_TEMPLATE pages")
    for p in doc:
        if abs(p.rect.width-1190.55)>1 or abs(p.rect.height-841.88)>1: raise RuntimeError("REJECT_TEMPLATE dimensions")
    rows=[]
    for pi,ox,rno,ymin,ymax in RACE_SPECS:
        words=doc[pi].get_text("words")
        cars=sorted((CAR_MAP[w[4]],w) for w in words if w[4] in CAR_MAP and ox+75<=w[0]<=ox+90 and ymin<=w[1]<=ymax)
        if [c for c,_ in cars]!=list(range(1,8)): raise RuntimeError(f"REJECT_CAR_GLYPH race={rno}")
        for car,wcar in cars:
            cy=wcar[1]
            def ws(xlo,xhi,ylo,yhi): return [w for w in words if ox+xlo<=w[0]<=ox+xhi and cy+ylo<=w[1]<=cy+yhi]
            ct="".join(norm(w[4]) for w in sorted(ws(104,114,-4,13),key=lambda z:(z[1],z[0])))
            ct="".join(ch for ch in ct if ch in "ASL0123456789")
            m=re.search(r"(SS|S[12]|A[123]|L1)",ct)
            if not m: raise RuntimeError(f"REJECT_CLASS race={rno} car={car}")
            cls=m.group(1)
            nw=[w for w in ws(112,195,0,10) if re.search(r"[\u3400-\u9fff々ヶ]",w[4])]
            if not nw: raise RuntimeError(f"REJECT_NAME race={rno} car={car}")
            name=norm(max(nw,key=lambda w:(len(norm(w[4])),w[2]-w[0]))[4])
            pt=norm("".join(w[4] for w in sorted(ws(203,246,-1,10),key=lambda z:z[0])))
            pref=term=None
            for pr in sorted(PREFS,key=len,reverse=True):
                if pt.startswith(pr) and re.fullmatch(r"\d{1,3}",pt[len(pr):]):
                    pref=pr; term=int(pt[len(pr):]); break
            if pref is None: raise RuntimeError(f"REJECT_PREF_TERM race={rno} car={car}")
            score=next((float(norm(w[4])) for w in ws(337,366,-4,5) if re.fullmatch(r"\d{2,3}\.\d{2}",norm(w[4]))),None)
            if score is None: raise RuntimeError(f"REJECT_SCORE race={rno} car={car}")
            qr=None
            for w in ws(338,366,3,13):
                t=norm(w[4])
                if re.fullmatch(r"(?:\d\.\d{3}|\.\d{3})",t): qr=float(t if not t.startswith(".") else "0"+t); break
            if qr is None or not 0<=qr<=1: raise RuntimeError(f"REJECT_RATE race={rno} car={car}")
            def intfield(a,b):
                for w in ws(a,b,-1,10):
                    t=norm(w[4])
                    if re.fullmatch(r"\d{1,2}",t): return int(t)
                return None
            S=intfield(412,423); B=intfield(423,434)
            if S is None or B is None: raise RuntimeError(f"REJECT_SB race={rno} car={car}")
            race_id=f"{race_date.replace('-','')}_61_tamano_{rno:02d}R"
            rows.append(dict(race_id=race_id,race_date=race_date,venue="玉野",venue_code="61",race_no=rno,car_no=car,
                             rider_id=rider_key(name,pref,term),rider_name=name,prefecture=pref,term=term,
                             **{"class":cls,"score":score,"S":S,"B":B,"quinella_rate":qr,"withdrawn":False}))
    df=pd.DataFrame(rows).sort_values(["race_no","car_no"]).reset_index(drop=True)
    if len(df)!=84 or df.race_id.nunique()!=12: raise RuntimeError("REJECT_COVERAGE")
    for rno,g in df.groupby("race_no"):
        if g.car_no.tolist()!=list(range(1,8)): raise RuntimeError(f"REJECT_CAR_SET {rno}")
        if g.rider_id.duplicated().any(): raise RuntimeError(f"REJECT_DUP_RIDER {rno}")
    return df
