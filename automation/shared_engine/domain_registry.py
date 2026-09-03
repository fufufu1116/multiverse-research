"""MULTIVERSE shared-engine domain registry v0.1."""
from __future__ import annotations
from dataclasses import dataclass
from typing import FrozenSet, Mapping, Any

class DomainPolicyError(Exception): pass

@dataclass(frozen=True)
class DomainProfile:
    domain: str
    allowed_task_types: FrozenSet[str]
    denied_capabilities: FrozenSet[str]
    protected_resources: FrozenSet[str]
    notes: str = ""

ENGINE_GLOBAL_DENY = frozenset({"canonical_main_mutation","runtime_activation","production_mutation","ruleset_mutation","secret_or_writer_key","live_provider","external_effect","spend"})
CORE = DomainProfile("core", frozenset({"implement","research","review","audit","maintenance"}), ENGINE_GLOBAL_DENY, frozenset({"canonical_main","production_runtime","owner_gate_receipts"}), "Core Candidate work only; canonical adoption remains separate.")
KEIRIN = DomainProfile("keirin", frozenset({"research","analysis","candidate_implementation","review","audit"}), ENGINE_GLOBAL_DENY | frozenset({"result_feature_access","payout_feature_access","real_money_wagering","protected_holdout_open","same_lineage_rescue","model_promotion","post_race_backfill_into_pre"}), frozenset({"ECON_HOLDOUT1000","DEV2000_C_NEW_LINEAGE","RESULT","PAYOUT","untouched_validation"}), "Preserves Keirin scientific firewall and PIT boundaries.")
GENERIC_RESEARCH = DomainProfile("research", frozenset({"research","analysis","candidate_implementation","review","audit"}), ENGINE_GLOBAL_DENY, frozenset(), "Future domain template; no implicit privilege.")
_PROFILES={p.domain:p for p in (CORE,KEIRIN,GENERIC_RESEARCH)}

def get_profile(domain:str)->DomainProfile:
    try:return _PROFILES[domain]
    except KeyError as exc: raise DomainPolicyError(f"UNKNOWN_DOMAIN:{domain}") from exc

def validate_domain_task(domain:str, task_type:str, requested_capabilities:Mapping[str,Any]|None=None, resources:set[str]|frozenset[str]|None=None)->DomainProfile:
    p=get_profile(domain)
    if task_type not in p.allowed_task_types: raise DomainPolicyError(f"TASK_TYPE_DENIED:{domain}:{task_type}")
    for capability,enabled in (requested_capabilities or {}).items():
        if enabled and capability in p.denied_capabilities: raise DomainPolicyError(f"CAPABILITY_DENIED:{domain}:{capability}")
    blocked=set(resources or ()).intersection(p.protected_resources)
    if blocked: raise DomainPolicyError(f"PROTECTED_RESOURCE_DENIED:{domain}:{','.join(sorted(blocked))}")
    return p

def adoption_targets()->tuple[str,...]: return ("core","keirin","research")
