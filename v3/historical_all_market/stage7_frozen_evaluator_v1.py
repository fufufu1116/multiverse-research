#!/usr/bin/env python3
"""Multiverse Hybrid v3.0 — frozen Stage-7 chronological economic evaluator v1.

Two-phase evaluator:
  AB: evaluate all 784 frozen configs on Segment A, shortlist Top10, validate on B,
      and atomically freeze exactly one FINAL_DEV2000_CONFIGURATION.
      Segment-C settlement content is never opened in this phase.
  C:  after the final freeze exists, score that one config exactly once on C,
      persist a complete 500-race ledger atomically, then run the preregistered
      10,000 whole-race bootstrap and emit the final OOS receipt.

No model refit, no post-settlement rule changes, no HOLDOUT access.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXPECTED_STAGE2_SHA256 = "34ad32bed6e8b4d700864c46f4533bef1da254c7d87dc7ffe6ec266fd74530dc"
EXPECTED_PRED_SHA256 = "772eca4d26f177b94a86ccf7c1b8486e3cdbac0cae454d76ce91fadeca5f1d51"
EXPECTED_UNIVERSE_SHA256 = "eb561c9cad5121cf689b237d44a08d089f375a2b2b728e34e91a48338446f3b1"
EXPECTED_STAGE456_BLOB = "a0ed6984969b0b98af1b074ef9fd2348f16604a0"
EXPECTED_STAGE3_PREREG_BLOB = "ba4175bb044bcacfa66a7b8d089e92c04762b2e6"
EXPECTED_STAGE4_PREREG_BLOB = "f5bb38e97dd2543842308f9b8ee401957d2e5216"
EXPECTED_STAGE5_PREREG_BLOB = "f13b5aa5584d260d30032c269cfc205a312f2426"
EXPECTED_STAGE6_PREREG_BLOB = "7dc0ac09440755ad1c43959237c0d975be11b245"
EXPECTED_STAGE7_PREREG_BLOB = "0cb70520777d4ac9d00ddd90b888df1f403c3a7e"
EXPECTED_EXEC_CONVENTIONS_BLOB = "b388ef5622d4c92ae4df96ad0105882b4994adf4"
EXPECTED_APPROVAL_BLOB = "71e87740ded33ea73c3f534d39830080ad8b43bb"

EXPECTED_RACES = 2000
EXPECTED_STAGE2_ROWS = 4000
START_BANKROLL = 100000
BOOTSTRAP_REPS = 10000
BOOTSTRAP_SEED = 20260819

MODELS = ("candidate_a", "b1a_reconstituted_v1")
PROFILE_IDS = ("P00","P05","P10","P20","P35","P50","P100")
GATE_IDS = ("G0","G20","G25","G30")
TEMPLATE_IDS = ("SINGLE","TOP1_PER_MARKET","TOP3_PER_MARKET","TOP5_PER_MARKET","BOX3","WHEEL1x3","FORMATION_2x3x4")
POLICY_IDS = ("FLAT100","RACE2PCT_EQUAL","FK10_R2","FK25_R3")

class FailClosed(RuntimeError):
    pass

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def git_blob_sha1_bytes(b: bytes) -> str:
    return hashlib.sha1(f"blob {len(b)}\0".encode("ascii") + b).hexdigest()

def atomic_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)

def atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as w:
        for r in rows:
            w.write(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    tmp.replace(path)

def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                x = json.loads(line)
            except Exception as e:
                raise FailClosed(f"{path.name}:{ln}: JSON parse error: {e}") from e
            if not isinstance(x, dict):
                raise FailClosed(f"{path.name}:{ln}: non-object record")
            out.append(x)
    return out

def verify_git_blob(repo: Path, rel: str, expected: str) -> None:
    p = repo / rel
    if not p.is_file():
        raise FailClosed(f"missing frozen file: {rel}")
    obs = git_blob_sha1_bytes(p.read_bytes())
    if obs != expected:
        raise FailClosed(f"blob mismatch {rel}: {obs} != {expected}")

def import_stage456(repo: Path):
    rel = "v3/historical_all_market/stage456_preoutcome_decision_engine_v1.py"
    verify_git_blob(repo, rel, EXPECTED_STAGE456_BLOB)
    p = repo / rel
    spec = importlib.util.spec_from_file_location("multiverse_stage456_frozen", p)
    if spec is None or spec.loader is None:
        raise FailClosed("cannot import frozen Stage456 engine")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if tuple(x[0] for x in mod.PROFILES) != PROFILE_IDS:
        raise FailClosed("Stage456 profile family drift")
    if tuple(x[0] for x in mod.GATES) != GATE_IDS:
        raise FailClosed("Stage456 gate family drift")
    if tuple(mod.TEMPLATES) != TEMPLATE_IDS:
        raise FailClosed("Stage456 template family drift")
    if tuple(mod.STAKE_POLICIES) != POLICY_IDS:
        raise FailClosed("Stage456 policy family drift")
    return mod

def verify_governance(repo: Path) -> None:
    base = "v3/historical_all_market/governance/"
    checks = {
        base + "STAGE3_TICKET_FILTER_FAMILY_PREREG_v1.md": EXPECTED_STAGE3_PREREG_BLOB,
        base + "STAGE4_CONSENSUS_AGREEMENT_GATE_PREREG_v1.md": EXPECTED_STAGE4_PREREG_BLOB,
        base + "STAGE5_PORTFOLIO_TEMPLATE_PREREG_v1.md": EXPECTED_STAGE5_PREREG_BLOB,
        base + "STAGE6_BANKROLL_RISK_POLICY_PREREG_v1.md": EXPECTED_STAGE6_PREREG_BLOB,
        base + "STAGE7_TIME_SPLIT_SELECTION_VALIDATION_PREREG_v1.md": EXPECTED_STAGE7_PREREG_BLOB,
        base + "STAGE7_EXECUTION_CONVENTIONS_FREEZE_v1.md": EXPECTED_EXEC_CONVENTIONS_BLOB,
        base + "INDEPENDENT_GOVERNANCE_STAGE7_SETTLEMENT_APPROVE_RECEIPT_v1.json": EXPECTED_APPROVAL_BLOB,
    }
    for rel, exp in checks.items():
        verify_git_blob(repo, rel, exp)
    approval = json.loads((repo / (base + "INDEPENDENT_GOVERNANCE_STAGE7_SETTLEMENT_APPROVE_RECEIPT_v1.json")).read_text(encoding="utf-8"))
    dec = approval.get("explicit_decisions", {})
    if approval.get("verdict") != "APPROVE":
        raise FailClosed("Stage7 independent approval verdict != APPROVE")
    if dec.get("DEV2000_SETTLEMENT_BULK") != "AUTHORIZED_FOR_FROZEN_STAGE7_ONLY":
        raise FailClosed("Settlement authorization missing")
    if dec.get("ECON_HOLDOUT1000") != "SEALED":
        raise FailClosed("HOLDOUT sealed decision missing")
    if dec.get("STAGE7_REALIZED_SCIENTIFIC_TRIAL_COUNT_BEFORE_OPEN") != 0:
        raise FailClosed("pre-open scientific trial count != 0")

def verify_input_hashes(stage2: Path, pred: Path, universe: Path) -> None:
    for p, exp, lab in [
        (stage2, EXPECTED_STAGE2_SHA256, "Stage2"),
        (pred, EXPECTED_PRED_SHA256, "Prediction"),
        (universe, EXPECTED_UNIVERSE_SHA256, "Universe"),
    ]:
        if not p.is_file():
            raise FailClosed(f"{lab} file missing: {p}")
        obs = sha256_file(p)
        if obs != exp:
            raise FailClosed(f"{lab} SHA mismatch: {obs} != {exp}")

def load_universe(path: Path) -> tuple[dict[int, str], dict[str, int]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != EXPECTED_RACES:
        raise FailClosed(f"universe rows={len(rows)}")
    by_idx: dict[int, str] = {}
    idx_by_race: dict[str, int] = {}
    for r in rows:
        try:
            idx = int(r["dev_index"])
        except Exception as e:
            raise FailClosed("invalid universe dev_index") from e
        rid = str(r["race_id"]).strip()
        if idx in by_idx or not rid or rid in idx_by_race:
            raise FailClosed("duplicate/blank universe identity")
        by_idx[idx] = rid
        idx_by_race[rid] = idx
    if set(by_idx) != set(range(1, 2001)):
        raise FailClosed("universe dev_index must be exactly 1..2000")
    return by_idx, idx_by_race

def load_predictions(path: Path) -> dict[str, dict[int, dict[str, float]]]:
    from collections import defaultdict
    pred = defaultdict(dict)
    rows = 0
    with path.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rid = str(r["race_id"]).strip()
            car = int(r["car_no"])
            pa = float(r["candidate_a_win_prob"])
            pb = float(r["b1a_reconstituted_v1_win_prob"])
            if not (math.isfinite(pa) and math.isfinite(pb) and pa > 0 and pb > 0):
                raise FailClosed(f"{rid}/{car}: invalid winner probability")
            if car in pred[rid]:
                raise FailClosed(f"{rid}: duplicate car={car}")
            pred[rid][car] = {"cons": min(pa, pb), "mean": (pa + pb) / 2.0}
            rows += 1
    if rows != 14255 or len(pred) != 2000:
        raise FailClosed(f"prediction cardinality rows={rows} races={len(pred)}")
    return dict(pred)

def load_stage2_pairs(path: Path, target_races: set[str]) -> dict[str, dict[str, dict[str, Any]]]:
    pairs: dict[str, dict[str, dict[str, Any]]] = {}
    total_rows = 0
    with path.open("r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            if not line.strip():
                continue
            total_rows += 1
            r = json.loads(line)
            rid = str(r.get("race_id", "")).strip()
            model = str(r.get("probability_source", ""))
            if model not in MODELS:
                raise FailClosed(f"Stage2 line {ln}: invalid model={model}")
            if r.get("result_fields_included") is not False or r.get("settlement_fields_included") is not False or r.get("realized_roi_computed") is not False:
                raise FailClosed(f"Stage2 line {ln}: outcome firewall drift")
            if rid not in target_races:
                continue
            d = pairs.setdefault(rid, {})
            if model in d:
                raise FailClosed(f"Stage2 duplicate {rid}/{model}")
            d[model] = r
    if total_rows != EXPECTED_STAGE2_ROWS:
        raise FailClosed(f"Stage2 rows={total_rows} expected={EXPECTED_STAGE2_ROWS}")
    if set(pairs) != target_races:
        raise FailClosed(f"Stage2 target race-set mismatch missing={len(target_races-set(pairs))}")
    for rid, d in pairs.items():
        if set(d) != set(MODELS):
            raise FailClosed(f"{rid}: Stage2 model pair incomplete")
    return pairs

def load_settlement_segment(path: Path, expected_segment: str, expected_indices: set[int], by_idx: dict[int, str]) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        raise FailClosed(f"settlement segment missing: {path}")
    rows = load_jsonl(path)
    if len(rows) != len(expected_indices):
        raise FailClosed(f"Settlement {expected_segment} rows={len(rows)} expected={len(expected_indices)}")
    by_race: dict[str, dict[str, Any]] = {}
    seen_idx: set[int] = set()
    for r in rows:
        rid = str(r.get("race_id", "")).strip()
        idx = int(r.get("dev_index"))
        if r.get("segment") != expected_segment:
            raise FailClosed(f"{rid}: settlement segment label drift")
        if idx not in expected_indices or by_idx.get(idx) != rid:
            raise FailClosed(f"{rid}: settlement universe binding failure idx={idx}")
        if rid in by_race or idx in seen_idx:
            raise FailClosed(f"{rid}: duplicate settlement identity")
        sett = r.get("settlements_yen_per_100")
        if not isinstance(sett, dict):
            raise FailClosed(f"{rid}: settlements missing")
        by_race[rid] = r
        seen_idx.add(idx)
    if seen_idx != expected_indices:
        raise FailClosed(f"Settlement {expected_segment}: index-set mismatch")
    return by_race

def global_rank(selected: list[tuple[str, str, dict[str, float]]]) -> list[tuple[str, str, dict[str, float]]]:
    return sorted(selected, key=lambda x: (-float(x[2]["ev"]), -float(x[2]["ratio"]), -float(x[2]["p"]), str(x[0]), str(x[1])))

def allocate_stakes(selected: list[tuple[str, str, dict[str, float]]], policy: str, bankroll: int) -> list[tuple[str, str, dict[str, float], int]]:
    if bankroll < 0:
        raise FailClosed("negative bankroll before race")
    ranked = global_rank(selected)
    if not ranked or bankroll < 100:
        return []
    if policy == "FLAT100":
        n = min(len(ranked), bankroll // 100)
        return [(m, k, v, 100) for m, k, v in ranked[:n]]
    if policy == "RACE2PCT_EQUAL":
        units = int(math.floor((0.02 * bankroll) / 100.0 + 1e-12))
        units = min(units, bankroll // 100)
        if units <= 0:
            return []
        keep_n = min(len(ranked), units)
        kept = ranked[:keep_n]
        base, rem = divmod(units, keep_n)
        out = []
        for i, (m, k, v) in enumerate(kept):
            u = base + (1 if i < rem else 0)
            if u > 0:
                out.append((m, k, v, int(u * 100)))
        return out
    if policy in ("FK10_R2", "FK25_R3"):
        mult, ticket_cap, race_cap = {
            "FK10_R2": (0.10, 0.0025, 0.02),
            "FK25_R3": (0.25, 0.0050, 0.03),
        }[policy]
        raw: list[float] = []
        for _, _, v in ranked:
            p = float(v["p"])
            o = float(v["odds"])
            if not (math.isfinite(p) and math.isfinite(o) and 0 < p <= 1 and o > 0):
                raise FailClosed(f"invalid Kelly inputs p={p} o={o}")
            if o <= 1.0:
                kelly = 0.0
            else:
                kelly = max(0.0, (o * p - 1.0) / (o - 1.0))
            raw.append(mult * kelly)
        s = sum(x for x in raw if x > 0)
        scale = (race_cap / s) if s > race_cap and s > 0 else 1.0
        out = []
        for (m, k, v), rf in zip(ranked, raw):
            frac = min(ticket_cap, max(0.0, rf * scale))
            stake = int(math.floor((bankroll * frac) / 100.0 + 1e-12)) * 100
            if stake > 0:
                out.append((m, k, v, stake))
        if sum(x[3] for x in out) > bankroll:
            raise FailClosed("Kelly allocation exceeds available bankroll")
        return out
    raise FailClosed(f"unknown stake policy={policy}")

@dataclass
class SegmentState:
    bankroll: int = START_BANKROLL
    peak: int = START_BANKROLL
    max_drawdown: float = 0.0
    total_stake: int = 0
    total_return: int = 0
    bet_races: int = 0
    hit_tickets: int = 0
    min_bankroll: int = START_BANKROLL
    def settle_race(self, allocations: list[tuple[str, str, dict[str, float], int]], settlement: dict[str, Any]) -> dict[str, Any]:
        before = self.bankroll
        stake = sum(int(x[3]) for x in allocations)
        if stake > before:
            raise FailClosed(f"race stake {stake} exceeds bankroll {before}")
        ret = 0
        hits = 0
        sett = settlement["settlements_yen_per_100"]
        for m, k, _, s in allocations:
            pay = int(sett.get(m, {}).get(k, 0))
            if pay > 0:
                hits += 1
                ret += pay * (s // 100)
        after = before - stake + ret
        if after < 0:
            raise FailClosed("bankroll went negative")
        self.bankroll = int(after)
        self.total_stake += int(stake)
        self.total_return += int(ret)
        if stake > 0:
            self.bet_races += 1
        self.hit_tickets += hits
        self.peak = max(self.peak, self.bankroll)
        if self.peak > 0:
            self.max_drawdown = max(self.max_drawdown, (self.peak - self.bankroll) / self.peak)
        self.min_bankroll = min(self.min_bankroll, self.bankroll)
        return {"bankroll_before":before,"stake":stake,"return":ret,"bankroll_after":self.bankroll,"bet_ticket_count":len(allocations),"hit_ticket_count":hits}
    def metrics(self) -> dict[str, Any]:
        roi = (self.total_return / self.total_stake - 1.0) if self.total_stake > 0 else None
        return {"realized_roi":roi,"total_stake":self.total_stake,"total_return":self.total_return,"bet_race_count":self.bet_races,"hit_ticket_count":self.hit_tickets,"ending_bankroll":self.bankroll,"maximum_drawdown":self.max_drawdown,"minimum_bankroll":self.min_bankroll,"negative_bankroll":self.min_bankroll < 0}

def config_id(profile: str, gate: str, template: str, policy: str) -> str:
    return f"{profile}:{gate}:{template}:{policy}"

def parse_config(cid: str) -> tuple[str, str, str, str]:
    p = cid.split(":")
    if len(p) != 4 or p[0] not in PROFILE_IDS or p[1] not in GATE_IDS or p[2] not in TEMPLATE_IDS or p[3] not in POLICY_IDS:
        raise FailClosed(f"invalid config id={cid}")
    return p[0], p[1], p[2], p[3]

def profile_map(mod) -> dict[str, tuple]:
    return {x[0]: x for x in mod.PROFILES}

def gate_map(mod) -> dict[str, Any]:
    return {x[0]: x[1] for x in mod.GATES}

def selections_for_base(mod, rid: str, A: dict, B: dict, pred: dict, needed_bases: set[tuple[str, str, str]] | None = None):
    pmap = profile_map(mod)
    gmap = gate_map(mod)
    out: dict[tuple[str, str, str], list[tuple[str, str, dict[str, float]]]] = {}
    profiles = PROFILE_IDS if needed_bases is None else sorted({x[0] for x in needed_bases})
    gates = GATE_IDS if needed_bases is None else sorted({x[1] for x in needed_bases})
    for pid in profiles:
        prof = pmap[pid]
        for gid in gates:
            bases_here = TEMPLATE_IDS if needed_bases is None else [t for p, g, t in needed_bases if p == pid and g == gid]
            if not bases_here:
                continue
            _, elig = mod.consensus_eligible(A, B, prof, gmap[gid])
            for tpl in bases_here:
                sel = mod.select_template(rid, A, elig, pred, tpl)
                out[(pid, gid, tpl)] = global_rank(sel)
    return out

def eval_configs_on_segment(mod, indices: range, by_idx: dict[int, str], pairs: dict[str, dict[str, dict[str, Any]]], pred: dict, settlements: dict[str, dict[str, Any]], cids: list[str], want_ledger_for: str | None = None):
    states = {cid: SegmentState() for cid in cids}
    needed_bases = {parse_config(cid)[:3] for cid in cids}
    policies_by_base: dict[tuple[str, str, str], list[tuple[str, str]]] = {}
    for cid in cids:
        p, g, t, pol = parse_config(cid)
        policies_by_base.setdefault((p, g, t), []).append((cid, pol))
    ledger: list[dict[str, Any]] = []
    for idx in indices:
        rid = by_idx[idx]
        d = pairs[rid]
        A = d["candidate_a"]
        B = d["b1a_reconstituted_v1"]
        base_sel = selections_for_base(mod, rid, A, B, pred, needed_bases)
        for base, cid_policies in policies_by_base.items():
            sel = base_sel[base]
            for cid, pol in cid_policies:
                st = states[cid]
                alloc = allocate_stakes(sel, pol, st.bankroll)
                race = st.settle_race(alloc, settlements[rid])
                if cid == want_ledger_for:
                    ledger.append({"dev_index":idx,"race_id":rid,"configuration_id":cid,**race})
    return states, ledger

def metrics_rank_key(item: tuple[str, dict[str, Any]]):
    cid, m = item
    roi = m["realized_roi"]
    if roi is None:
        roi = float("-inf")
    return (-float(roi), -int(m["ending_bankroll"]), float(m["maximum_drawdown"]), -int(m["bet_race_count"]), cid)

def all_config_ids() -> list[str]:
    return [config_id(p,g,t,s) for p in PROFILE_IDS for g in GATE_IDS for t in TEMPLATE_IDS for s in POLICY_IDS]

def load_bulk_receipt(settlement_dir: Path) -> dict[str, Any]:
    p = settlement_dir.parent / "STAGE7_SETTLEMENT_BULK_RECEIPT_v1.json"
    if not p.is_file():
        p = settlement_dir / "STAGE7_SETTLEMENT_BULK_RECEIPT_v1.json"
    if not p.is_file():
        raise FailClosed("settlement bulk receipt missing")
    x = json.loads(p.read_text(encoding="utf-8"))
    if x.get("status") != "PASS_COMPLETE":
        raise FailClosed("settlement bulk receipt not PASS_COMPLETE")
    if x.get("ECON_HOLDOUT1000") != "SEALED":
        raise FailClosed("settlement receipt HOLDOUT state drift")
    return x

def ab_phase(a, mod, by_idx, pred):
    out = Path(a.out_dir)
    freeze = out / "FINAL_DEV2000_CONFIGURATION_FREEZE_v1.json"
    ab_receipt = out / "STAGE7_AB_SELECTION_RECEIPT_v1.json"
    if freeze.is_file() and ab_receipt.is_file():
        fr = json.loads(freeze.read_text(encoding="utf-8"))
        ar = json.loads(ab_receipt.read_text(encoding="utf-8"))
        if ar.get("status") == "PASS_FINAL_CONFIG_FROZEN" and ar.get("final_configuration_id") == fr.get("final_configuration_id"):
            print(json.dumps({"status":"ALREADY_PASS_AB","final_configuration_id":fr.get("final_configuration_id")}, indent=2))
            return 0
    settlement_dir = Path(a.settlement_dir)
    load_bulk_receipt(settlement_dir)
    A_path = settlement_dir / "DEV2000_SETTLEMENT_A_v1.jsonl"
    B_path = settlement_dir / "DEV2000_SETTLEMENT_B_v1.jsonl"
    A_sett = load_settlement_segment(A_path, "A", set(range(1,1001)), by_idx)
    B_sett = load_settlement_segment(B_path, "B", set(range(1001,1501)), by_idx)
    target = {by_idx[i] for i in range(1,1501)}
    pairs = load_stage2_pairs(Path(a.stage2_jsonl), target)
    cids = all_config_ids()
    if len(cids) != 784 or len(set(cids)) != 784:
        raise FailClosed("frozen configuration cardinality != 784")
    A_states, _ = eval_configs_on_segment(mod, range(1,1001), by_idx, pairs, pred, A_sett, cids)
    A_metrics = {cid: st.metrics() for cid, st in A_states.items()}
    eligible = []
    for cid, m in A_metrics.items():
        if m["bet_race_count"] >= 100 and m["total_stake"] > 0 and not m["negative_bankroll"] and m["maximum_drawdown"] <= 0.35:
            eligible.append((cid, m))
    eligible.sort(key=metrics_rank_key)
    if not eligible:
        halt = {"record":"STAGE7_AB_SELECTION_RECEIPT_v1","status":"NO_A_ELIGIBLE_CONFIGURATION","a_eligible_count":0,"segment_c_opened":False,"scientific_segment_c_scoring_count":0,"ECON_HOLDOUT1000":"SEALED"}
        atomic_json(ab_receipt, halt)
        raise FailClosed("NO_A_ELIGIBLE_CONFIGURATION; Segment C remains untouched")
    top10 = eligible[:10]
    top_ids = [x[0] for x in top10]
    B_states, _ = eval_configs_on_segment(mod, range(1001,1501), by_idx, pairs, pred, B_sett, top_ids)
    B_metrics = {cid: st.metrics() for cid, st in B_states.items()}
    bpass = []
    for cid, m in B_metrics.items():
        if m["realized_roi"] is not None and m["realized_roi"] > 0 and m["bet_race_count"] >= 50 and m["maximum_drawdown"] <= 0.35 and not m["negative_bankroll"]:
            bpass.append((cid, m))
    bpass.sort(key=metrics_rank_key)
    if not bpass:
        halt = {"record":"STAGE7_AB_SELECTION_RECEIPT_v1","status":"NO_B_VALIDATED_CONFIGURATION","A_TOP10":[{"configuration_id":cid, **m} for cid,m in top10],"b_pass_count":0,"segment_c_opened":False,"scientific_segment_c_scoring_count":0,"ECON_HOLDOUT1000":"SEALED"}
        atomic_json(ab_receipt, halt)
        raise FailClosed("NO_B_VALIDATED_CONFIGURATION; Segment C remains untouched")
    final_cid, final_b = bpass[0]
    freeze_obj = {
        "record":"FINAL_DEV2000_CONFIGURATION_FREEZE_v1","status":"FROZEN_BEFORE_SEGMENT_C_OPEN","final_configuration_id":final_cid,
        "frozen_profile":parse_config(final_cid)[0],"frozen_gate":parse_config(final_cid)[1],"frozen_template":parse_config(final_cid)[2],"frozen_stake_policy":parse_config(final_cid)[3],
        "A_TOP10":[{"configuration_id":cid, **m} for cid,m in top10],"B_PASS":[{"configuration_id":cid, **m} for cid,m in bpass],"selected_B_metrics":final_b,
        "stage2_sha256":EXPECTED_STAGE2_SHA256,"prediction_sha256":EXPECTED_PRED_SHA256,"universe_sha256":EXPECTED_UNIVERSE_SHA256,
        "stage456_git_blob":EXPECTED_STAGE456_BLOB,"stage7_prereg_blob":EXPECTED_STAGE7_PREREG_BLOB,"stage7_execution_conventions_blob":EXPECTED_EXEC_CONVENTIONS_BLOB,"independent_approval_blob":EXPECTED_APPROVAL_BLOB,
        "segment_c_opened":False,"scientific_segment_c_scoring_count":0,"ECON_HOLDOUT1000":"SEALED"}
    atomic_json(freeze, freeze_obj)
    freeze_sha = sha256_file(freeze)
    receipt = {"record":"STAGE7_AB_SELECTION_RECEIPT_v1","status":"PASS_FINAL_CONFIG_FROZEN","a_eligible_count":len(eligible),"A_TOP10_count":len(top10),"b_pass_count":len(bpass),"final_configuration_id":final_cid,"final_freeze_sha256":freeze_sha,"segment_c_opened":False,"scientific_segment_c_scoring_count":0,"ECON_HOLDOUT1000":"SEALED"}
    atomic_json(ab_receipt, receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0

def _bootstrap_batch(batch_id: int, idx: Any, stake: Any, ret: Any):
    import numpy as np
    ss = stake[idx].sum(axis=1)
    rr = ret[idx].sum(axis=1)
    out = np.full(ss.shape, np.nan, dtype=np.float64)
    mask = ss > 0
    out[mask] = rr[mask] / ss[mask] - 1.0
    return batch_id, out

def bootstrap_from_ledger(ledger: list[dict[str, Any]], log_path: Path) -> dict[str, Any]:
    import numpy as np
    if len(ledger) != 500:
        raise FailClosed(f"C ledger rows={len(ledger)} expected=500")
    stake = np.asarray([int(r["stake"]) for r in ledger], dtype=np.int64)
    ret = np.asarray([int(r["return"]) for r in ledger], dtype=np.int64)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    all_idx = rng.integers(0, 500, size=(BOOTSTRAP_REPS, 500), dtype=np.int32)
    batch_size = 250
    batches = [(i, all_idx[s:min(s+batch_size, BOOTSTRAP_REPS)]) for i, s in enumerate(range(0, BOOTSTRAP_REPS, batch_size))]
    results: dict[int, Any] = {}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"BOOTSTRAP_START reps={BOOTSTRAP_REPS} seed={BOOTSTRAP_SEED} batches={len(batches)}\n"); log.flush()
        workers = max(1, min(4, os.cpu_count() or 1))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_bootstrap_batch, bid, idx, stake, ret): bid for bid, idx in batches}
            for fut in as_completed(futs):
                bid, vals = fut.result(); results[bid] = vals
                log.write(f"BOOTSTRAP_BATCH_PASS {bid+1}/{len(batches)}\n"); log.flush()
        ordered = np.concatenate([results[i] for i in sorted(results)])
        valid = ordered[np.isfinite(ordered)]
        omitted = int(BOOTSTRAP_REPS - valid.size)
        if valid.size < 9500:
            raise FailClosed(f"bootstrap valid replicates={valid.size}<9500")
        lo, hi = np.percentile(valid, [2.5,97.5], method="linear")
        log.write(f"BOOTSTRAP_PASS valid={valid.size} omitted={omitted} p2.5={lo} p97.5={hi}\n"); log.flush()
    return {"replicates_requested":BOOTSTRAP_REPS,"replicates_valid":int(valid.size),"replicates_zero_stake_omitted":omitted,"seed":BOOTSTRAP_SEED,"percentile_method":"numpy_linear","roi_p2_5":float(lo),"roi_p97_5":float(hi)}

def c_phase(a, mod, by_idx, pred):
    out = Path(a.out_dir)
    freeze_path = out / "FINAL_DEV2000_CONFIGURATION_FREEZE_v1.json"
    final_receipt = out / "STAGE7_FINAL_OOS_RECEIPT_v1.json"
    c_receipt = out / "STAGE7_C_SINGLE_SHOT_RECEIPT_v1.json"
    ledger_path = out / "SEGMENT_C_SINGLE_SHOT_LEDGER_v1.jsonl"
    lock_path = out / "SEGMENT_C_SCORE_LOCK_v1.json"
    boot_log = out / "STAGE7_C_BOOTSTRAP_LOG_v1.txt"
    if final_receipt.is_file():
        x = json.loads(final_receipt.read_text(encoding="utf-8"))
        if x.get("status") == "COMPLETE":
            print(json.dumps({"status":"ALREADY_COMPLETE","verdict":x.get("oos_verdict"),"final_configuration_id":x.get("final_configuration_id")}, indent=2)); return 0
    if not freeze_path.is_file():
        raise FailClosed("final configuration freeze missing; C cannot open")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("status") != "FROZEN_BEFORE_SEGMENT_C_OPEN":
        raise FailClosed("final configuration freeze status invalid")
    if freeze.get("segment_c_opened") is not False or freeze.get("scientific_segment_c_scoring_count") != 0:
        raise FailClosed("freeze is not pre-C state")
    cid = str(freeze.get("final_configuration_id","")); parse_config(cid)
    freeze_sha = sha256_file(freeze_path)
    technical_resume = False
    if lock_path.is_file():
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        if lock.get("final_configuration_id") != cid or lock.get("final_freeze_sha256") != freeze_sha:
            raise FailClosed("existing C score lock conflicts with final freeze")
        technical_resume = not ledger_path.is_file()
    else:
        lock = {"record":"SEGMENT_C_SCORE_LOCK_v1","status":"LOCKED_SINGLE_FROZEN_TRIAL","final_configuration_id":cid,"final_freeze_sha256":freeze_sha,"stage2_sha256":EXPECTED_STAGE2_SHA256,"stage456_git_blob":EXPECTED_STAGE456_BLOB,"stage7_prereg_blob":EXPECTED_STAGE7_PREREG_BLOB,"execution_conventions_blob":EXPECTED_EXEC_CONVENTIONS_BLOB,"bootstrap_reps":BOOTSTRAP_REPS,"bootstrap_seed":BOOTSTRAP_SEED,"scientific_segment_c_scoring_count":1,"ECON_HOLDOUT1000":"SEALED"}
        atomic_json(lock_path, lock)
    settlement_dir = Path(a.settlement_dir); load_bulk_receipt(settlement_dir)
    C_path = settlement_dir / "DEV2000_SETTLEMENT_C_UNTOUCHED_v1.jsonl"
    if ledger_path.is_file():
        ledger = load_jsonl(ledger_path)
        if len(ledger) != 500 or any(r.get("configuration_id") != cid for r in ledger):
            raise FailClosed("existing C ledger malformed/conflicts with frozen config")
        if [int(r["dev_index"]) for r in ledger] != list(range(1501,2001)):
            raise FailClosed("existing C ledger index sequence drift")
    else:
        C_sett = load_settlement_segment(C_path, "C", set(range(1501,2001)), by_idx)
        target = {by_idx[i] for i in range(1501,2001)}
        pairs = load_stage2_pairs(Path(a.stage2_jsonl), target)
        _, ledger = eval_configs_on_segment(mod, range(1501,2001), by_idx, pairs, pred, C_sett, [cid], want_ledger_for=cid)
        if len(ledger) != 500:
            raise FailClosed("C execution did not produce exactly 500 race rows")
        atomic_jsonl(ledger_path, ledger)
    total_stake = total_return = bet_races = hit_tickets = 0
    peak = START_BANKROLL; max_dd = 0.0; min_bank = START_BANKROLL; expected_before = START_BANKROLL
    for r in ledger:
        before = int(r["bankroll_before"]); after = int(r["bankroll_after"])
        if before != expected_before:
            raise FailClosed("C ledger bankroll continuity failure")
        stake = int(r["stake"]); ret = int(r["return"])
        if after != before - stake + ret or after < 0:
            raise FailClosed("C ledger accounting failure")
        total_stake += stake; total_return += ret
        if stake > 0: bet_races += 1
        hit_tickets += int(r["hit_ticket_count"])
        peak = max(peak, after); max_dd = max(max_dd, (peak-after)/peak if peak > 0 else 0.0); min_bank = min(min_bank, after); expected_before = after
    roi = (total_return / total_stake - 1.0) if total_stake > 0 else None
    c_metrics = {"realized_roi":roi,"total_stake":total_stake,"total_return":total_return,"bet_race_count":bet_races,"hit_ticket_count":hit_tickets,"ending_bankroll":expected_before,"maximum_drawdown":max_dd,"minimum_bankroll":min_bank,"negative_bankroll":min_bank < 0}
    boot = bootstrap_from_ledger(ledger, boot_log); lower = boot["roi_p2_5"]
    if roi is not None and roi > 0 and bet_races >= 50 and max_dd <= 0.25 and lower > 0:
        verdict = "OOS_STRONG_PASS"
    elif roi is not None and roi > 0 and bet_races >= 50 and max_dd <= 0.35 and lower <= 0:
        verdict = "OOS_POSITIVE_BUT_UNCERTAIN"
    else:
        verdict = "OOS_FAIL"
    c_rec = {"record":"STAGE7_C_SINGLE_SHOT_RECEIPT_v1","status":"PASS_SINGLE_SHOT_COMPLETE","final_configuration_id":cid,"final_freeze_sha256":freeze_sha,"technical_resume_same_frozen_trial":technical_resume,"ledger_sha256":sha256_file(ledger_path),"c_metrics":c_metrics,"bootstrap":boot,"oos_verdict":verdict,"scientific_segment_c_scoring_count":1,"ECON_HOLDOUT1000":"SEALED"}
    atomic_json(c_receipt, c_rec)
    final = {"record":"STAGE7_FINAL_OOS_RECEIPT_v1","status":"COMPLETE","final_configuration_id":cid,"configuration":{"profile":parse_config(cid)[0],"gate":parse_config(cid)[1],"template":parse_config(cid)[2],"stake_policy":parse_config(cid)[3]},"segment_A_top10":freeze.get("A_TOP10"),"segment_B_selected_metrics":freeze.get("selected_B_metrics"),"segment_C_metrics":c_metrics,"bootstrap":boot,"oos_verdict":verdict,"stage2_sha256":EXPECTED_STAGE2_SHA256,"prediction_sha256":EXPECTED_PRED_SHA256,"universe_sha256":EXPECTED_UNIVERSE_SHA256,"stage456_git_blob":EXPECTED_STAGE456_BLOB,"stage7_prereg_blob":EXPECTED_STAGE7_PREREG_BLOB,"execution_conventions_blob":EXPECTED_EXEC_CONVENTIONS_BLOB,"independent_approval_blob":EXPECTED_APPROVAL_BLOB,"final_freeze_sha256":freeze_sha,"c_ledger_sha256":sha256_file(ledger_path),"scientific_segment_c_scoring_count":1,"post_c_rescue_tuning_performed":False,"model_refit_performed":False,"ECON_HOLDOUT1000":"SEALED","holdout_access":False,"live_wagering_authorized":False}
    atomic_json(final_receipt, final)
    print(json.dumps(final, ensure_ascii=False, indent=2)); return 0

def self_test() -> int:
    sel = [("3rentan","1-2-3",{"ev":1.0,"ratio":2.0,"p":0.20,"odds":10.0}),("2shatan","1-2",{"ev":0.5,"ratio":1.5,"p":0.30,"odds":5.0}),("wide","1=2",{"ev":0.2,"ratio":1.2,"p":0.40,"odds":3.0})]
    assert [x[1] for x in global_rank(sel)] == ["1-2-3","1-2","1=2"]
    assert [x[3] for x in allocate_stakes(sel, "FLAT100", 250)] == [100,100]
    r = allocate_stakes(sel, "RACE2PCT_EQUAL", 100000); assert sum(x[3] for x in r) == 2000 and len(r) == 3
    k = allocate_stakes(sel, "FK10_R2", 100000); assert sum(x[3] for x in k) <= 2000 and all(x[3] % 100 == 0 for x in k)
    st = SegmentState(); settlement = {"settlements_yen_per_100":{"3rentan":{"1-2-3":1000},"2shatan":{},"wide":{}}}
    rr = st.settle_race([("3rentan","1-2-3",sel[0][2],100)], settlement); assert rr["stake"] == 100 and rr["return"] == 1000 and st.bankroll == 100900
    assert len(all_config_ids()) == 784 and len(set(all_config_ids())) == 784
    print(json.dumps({"status":"SELF_TEST_PASS","configuration_count":784}, indent=2)); return 0

def parse_args():
    ap = argparse.ArgumentParser(); ap.add_argument("--phase", choices=("ab","c","self-test"), required=True)
    ap.add_argument("--repo-root"); ap.add_argument("--stage2-jsonl"); ap.add_argument("--prediction-csv"); ap.add_argument("--universe-csv"); ap.add_argument("--settlement-dir"); ap.add_argument("--out-dir")
    return ap.parse_args()

def main() -> int:
    a = parse_args()
    if a.phase == "self-test": return self_test()
    for name in ("repo_root","stage2_jsonl","prediction_csv","universe_csv","settlement_dir","out_dir"):
        if not getattr(a, name): raise FailClosed(f"--{name.replace('_','-')} required for phase {a.phase}")
    repo = Path(a.repo_root).resolve(); verify_governance(repo); mod = import_stage456(repo)
    verify_input_hashes(Path(a.stage2_jsonl), Path(a.prediction_csv), Path(a.universe_csv))
    by_idx, _ = load_universe(Path(a.universe_csv)); pred = load_predictions(Path(a.prediction_csv))
    if a.phase == "ab": return ab_phase(a, mod, by_idx, pred)
    return c_phase(a, mod, by_idx, pred)

if __name__ == "__main__":
    raise SystemExit(main())
