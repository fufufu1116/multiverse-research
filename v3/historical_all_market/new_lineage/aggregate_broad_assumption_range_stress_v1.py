from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from c0_c1_n1_broad_assumption_range_stress_v1 import (
    BANKS, LINE_SHAPES, MODELS, PRE_WORLDS, RHOS, TIER_A_LINE_SHAPES, WINDS,
    LOCKED_RACES_PER_CONTEXT, LOCKED_SEED,
)
from digital_twin_stress_grid_v1 import ASSUMPTION_GRID


def _p90(vals):
    ordered=sorted(vals); return ordered[max(0,math.ceil(0.90*len(ordered))-1)]
def _new_group():
    return {"cell_count":0,"winner_counts":{m:0 for m in MODELS},"regret":{m:[] for m in MODELS},"metrics":{m:{"log_loss":0.0,"kl":0.0,"brier":0.0} for m in MODELS}}
def _update(g,cell):
    g["cell_count"]+=1; g["winner_counts"][cell["winner"]]+=1
    for m in MODELS:
        g["regret"][m].append(float(cell["excess_log_loss"][m]))
        for k in ("log_loss","kl","brier"): g["metrics"][m][k]+=float(cell["models"][m][k])
def _finish(g):
    n=g["cell_count"]
    return {"cell_count":n,"winner_counts":g["winner_counts"],"models":{m:{
        "mean_log_loss":g["metrics"][m]["log_loss"]/n,
        "mean_kl":g["metrics"][m]["kl"]/n,
        "mean_brier":g["metrics"][m]["brier"]/n,
        "mean_excess_log_loss":sum(g["regret"][m])/n,
        "worst_case_excess_log_loss":max(g["regret"][m]),
        "p90_excess_log_loss_nearest_rank":_p90(g["regret"][m]),
        "zero_regret_cell_count":sum(abs(x)<=1e-15 for x in g["regret"][m]),
    } for m in MODELS}}

def aggregate(input_dir:Path)->dict:
    files=sorted(input_dir.rglob('*.json'))
    shards=[]
    for p in files:
        try:d=json.loads(p.read_text())
        except Exception:continue
        if d.get('record')=='C0_C1_N1_BROAD_ASSUMPTION_RANGE_LINE_SHARD_v1': shards.append(d)
    if len(shards)!=len(LINE_SHAPES): raise ValueError(f"shard_count_mismatch:{len(shards)}:{len(LINE_SHAPES)}")
    by_line={s['line_id']:s for s in shards}
    if set(by_line)!=set(LINE_SHAPES): raise ValueError(f"line_set_mismatch:{set(by_line)^set(LINE_SHAPES)}")
    heads={s['executed_head'] for s in shards}
    if len(heads)!=1: raise ValueError(f"mixed_heads:{heads}")
    head=next(iter(heads))
    allg=_new_group(); primary=_new_group(); groups={d:{} for d in ('tier','pre_world','line_shape','bank','wind','rho','truth_scenario')}
    total_evals=0
    scenario_ids={x.scenario_id for x in ASSUMPTION_GRID}
    for line_id,s in by_line.items():
        if s['seed']!=LOCKED_SEED or s['races_per_structural_context']!=LOCKED_RACES_PER_CONTEXT: raise ValueError('lock_mismatch')
        if tuple(s['line_shape'])!=LINE_SHAPES[line_id]: raise ValueError(f'shape_mismatch:{line_id}')
        if s['cell_count']!=1080 or s['scenario_race_evaluations']!=25920: raise ValueError(f'shard_size_mismatch:{line_id}')
        total_evals += s['scenario_race_evaluations']
        seen=set()
        for cell in s['cells']:
            key=(cell['pre_world'],cell['bank'],cell['wind'],cell['rho'],cell['scenario_id'])
            if key in seen: raise ValueError(f'duplicate_cell:{line_id}:{key}')
            seen.add(key)
            if cell['pre_world'] not in PRE_WORLDS or cell['bank'] not in BANKS or cell['wind'] not in WINDS or cell['rho'] not in RHOS or cell['scenario_id'] not in scenario_ids: raise ValueError(f'axis_drift:{line_id}:{key}')
            _update(allg,cell)
            tier='A' if line_id in TIER_A_LINE_SHAPES else 'B'
            if tier=='A': _update(primary,cell)
            dims={'tier':tier,'pre_world':cell['pre_world'],'line_shape':line_id,'bank':str(cell['bank']),'wind':str(cell['wind']),'rho':str(cell['rho']),'truth_scenario':cell['scenario_id']}
            for dim,val in dims.items(): _update(groups[dim].setdefault(val,_new_group()),cell)
        if len(seen)!=1080: raise ValueError(f'unique_cell_count:{line_id}:{len(seen)}')
    if allg['cell_count']!=16200 or primary['cell_count']!=6480 or total_evals!=388800: raise ValueError('aggregate_count_mismatch')
    return {
      'record':'C0_C1_N1_BROAD_ASSUMPTION_RANGE_STRESS_v1',
      'status':'SYNTHETIC_ENGINEERING_FALSIFICATION_ONLY',
      'executed_head':head,
      'seed':LOCKED_SEED,
      'races_per_structural_context':LOCKED_RACES_PER_CONTEXT,
      'line_partition_count':15,
      'scenario_world_cell_count':16200,
      'total_scenario_race_evaluations':388800,
      'primary_tier_A_robustness':_finish(primary),
      'all_topologies_diagnostic_only':_finish(allg),
      'breakdowns':{d:{k:_finish(v) for k,v in vals.items()} for d,vals in groups.items()},
      'claim_boundary':'No topology frequency, real causal effect, predictive edge, ROI, model promotion or real-world equivalence may be inferred.',
      'scientific_firewall':{'ECON_HOLDOUT1000':'SEALED','RESULT_PAYOUT_access':'UNAUTHORIZED','same_source_realism_retuning':'CLOSED','untouched_validation':'CLOSED','model_promotion':'PROHIBITED'}
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input-dir',required=True);ap.add_argument('--output',required=True);args=ap.parse_args()
    out=aggregate(Path(args.input_dir));Path(args.output).write_text(json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True))
    print('BROAD_ASSUMPTION_RANGE_AGGREGATION_PASS')
    print(json.dumps({'executed_head':out['executed_head'],'cells':out['scenario_world_cell_count'],'evals':out['total_scenario_race_evaluations'],'tierA_wins':out['primary_tier_A_robustness']['winner_counts'],'all_wins':out['all_topologies_diagnostic_only']['winner_counts']},sort_keys=True))
if __name__=='__main__':main()
