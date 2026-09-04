"""Shared CURRENT/Resume projection for MULTIVERSE domains."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
import db
from domain_registry import get_profile

@dataclass(frozen=True)
class DomainCurrent:
    domain:str; active_count:int; waiting_count:int; done_count:int; next_task_id:str|None; next_state:str|None

def domain_current(domain:str)->DomainCurrent:
    get_profile(domain)
    tasks=[t for t in db.list_tasks() if t["domain"]==domain]
    active=[t for t in tasks if t["state"] not in ("DONE","ROLLED_BACK","OWNER_GATE","BLOCKED_TECHNICAL","FAILED_CLOSED")]
    waiting=[t for t in tasks if t["state"] in ("OWNER_GATE","BLOCKED_TECHNICAL","FAILED_CLOSED")]
    done=[t for t in tasks if t["state"] in ("DONE","ROLLED_BACK")]
    nxt=sorted(active,key=lambda t:(-t["priority"],t["created_at"]))[0] if active else None
    return DomainCurrent(domain,len(active),len(waiting),len(done),nxt["id"] if nxt else None,nxt["state"] if nxt else None)

def shared_current(bindings:dict[str,Any])->dict[str,Any]:
    if set(bindings)!={"canonical_main","automation_candidate","keirin_research"}: raise ValueError("CURRENT_BINDING_KEYS")
    return {"schema":"multiverse.shared-current.v0.1","authority":{"task_state":"sqlite","chat":False,"github_binding_is_mutation_authority":False},"bindings":dict(bindings),"domains":{d:asdict(domain_current(d)) for d in ("core","keirin","research")},"owner_routing_required":False}

def resume_instruction(snapshot:dict[str,Any],domain:str)->dict[str,Any]:
    if snapshot.get("schema")!="multiverse.shared-current.v0.1": raise ValueError("CURRENT_SCHEMA")
    d=snapshot["domains"].get(domain)
    if d is None: raise ValueError("CURRENT_DOMAIN")
    return {"domain":domain,"task_id":d["next_task_id"],"state":d["next_state"],"fresh_read_required_before_external_claims":True}
