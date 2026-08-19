#!/usr/bin/env python3
"""Multiverse Hybrid v3.0 pre-Settlement Stage 4-6 diagnostics engine v1.

Inputs are pre-result only:
- exact Stage2 PRICE/EV catalog
- frozen Candidate-A/B1a prediction CSV
- immutable DEV2000 universe

No RESULT/PAYOUT/Settlement/realized ROI is read or computed.
"""
from __future__ import annotations
import argparse, csv, hashlib, itertools, json, math
from collections import Counter, defaultdict
from pathlib import Path

EXPECTED_STAGE2_SHA256="34ad32bed6e8b4d700864c46f4533bef1da254c7d87dc7ffe6ec266fd74530dc"
EXPECTED_PRED_SHA256="772eca4d26f177b94a86ccf7c1b8486e3cdbac0cae454d76ce91fadeca5f1d51"
EXPECTED_UNIVERSE_SHA256="eb561c9cad5121cf689b237d44a08d089f375a2b2b728e34e91a48338446f3b1"
EXPECTED_RACES=2000
EXPECTED_STAGE2_ROWS=4000

PROFILES=(
 ("P00",0.00,1.00),("P05",0.05,1.05),("P10",0.10,1.10),
 ("P20",0.20,1.20),("P35",0.35,1.35),("P50",0.50,1.50),("P100",1.00,2.00),
)
GATES=(("G0",None),("G20",0.20),("G25",0.25),("G30",0.30))
TEMPLATES=("SINGLE","TOP1_PER_MARKET","TOP3_PER_MARKET","TOP5_PER_MARKET","BOX3","WHEEL1x3","FORMATION_2x3x4")
STAKE_POLICIES=("FLAT100","RACE2PCT_EQUAL","FK10_R2","FK25_R3")
CAR_MARKETS={"3rentan","3renhuku","2shatan","2shahuku","wide"}
FRAME_MARKETS={"2wakutan","2wakuhuku"}
MODELS=("candidate_a","b1a_reconstituted_v1")
MARKETS=("3rentan","3renhuku","2shatan","2shahuku","wide","2wakutan","2wakuhuku")

class FailClosed(RuntimeError): pass

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def qtile(xs:list[float], q:float)->float:
    ys=sorted(xs)
    if not ys: raise FailClosed("empty quantile")
    if len(ys)==1: return float(ys[0])
    pos=(len(ys)-1)*q; lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi: return float(ys[lo])
    frac=pos-lo
    return float(ys[lo]*(1-frac)+ys[hi]*frac)

def frame_map_for_nominal(n:int)->dict[int,int]:
    if n not in (7,8,9): raise FailClosed(f"unsupported nominal={n}")
    singles=12-n
    out={c:c for c in range(1,singles+1)}
    frame=singles+1; c=singles+1
    while c<=n:
        out[c]=frame
        if c+1<=n: out[c+1]=frame
        c+=2; frame+=1
    return out

def frame_key_sets(active:list[int], fm:dict[int,int])->tuple[set[str],set[str]]:
    op=set(); un=set()
    for i in active:
        for j in active:
            if i!=j: op.add(f"{fm[i]}-{fm[j]}")
    for a,b in itertools.combinations(active,2):
        fa,fb=fm[a],fm[b]
        un.add(f"{min(fa,fb)}={max(fa,fb)}")
    return op,un

def infer_frame_map(row:dict)->tuple[int|None,dict[int,int]|None]:
    if "2wakutan" not in row["sold_markets"]:
        return None,None
    active=[int(x) for x in row["active_car_numbers"]]
    pub_op=set(row["ticket_price_probability_metrics"]["2wakutan"])
    pub_un=set(row["ticket_price_probability_metrics"]["2wakuhuku"])
    valid=[]
    for n in (7,8,9):
        if max(active)>n: continue
        fm=frame_map_for_nominal(n)
        op,un=frame_key_sets(active,fm)
        if op==pub_op and un==pub_un: valid.append((n,fm))
    if len(valid)!=1: raise FailClosed(f"{row['race_id']}: frame-map candidates={[n for n,_ in valid]}")
    return valid[0]

def parse_ticket(market:str,key:str)->tuple[int,...]:
    sep="-" if market in {"3rentan","2shatan","2wakutan"} else "="
    return tuple(int(x) for x in key.split(sep))

def tv3(a:dict,b:dict)->float:
    ca=a["ticket_price_probability_metrics"]["3rentan"]
    cb=b["ticket_price_probability_metrics"]["3rentan"]
    if set(ca)!=set(cb): raise FailClosed(f"{a['race_id']}: 3rentan key mismatch")
    keys=sorted(ca)
    pa=[float(ca[k]["model_event_probability"]) for k in keys]
    pb=[float(cb[k]["model_event_probability"]) for k in keys]
    sa=sum(pa); sb=sum(pb)
    if abs(sa-1)>1e-10 or abs(sb-1)>1e-10: raise FailClosed(f"{a['race_id']}: TV source sum drift")
    return 0.5*sum(abs(x-y) for x,y in zip(pa,pb))

def consensus_eligible(a:dict,b:dict,profile:tuple[str,float,float],tv_cap:float|None):
    _,emin,rmin=profile
    t=tv3(a,b)
    out={}
    if tv_cap is not None and t>tv_cap:
        return t,{m:{} for m in a["sold_markets"]}
    if a["sold_markets"]!=b["sold_markets"]: raise FailClosed(f"{a['race_id']}: sold-market model mismatch")
    for m in a["sold_markets"]:
        ta=a["ticket_price_probability_metrics"][m]; tb=b["ticket_price_probability_metrics"][m]
        if set(ta)!=set(tb): raise FailClosed(f"{a['race_id']}/{m}: ticket model mismatch")
        d={}
        for k in ta:
            xa,xb=ta[k],tb[k]
            ev=min(float(xa["raw_ev_primary"]),float(xb["raw_ev_primary"]))
            ratio=min(float(xa["shape_edge_ratio_primary"]),float(xb["shape_edge_ratio_primary"]))
            p=min(float(xa["model_event_probability"]),float(xb["model_event_probability"]))
            if ev>=emin and ratio>=rmin:
                odds=float(xa["closing_odds_low"] if m=="wide" else xa["closing_odds"])
                d[k]={"p":p,"ev":ev,"ratio":ratio,"odds":odds}
        out[m]=d
    return t,out

def rank_tickets(d:dict):
    return sorted(d.items(), key=lambda kv:(-kv[1]["ev"],-kv[1]["ratio"],-kv[1]["p"],kv[0]))

def select_template(rid:str,row:dict,elig:dict,pred:dict,template:str):
    def car_rank():
        d=pred[rid]
        return sorted(d,key=lambda c:(-d[c]["cons"],-d[c]["mean"],c))
    def frame_rank():
        _,fm=infer_frame_map(row)
        if fm is None:return None,None
        s=defaultdict(float); mu=defaultdict(float)
        for c0 in row["active_car_numbers"]:
            c=int(c0); f=fm[c]
            s[f]+=pred[rid][c]["cons"]; mu[f]+=pred[rid][c]["mean"]
        return sorted(s,key=lambda f:(-s[f],-mu[f],f)),fm

    if template=="SINGLE":
        pool=[(m,k,v) for m,d in elig.items() for k,v in d.items()]
        if not pool:return []
        pool.sort(key=lambda x:(-x[2]["ev"],-x[2]["ratio"],-x[2]["p"],x[0],x[1]))
        return [pool[0]]
    if template in {"TOP1_PER_MARKET","TOP3_PER_MARKET","TOP5_PER_MARKET"}:
        K={"TOP1_PER_MARKET":1,"TOP3_PER_MARKET":3,"TOP5_PER_MARKET":5}[template]
        return [(m,k,v) for m,d in elig.items() for k,v in rank_tickets(d)[:K]]

    cr=car_rank(); fr,fm=frame_rank()
    selected=[]
    if template=="BOX3":
        topc=set(cr[:3]); topf=set(fr[:3]) if fr else set()
        for m,d in elig.items():
            group=topc if m in CAR_MARKETS else topf
            for k,v in d.items():
                if all(x in group for x in parse_ticket(m,k)): selected.append((m,k,v))
    elif template=="WHEEL1x3":
        axis=cr[0]; partners=set(cr[1:4])
        fax=fr[0] if fr else None; fpartners=set(fr[1:4]) if fr else set()
        for m,d in elig.items():
            for k,v in d.items():
                parts=parse_ticket(m,k); ok=False
                if m=="3rentan": ok=(parts[0]==axis and parts[1] in partners and parts[2] in partners and parts[1]!=parts[2])
                elif m=="3renhuku": ok=(axis in parts and len(set(parts)-{axis})==2 and (set(parts)-{axis})<=partners)
                elif m=="2shatan": ok=(parts[0]==axis and parts[1] in partners)
                elif m in {"2shahuku","wide"}: ok=(axis in parts and len(set(parts)-{axis})==1 and next(iter(set(parts)-{axis}),None) in partners)
                elif m=="2wakutan": ok=(parts[0]==fax and parts[1] in fpartners)
                elif m=="2wakuhuku": ok=(fax in parts and len(set(parts)-{fax})==1 and next(iter(set(parts)-{fax}),None) in fpartners)
                if ok:selected.append((m,k,v))
    elif template=="FORMATION_2x3x4":
        c1=set(cr[:2]); c2=set(cr[:3]); c3=set(cr[:4])
        f1=set(fr[:2]) if fr else set(); f2=set(fr[:3]) if fr else set()
        for m,d in elig.items():
            for k,v in d.items():
                p=parse_ticket(m,k); ok=False
                if m=="3rentan": ok=(p[0] in c1 and p[1] in c2 and p[2] in c3 and len(set(p))==3)
                elif m=="2shatan": ok=(p[0] in c1 and p[1] in c2 and p[0]!=p[1])
                elif m=="2wakutan": ok=(p[0] in f1 and p[1] in f2)
                if ok:selected.append((m,k,v))
    else: raise FailClosed(f"unknown template={template}")
    uniq={}
    for m,k,v in selected: uniq[(m,k)]=(m,k,v)
    return [uniq[x] for x in sorted(uniq)]

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("stage2_jsonl"); ap.add_argument("prediction_csv"); ap.add_argument("universe_csv"); ap.add_argument("quality_json")
    a=ap.parse_args()
    s2=Path(a.stage2_jsonl); pp=Path(a.prediction_csv); up=Path(a.universe_csv); qp=Path(a.quality_json)
    if sha256_file(s2)!=EXPECTED_STAGE2_SHA256: raise FailClosed("Stage2 SHA mismatch")
    if sha256_file(pp)!=EXPECTED_PRED_SHA256: raise FailClosed("prediction SHA mismatch")
    if sha256_file(up)!=EXPECTED_UNIVERSE_SHA256: raise FailClosed("universe SHA mismatch")

    pred=defaultdict(dict); pred_rows=0
    with pp.open("r",encoding="utf-8",newline="") as f:
        for r in csv.DictReader(f):
            rid=str(r["race_id"]); car=int(r["car_no"])
            pa=float(r["candidate_a_win_prob"]); pb=float(r["b1a_reconstituted_v1_win_prob"])
            pred[rid][car]={"cons":min(pa,pb),"mean":(pa+pb)/2}
            pred_rows+=1
    if pred_rows!=14255 or len(pred)!=EXPECTED_RACES: raise FailClosed("prediction cardinality")

    universe=[]
    with up.open("r",encoding="utf-8",newline="") as f:
        universe=list(csv.DictReader(f))
    if len(universe)!=EXPECTED_RACES: raise FailClosed("universe cardinality")
    universe_ids=[str(x["race_id"]) for x in universe]

    pairs=defaultdict(dict); rows=0
    with s2.open("r",encoding="utf-8") as f:
        for line in f:
            if not line.strip():continue
            r=json.loads(line); rid=str(r["race_id"]); model=str(r["probability_source"])
            if model not in MODELS or model in pairs[rid]: raise FailClosed("Stage2 duplicate/model")
            if r.get("result_fields_included") is not False or r.get("settlement_fields_included") is not False or r.get("realized_roi_computed") is not False:
                raise FailClosed("Stage2 outcome firewall")
            pairs[rid][model]=r; rows+=1
    if rows!=EXPECTED_STAGE2_ROWS or set(pairs)!=set(universe_ids): raise FailClosed("Stage2 cardinality/race set")
    if any(set(v)!=set(MODELS) for v in pairs.values()): raise FailClosed("missing paired model")

    tvs=[]; gate_pass=Counter(); cons_counts=Counter(); cons_no_bet=Counter()
    port=defaultdict(lambda:{"races":0,"nonempty":0,"tickets":0,"max_tickets":0})
    frame_races=0
    for rid in universe_ids:
        A=pairs[rid]["candidate_a"]; B=pairs[rid]["b1a_reconstituted_v1"]
        t=tv3(A,B); tvs.append(t)
        if "2wakutan" in A["sold_markets"]:
            infer_frame_map(A); frame_races+=1
        for gid,cap in GATES:
            if cap is None or t<=cap: gate_pass[gid]+=1
        for profile in PROFILES:
            for gid,cap in GATES:
                _,elig=consensus_eligible(A,B,profile,cap)
                for m,d in elig.items():
                    key=f"{profile[0]}:{gid}:{m}"
                    cons_counts[key]+=len(d)
                    if not d: cons_no_bet[key]+=1
                for tpl in TEMPLATES:
                    sel=select_template(rid,A,elig,pred,tpl)
                    k=f"{profile[0]}:{gid}:{tpl}"
                    st=port[k]; st["races"]+=1; st["tickets"]+=len(sel); st["max_tickets"]=max(st["max_tickets"],len(sel))
                    if sel: st["nonempty"]+=1

    policy_max_initial_race_stake={
        "FLAT100": max(st["max_tickets"]*100 for st in port.values()),
        "RACE2PCT_EQUAL": 2000,
        "FK10_R2": 2000,
        "FK25_R3": 3000,
    }
    quality={
        "record":"STAGE456_PRESETTLEMENT_QUALITY_v1",
        "status":"PASS",
        "stage2_sha256":EXPECTED_STAGE2_SHA256,
        "prediction_sha256":EXPECTED_PRED_SHA256,
        "universe_sha256":EXPECTED_UNIVERSE_SHA256,
        "races":EXPECTED_RACES,
        "stage2_rows":rows,
        "tv3":{"min":min(tvs),"p25":qtile(tvs,.25),"median":qtile(tvs,.5),"p75":qtile(tvs,.75),"p90":qtile(tvs,.9),"p95":qtile(tvs,.95),"p99":qtile(tvs,.99),"max":max(tvs)},
        "agreement_gate_pass_races":dict(gate_pass),
        "frame_market_races":frame_races,
        "stage3_profiles":[x[0] for x in PROFILES],
        "stage4_gates":[x[0] for x in GATES],
        "stage5_templates":list(TEMPLATES),
        "stage6_stake_policies":list(STAKE_POLICIES),
        "pre_bankroll_configuration_count":len(PROFILES)*len(GATES)*len(TEMPLATES),
        "full_configuration_count":len(PROFILES)*len(GATES)*len(TEMPLATES)*len(STAKE_POLICIES),
        "consensus_candidate_counts":dict(sorted(cons_counts.items())),
        "consensus_no_bet_market_race_counts":dict(sorted(cons_no_bet.items())),
        "portfolio_diagnostics":{
            k:{**v,"mean_tickets_per_race":v["tickets"]/v["races"],"nonempty_race_share":v["nonempty"]/v["races"]}
            for k,v in sorted(port.items())
        },
        "initial_bankroll_jpy":100000,
        "policy_max_initial_race_stake_jpy":policy_max_initial_race_stake,
        "result_access":False,
        "payout_access":False,
        "settlement_access":False,
        "realized_roi_computed":False,
        "scientific_trial_count":0,
        "ECON_HOLDOUT1000":"SEALED",
    }
    qp.parent.mkdir(parents=True,exist_ok=True)
    qp.write_text(json.dumps(quality,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","races":EXPECTED_RACES,"full_configuration_count":quality["full_configuration_count"],"tv3_median":quality["tv3"]["median"],"frame_market_races":frame_races},indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
