#!/usr/bin/env python3
import argparse
import itertools
import json
import math
from pathlib import Path

MARKETS = ("3rentan","3renhuku","2shatan","2shahuku","wide")

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def circ_bucket(race):
    b=race.get("circumference_bucket")
    if b in ("333_OR_333_33","400"):
        return b
    m=float(race["circumference_m"])
    if abs(m-400.0)<1e-6:
        return "400"
    if abs(m-333.0)<1.0 or abs(m-333.33)<1.0:
        return "333_OR_333_33"
    raise ValueError(f"unsupported circumference {m}")

def build_logits(model,race,use_challenger):
    beta=float(model["baseline"]["beta"])
    rider_lookup={
        str(x["official_registration_number"]):float(x["delta_logit"])
        for x in model["rider_level"]["lookup"]
    }
    style_lookup={
        k:float(v["delta_logit"])
        for k,v in model["style_fallback"]["lookup"].items()
    }
    bucket=circ_bucket(race)
    q=1.0 if bucket=="333_OR_333_33" else -1.0
    rows=[]
    for r in race["riders"]:
        car=int(r["car_no"])
        reg=str(r.get("official_registration_number") or "")
        style=r.get("style")
        score=float(r["competition_score"])
        delta=0.0
        source="S0"
        if use_challenger:
            if reg and reg in rider_lookup:
                delta=rider_lookup[reg]
                source="RIDER"
            elif style in style_lookup:
                delta=style_lookup[style]
                source="STYLE"
        z=beta*score + q*delta
        rows.append({
            "car_no":car,
            "rider_name":r.get("rider_name"),
            "official_registration_number":reg or None,
            "style":style,
            "competition_score":score,
            "correction_source":source,
            "delta_logit":delta,
            "logit":z,
            "weight":math.exp(z),
        })
    if len(rows)<3:
        raise ValueError("at least 3 active riders required")
    cars=[x["car_no"] for x in rows]
    if len(cars)!=len(set(cars)):
        raise ValueError("duplicate car_no")
    return rows,bucket

def ordered_top3(rows):
    w={x["car_no"]:x["weight"] for x in rows}
    total=sum(w.values())
    out={}
    cars=list(w)
    for i,j,k in itertools.permutations(cars,3):
        p1=w[i]/total
        p2=w[j]/(total-w[i])
        p3=w[k]/(total-w[i]-w[j])
        out[f"{i}-{j}-{k}"]=p1*p2*p3
    return out

def derive_markets(ot3):
    three_tan=dict(ot3)
    three_fuku={}
    two_tan={}
    two_fuku={}
    wide={}
    for key,p in ot3.items():
        i,j,k=map(int,key.split("-"))
        u3="=".join(map(str,sorted((i,j,k))))
        three_fuku[u3]=three_fuku.get(u3,0.0)+p
        t2=f"{i}-{j}"
        two_tan[t2]=two_tan.get(t2,0.0)+p
        u2=f"{min(i,j)}={max(i,j)}"
        two_fuku[u2]=two_fuku.get(u2,0.0)+p
        for a,b in ((i,j),(i,k),(j,k)):
            wk=f"{min(a,b)}={max(a,b)}"
            wide[wk]=wide.get(wk,0.0)+p
    return {
        "3rentan":three_tan,
        "3renhuku":three_fuku,
        "2shatan":two_tan,
        "2shahuku":two_fuku,
        "wide":wide,
    }

def win_probs(rows):
    total=sum(x["weight"] for x in rows)
    return {str(x["car_no"]):x["weight"]/total for x in rows}

def project(model,race,use_challenger):
    rows,bucket=build_logits(model,race,use_challenger)
    ot3=ordered_top3(rows)
    mk=derive_markets(ot3)
    sums={m:sum(v.values()) for m,v in mk.items()}
    checks={
        "3rentan_mass":sums["3rentan"],
        "3renhuku_mass":sums["3renhuku"],
        "2shatan_mass":sums["2shatan"],
        "2shahuku_mass":sums["2shahuku"],
        "wide_mass":sums["wide"],
        "pass":(
            abs(sums["3rentan"]-1)<1e-9
            and abs(sums["3renhuku"]-1)<1e-9
            and abs(sums["2shatan"]-1)<1e-9
            and abs(sums["2shahuku"]-1)<1e-9
            and abs(sums["wide"]-3)<1e-9
        )
    }
    return {
        "circumference_bucket":bucket,
        "win_probabilities":win_probs(rows),
        "riders":rows,
        "ordered_top3":ot3,
        "ticket_probabilities":mk,
        "mass_checks":checks,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",required=True)
    ap.add_argument("--race",required=True)
    ap.add_argument("--out")
    args=ap.parse_args()
    model=load(args.model)
    race=load(args.race)
    out={
        "record":"KEIRIN_PRE_ONLY_ALL_MARKET_PROJECTION",
        "result_accessed":False,
        "odds_used":False,
        "markets":list(MARKETS),
        "s0":project(model,race,False),
        "challenger":project(model,race,True),
    }
    txt=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
    if args.out:
        Path(args.out).write_text(txt,encoding="utf-8")
    else:
        print(txt,end="")

if __name__=="__main__":
    main()
