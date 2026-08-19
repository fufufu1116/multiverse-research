#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, math, os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import cmp_to_key
from pathlib import Path
from typing import Any
import numpy as np

EXPECTED_STAGE2_SHA256="34ad32bed6e8b4d700864c46f4533bef1da254c7d87dc7ffe6ec266fd74530dc"
EXPECTED_PRED_SHA256="772eca4d26f177b94a86ccf7c1b8486e3cdbac0cae454d76ce91fadeca5f1d51"
EXPECTED_UNIVERSE_SHA256="eb561c9cad5121cf689b237d44a08d089f375a2b2b728e34e91a48338446f3b1"
INITIAL_BANKROLL=100000
BOOTSTRAP_REPS=10000
BOOTSTRAP_SEED=20260819
MARKETS=("3rentan","3renhuku","2shatan","2shahuku","wide","2wakutan","2wakuhuku")
MODELS=("candidate_a","b1a_reconstituted_v1")

class FailClosed(RuntimeError): pass

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def git_blob(p:Path)->str:
    b=p.read_bytes(); return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()

def dump_json(p:Path,x:Any):
    p.parent.mkdir(parents=True,exist_ok=True); q=p.with_suffix(p.suffix+".tmp")
    q.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8"); q.replace(p)

def load_json(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise FailClosed(f"object expected: {p}")
    return x

@dataclass
class Stage2Index:
    path:Path; offsets:dict[tuple[str,str],int]
    @classmethod
    def build(cls,path:Path,uids:set[str]):
        if sha256_file(path)!=EXPECTED_STAGE2_SHA256: raise FailClosed("Stage2 SHA mismatch")
        off={}; races=set(); n=0
        with path.open("rb") as f:
            while True:
                pos=f.tell(); line=f.readline()
                if not line: break
                if not line.strip(): continue
                n+=1; r=json.loads(line); rid=str(r.get("race_id","")); model=str(r.get("probability_source",""))
                if rid not in uids or model not in MODELS or (rid,model) in off: raise FailClosed("Stage2 race/model invariant")
                if r.get("result_fields_included") is not False or r.get("settlement_fields_included") is not False or r.get("realized_roi_computed") is not False: raise FailClosed("Stage2 firewall")
                off[(rid,model)]=pos; races.add(rid)
        if n!=4000 or len(off)!=4000 or races!=uids: raise FailClosed("Stage2 cardinality")
        print(f"[STAGE2 INDEX] rows={n} races={len(races)}",flush=True); return cls(path,off)
    def pair(self,rid:str):
        d={}
        with self.path.open("rb") as f:
            for model in MODELS:
                pos=self.offsets.get((rid,model))
                if pos is None: raise FailClosed("Stage2 missing pair")
                f.seek(pos); r=json.loads(f.readline())
                if str(r.get("race_id"))!=rid or str(r.get("probability_source"))!=model: raise FailClosed("Stage2 offset corruption")
                d[model]=r
        return d[MODELS[0]],d[MODELS[1]]

@dataclass
class MetricState:
    bankroll:int=INITIAL_BANKROLL; peak_bankroll:int=INITIAL_BANKROLL; min_bankroll:int=INITIAL_BANKROLL
    total_stake:int=0; total_return:int=0; bet_races:int=0; hit_tickets:int=0; max_dd_num:int=0; max_dd_den:int=1
    def draw(self):
        if self.bankroll>self.peak_bankroll:self.peak_bankroll=self.bankroll
        num=self.peak_bankroll-self.bankroll; den=self.peak_bankroll
        if den<=0: raise FailClosed("nonpositive peak bankroll")
        if num*self.max_dd_den>self.max_dd_num*den:self.max_dd_num,self.max_dd_den=num,den
        self.min_bankroll=min(self.min_bankroll,self.bankroll)
    def roi(self): return None if self.total_stake<=0 else self.total_return/self.total_stake-1.0
    def dd(self): return self.max_dd_num/self.max_dd_den

def global_rank(sel): return sorted(sel,key=lambda x:(-float(x[2]["ev"]),-float(x[2]["ratio"]),-float(x[2]["p"]),x[0],x[1]))

def allocate(policy:str,bank:int,sel):
    if bank<100 or not sel:return []
    r=global_rank(sel)
    if policy=="FLAT100": return [(m,k,100) for m,k,_ in r[:bank//100]]
    if policy=="RACE2PCT_EQUAL":
        units=bank//5000
        if units<=0:return []
        n=min(len(r),units); kept=r[:n]; base,rem=divmod(units,n)
        return [(m,k,(base+(i<rem))*100) for i,(m,k,_) in enumerate(kept)]
    if policy not in {"FK10_R2","FK25_R3"}: raise FailClosed("unknown stake policy")
    frac,tcap,rcap=(.10,.0025,.02) if policy=="FK10_R2" else (.25,.005,.03)
    raw=[]
    for m,k,v in r:
        p=float(v["p"]); o=float(v["odds"])
        if not 0<=p<=1 or not (o>1 and math.isfinite(o)): raise FailClosed(f"Kelly input {m}/{k}")
        raw.append(frac*max(0.0,(o*p-1)/(o-1)))
    s=sum(raw); scaled=[x*(rcap/s) for x in raw] if s>rcap and s>0 else raw
    fs=[min(x,tcap) for x in scaled]; out=[]
    for (m,k,_),f in zip(r,fs):
        stake=int(math.floor(bank*f/100))*100
        if stake>=100:out.append((m,k,stake))
    if sum(x[2] for x in out)>bank: raise FailClosed("stake exceeds bankroll")
    return out

def validate_settlement(rid:str,s:dict,A:dict,B:dict):
    if str(s.get("race_id"))!=rid: raise FailClosed("settlement race mismatch")
    sa=list(A.get("sold_markets",[])); sb=list(B.get("sold_markets",[]))
    if sa!=sb: raise FailClosed("model market mismatch")
    if s.get("settled_market_presence")!={m:m in sa for m in MARKETS}: raise FailClosed(f"{rid}: settlement market presence mismatch")
    sm=s.get("settlements_yen_per_100")
    if not isinstance(sm,dict) or set(sm)!=set(MARKETS): raise FailClosed("settlement schema")
    for m in sa:
        ka=set(A["ticket_price_probability_metrics"][m]); kb=set(B["ticket_price_probability_metrics"][m])
        if ka!=kb or set(sm[m])-ka: raise FailClosed(f"{rid}/{m}: settlement ticket mismatch")

def settle(st:MetricState,sel,policy,s):
    pre=st.bankroll; stakes=allocate(policy,pre,sel); stake=sum(x[2] for x in stakes)
    if stake>pre: raise FailClosed("negative-bankroll attempt")
    ret=hits=0; sm=s["settlements_yen_per_100"]
    for m,k,v in stakes:
        pay=int(sm[m].get(k,0))
        if pay>0:hits+=1; ret+=(v//100)*pay
    st.bankroll=pre-stake+ret
    if st.bankroll<0:raise FailClosed("negative bankroll")
    st.total_stake+=stake; st.total_return+=ret; st.hit_tickets+=hits; st.bet_races+=int(stake>0); st.draw()
    return {"pre_bankroll":pre,"stake":stake,"return":ret,"post_bankroll":st.bankroll,"hits":hits,"executed_tickets":len(stakes)}

def config_id(p,g,t,s): return f"{p}:{g}:{t}:{s}"
def parse_config(cid):
    p=cid.split(":")
    if len(p)!=4:raise FailClosed("bad config ID")
    return tuple(p)
def dd_leq(st,pct): return st.max_dd_num*100<=st.max_dd_den*pct
def metrics(cid,st,seg):
    return {"segment":seg,"configuration_id":cid,"total_stake":st.total_stake,"total_return":st.total_return,"realized_roi":st.roi(),"ending_bankroll":st.bankroll,"bet_races":st.bet_races,"hit_tickets":st.hit_tickets,"max_drawdown":st.dd(),"max_drawdown_num":st.max_dd_num,"max_drawdown_den":st.max_dd_den,"min_bankroll":st.min_bankroll}
def compare(a,b):
    ca,sa=a; cb,sb=b; x=sa.total_return*sb.total_stake; y=sb.total_return*sa.total_stake
    if x!=y:return -1 if x>y else 1
    if sa.bankroll!=sb.bankroll:return -1 if sa.bankroll>sb.bankroll else 1
    x=sa.max_dd_num*sb.max_dd_den; y=sb.max_dd_num*sa.max_dd_den
    if x!=y:return -1 if x<y else 1
    if sa.bet_races!=sb.bet_races:return -1 if sa.bet_races>sb.bet_races else 1
    return -1 if ca<cb else (1 if ca>cb else 0)
def sort_states(xs): xs.sort(key=cmp_to_key(compare)); return xs

def write_metrics(path,rows):
    fields=["segment","configuration_id","total_stake","total_return","realized_roi","ending_bankroll","bet_races","hit_tickets","max_drawdown","max_drawdown_num","max_drawdown_den","min_bankroll"]
    q=path.with_suffix(path.suffix+".tmp")
    with q.open("w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    q.replace(path)

def load_settlement(path:Path,seg:str,n:int,sha:str):
    if not path.is_file() or sha256_file(path)!=sha: raise FailClosed(f"settlement {seg} missing/SHA")
    d={}
    for i,line in enumerate(path.open(encoding="utf-8"),1):
        if not line.strip():continue
        x=json.loads(line); rid=str(x.get("race_id",""))
        if not rid or rid in d or x.get("segment")!=seg:raise FailClosed(f"settlement {seg} schema row={i}")
        d[rid]=x
    if len(d)!=n:raise FailClosed(f"settlement {seg} rows={len(d)}")
    print(f"[OPEN SETTLEMENT {seg}] rows={n} sha={sha}",flush=True); return d

def build_universe(path:Path):
    if sha256_file(path)!=EXPECTED_UNIVERSE_SHA256:raise FailClosed("universe SHA")
    with path.open(encoding="utf-8",newline="") as f:rs=list(csv.DictReader(f))
    d={}
    for r in rs:
        i=int(r["dev_index"]); rid=str(r["race_id"])
        if i in d or not rid:raise FailClosed("universe duplicate")
        d[i]=rid
    if len(rs)!=2000 or set(d)!=set(range(1,2001)) or len(set(d.values()))!=2000:raise FailClosed("universe cardinality")
    return d

def load_prediction(path:Path,uids:set[str]):
    if sha256_file(path)!=EXPECTED_PRED_SHA256:raise FailClosed("prediction SHA")
    d=defaultdict(dict); n=0
    with path.open(encoding="utf-8",newline="") as f:
        for r in csv.DictReader(f):
            rid=str(r["race_id"]); c=int(r["car_no"])
            if rid not in uids or c in d[rid]:raise FailClosed("prediction duplicate")
            a=float(r["candidate_a_win_prob"]); b=float(r["b1a_reconstituted_v1_win_prob"]); d[rid][c]={"cons":min(a,b),"mean":(a+b)/2}; n+=1
    if n!=14255 or set(d)!=uids:raise FailClosed("prediction cardinality")
    return d

def pval(mod,pid):
    for x in mod.PROFILES:
        if x[0]==pid:return x
    raise FailClosed("profile")
def gval(mod,gid):
    for x in mod.GATES:
        if x[0]==gid:return x[1]
    raise FailClosed("gate")

def evaluate(seg,rids,sett,configs,s2,pred,mod,ledger_for=None):
    states={c:MetricState() for c in configs}; parts={c:parse_config(c) for c in configs}; ledger=[]
    for j,rid in enumerate(rids,1):
        A,B=s2.pair(rid); validate_settlement(rid,sett[rid],A,B); ec={}; pc={}
        for cid in configs:
            p,g,t,pol=parts[cid]; eg=(p,g)
            if eg not in ec:ec[eg]=mod.consensus_eligible(A,B,pval(mod,p),gval(mod,g))[1]
            pt=(p,g,t)
            if pt not in pc:pc[pt]=mod.select_template(rid,A,ec[eg],pred,t)
            info=settle(states[cid],pc[pt],pol,sett[rid])
            if cid==ledger_for:ledger.append({"race_ordinal_in_segment":j,"race_id":rid,**info})
        if j%100==0 or j==len(rids):print(f"[{seg}] {j}/{len(rids)} configs={len(configs)}",flush=True)
    return states,ledger

def write_c_ledger(path,ledger):
    fields=["race_ordinal_in_segment","race_id","pre_bankroll","stake","return","post_bankroll","hits","executed_tickets"]; q=path.with_suffix(path.suffix+".tmp")
    with q.open("w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(ledger)
    q.replace(path)

def load_c_ledger(path:Path,rids:list[str]):
    if not path.is_file():raise FailClosed("C ledger missing")
    st=MetricState(); out=[]
    with path.open(encoding="utf-8",newline="") as f:
        for i,r in enumerate(csv.DictReader(f),1):
            rid=str(r["race_id"]); pre=int(r["pre_bankroll"]); stake=int(r["stake"]); ret=int(r["return"]); post=int(r["post_bankroll"]); hits=int(r["hits"]); ex=int(r["executed_tickets"])
            if i>500 or rid!=rids[i-1] or int(r["race_ordinal_in_segment"])!=i or pre!=st.bankroll or post!=pre-stake+ret or min(stake,ret,post,hits,ex)<0 or stake%100 or hits>ex:raise FailClosed(f"C ledger invariant row={i}")
            st.bankroll=post; st.total_stake+=stake; st.total_return+=ret; st.hit_tickets+=hits; st.bet_races+=int(stake>0); st.draw()
            out.append({"race_ordinal_in_segment":i,"race_id":rid,"pre_bankroll":pre,"stake":stake,"return":ret,"post_bankroll":post,"hits":hits,"executed_tickets":ex})
    if len(out)!=500:raise FailClosed("C ledger cardinality")
    return out,st

def _boot(idx,stake,ret):
    s=stake[idx].sum(axis=1,dtype=np.int64); r=ret[idx].sum(axis=1,dtype=np.int64); v=s>0
    return (r[v]/s[v]-1).astype(np.float64),int((~v).sum())
def bootstrap(ledger,log:Path):
    if len(ledger)!=500:raise FailClosed("C ledger rows")
    stake=np.asarray([int(x["stake"]) for x in ledger],dtype=np.int64); ret=np.asarray([int(x["return"]) for x in ledger],dtype=np.int64)
    idx=np.random.default_rng(BOOTSTRAP_SEED).integers(0,500,size=(BOOTSTRAP_REPS,500),dtype=np.int32); bs=500; jobs=[(i,idx[i:i+bs]) for i in range(0,BOOTSTRAP_REPS,bs)]
    workers=max(2,min(4,os.cpu_count() or 2)); res={}; omitted=0
    with log.open("w",encoding="utf-8") as lf:
        lf.write(f"BOOTSTRAP start reps={BOOTSTRAP_REPS} seed={BOOTSTRAP_SEED} workers={workers} batch_size={bs}\n");lf.flush();os.fsync(lf.fileno())
        with ThreadPoolExecutor(max_workers=workers) as ex:
            fs={ex.submit(_boot,a,stake,ret):i for i,a in jobs}; done=0
            for f in as_completed(fs):
                i=fs[f]; ro,o=f.result();res[i]=ro;omitted+=o;done+=1;msg=f"[BOOTSTRAP] batch {done}/{len(jobs)} start={i} valid={len(ro)} omitted={o}";print(msg,flush=True);lf.write(msg+"\n");lf.flush();os.fsync(lf.fileno())
    v=np.concatenate([res[i] for i in sorted(res)])
    if len(v)<9500:raise FailClosed("bootstrap valid <9500")
    lo,hi=np.percentile(v,[2.5,97.5],method="linear")
    return {"replicates_requested":10000,"seed":BOOTSTRAP_SEED,"resample_unit":"WHOLE_RACE","races_per_replicate":500,"valid_replicates":int(len(v)),"omitted_zero_stake_replicates":omitted,"percentile_method":"numpy_linear","roi_p025":float(lo),"roi_p975":float(hi),"worker_threads":workers,"batch_size":bs}
def verdict(st,boot):
    pos=st.total_return>st.total_stake
    if pos and st.bet_races>=50 and dd_leq(st,25) and boot["roi_p025"]>0:return "OOS_STRONG_PASS"
    if pos and st.bet_races>=50 and dd_leq(st,35) and boot["roi_p025"]<=0:return "OOS_POSITIVE_BUT_UNCERTAIN"
    return "OOS_FAIL"
