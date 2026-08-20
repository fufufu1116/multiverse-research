#!/usr/bin/env python3
"""Classify GitHub Actions auto-trigger exposure without executing workflows.

Reads workflow YAML text conservatively. The purpose is to distinguish broad auto
triggers from legacy self-file activation triggers during an Owner-directed pause.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ON_RE = re.compile(r"^(?:['\"]?on['\"]?):\s*(.*?)\s*$")
EVENT_RE = re.compile(r"^\s{2}([A-Za-z0-9_-]+):(?:\s*(.*))?$")
KEY_RE = re.compile(r"^\s{4}([A-Za-z0-9_-]+):\s*(.*?)\s*$")
LIST_RE = re.compile(r"^\s{6}-\s*(.*?)\s*$")
SENSITIVE = ("keirin","keirinjp","tamano","shadow250","sim100","stage7","dev2000","all-market","nextgen","universe","settlement","result","payout")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(' '))


def _parse_inline_list(value: str) -> List[str]:
    value=value.strip()
    if not value:
        return []
    if value.startswith('[') and value.endswith(']'):
        try:
            x=ast.literal_eval(value)
            if isinstance(x,(list,tuple)):
                return [str(v) for v in x]
        except Exception:
            return [v.strip().strip("'\"") for v in value[1:-1].split(',') if v.strip()]
    return [value.strip().strip("'\"")]


def event_blocks(text: str) -> Dict[str, List[str]]:
    lines=text.splitlines()
    on_idx=None
    inline=''
    for i,line in enumerate(lines):
        if line.startswith((' ','\t')):
            continue
        m=ON_RE.match(line)
        if m:
            on_idx=i; inline=m.group(1); break
    if on_idx is None:
        return {}
    if inline:
        return {e: [] for e in _parse_inline_list(inline)}
    block=[]
    for line in lines[on_idx+1:]:
        if line and not line.startswith((' ','\t','#')):
            break
        block.append(line)
    out: Dict[str,List[str]]={}
    current=None
    for line in block:
        m=EVENT_RE.match(line)
        if m:
            current=m.group(1); out[current]=[]; continue
        if current is not None:
            out[current].append(line)
    return out


def filters(lines: List[str]) -> Dict[str,List[str]]:
    out: Dict[str,List[str]]={}
    current: Optional[str]=None
    for line in lines:
        m=KEY_RE.match(line)
        if m:
            key,val=m.group(1),m.group(2)
            current=key
            out.setdefault(key,[])
            out[key].extend(_parse_inline_list(val))
            continue
        m=LIST_RE.match(line)
        if m and current is not None:
            out[current].append(m.group(1).strip().strip("'\""))
    return out


def classify_event(path: str, event: str, block: List[str]) -> Dict[str,object]:
    f=filters(block)
    row={"event":event,"filters":f}
    if event=='push':
        paths=f.get('paths',[])
        ignored=f.get('paths-ignore',[])
        if paths:
            normalized=[p[2:] if p.startswith('./') else p for p in paths]
            if normalized and all(p==path for p in normalized):
                exposure='SELF_FILE_ONLY'
            else:
                exposure='RESTRICTED_PATHS'
        elif ignored:
            exposure='ANY_PATH_EXCEPT_IGNORED'
        else:
            exposure='ANY_PATH'
    elif event in ('pull_request','pull_request_target'):
        paths=f.get('paths',[])
        exposure='PR_RESTRICTED_PATHS' if paths else 'ANY_PR_PATH'
    elif event=='schedule':
        exposure='SCHEDULED'
    elif event=='workflow_dispatch':
        exposure='MANUAL_ONLY'
    elif event=='workflow_call':
        exposure='CALLABLE'
    else:
        exposure='OTHER_AUTO_OR_UNKNOWN'
    row['exposure']=exposure
    return row


def scan(root: Path) -> Dict[str,object]:
    rows=[]
    for p in sorted([*root.glob('*.yml'),*root.glob('*.yaml')]):
        blocks=event_blocks(p.read_text(encoding='utf-8'))
        erows=[classify_event(p.as_posix(),e,b) for e,b in sorted(blocks.items())]
        sensitive=any(t in p.name.lower() for t in SENSITIVE)
        rows.append({"path":p.as_posix(),"keirin_sensitive_name":sensitive,"events":erows})
    sens=[r for r in rows if r['keirin_sensitive_name']]
    def n(exp): return sum(1 for r in sens for e in r['events'] if e['exposure']==exp)
    return {
        "record":"MULTIVERSE_WORKFLOW_TRIGGER_EXPOSURE_v1",
        "workflow_count":len(rows),
        "sensitive_name_count":len(sens),
        "sensitive_push_self_file_only":n('SELF_FILE_ONLY'),
        "sensitive_push_restricted_paths":n('RESTRICTED_PATHS'),
        "sensitive_push_any_path":n('ANY_PATH'),
        "sensitive_push_any_path_except_ignored":n('ANY_PATH_EXCEPT_IGNORED'),
        "sensitive_pull_request_any_path":n('ANY_PR_PATH'),
        "sensitive_pull_request_restricted_paths":n('PR_RESTRICTED_PATHS'),
        "sensitive_schedule":n('SCHEDULED'),
        "rows":rows,
        "scientific_execution_performed":False,
        "result_payout_accessed":False,
        "holdout_accessed":False,
    }


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='.github/workflows'); ap.add_argument('--output'); a=ap.parse_args()
    x=scan(Path(a.root)); s=json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
    if a.output: Path(a.output).write_text(s,encoding='utf-8')
    else: print(s,end='')
    print('MULTIVERSE_WORKFLOW_TRIGGER_EXPOSURE_PASS',
          'self_only='+str(x['sensitive_push_self_file_only']),
          'restricted='+str(x['sensitive_push_restricted_paths']),
          'any_push='+str(x['sensitive_push_any_path']),
          'any_pr='+str(x['sensitive_pull_request_any_path']),
          'schedule='+str(x['sensitive_schedule']))
    return 0

if __name__=='__main__': raise SystemExit(main())
