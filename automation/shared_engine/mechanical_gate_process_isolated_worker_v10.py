"""Mechanical gate for process-isolated consume-only worker v10 Candidate."""
from __future__ import annotations
import json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
CLIENT = ROOT/'automation'/'shared_engine'/'process_isolated_worker_v10.py'
BROKER = ROOT/'automation'/'shared_engine'/'process_isolated_worker_broker_v10.py'
MANIFEST = ROOT/'automation'/'shared_engine'/'PROCESS_ISOLATED_WORKER_V10.json'
README = ROOT/'automation'/'shared_engine'/'README_PROCESS_ISOLATED_WORKER_V10.md'
EXPECTED_BRANCH='agent/automation-shared-engine-process-isolated-worker-v10-20260904-v1'
EXPECTED_PREDECESSOR='32b13303d888214215dd9a87cb6eef180bb52d69'
EXPECTED_PR91='61f4e330fd5b1945dbfbceb223cbc71d205860f2'
EXPECTED_V7='4a72ef46116043094c7a8e494404956925a5b3bf'
EXPECTED_MAIN='040d37f0a4e426cf2e119706484c90cbb48f0e56'
def require(c,code):
    if not c: raise SystemExit(code)
def main():
    m=json.loads(MANIFEST.read_text())
    require(m['candidate_only'] is True,'V10_CANDIDATE_ONLY_REQUIRED'); require(m['branch']==EXPECTED_BRANCH,'V10_BRANCH_BINDING')
    require(m['predecessor_head']==EXPECTED_PREDECESSOR,'V10_PREDECESSOR_BINDING'); require(m['base_pr91_head']==EXPECTED_PR91,'V10_PR91_BINDING')
    require(m['stacked_v7_head']==EXPECTED_V7,'V10_V7_BINDING'); require(m['canonical_main']==EXPECTED_MAIN,'V10_MAIN_BINDING')
    require(all(v is False for v in m['authority'].values()),'V10_AUTHORITY_MUST_BE_FALSE')
    a=m['architecture']; require(a['client_and_engine_distinct_os_processes'] is True,'V10_PROCESS_ISOLATION_REQUIRED')
    require(a['ipc_ops']==['PING','STEP','STOP'],'V10_EXACT_IPC_OPS'); require(a['task_creation_opcode'] is False and a['generic_dispatch'] is False,'V10_CONSUME_ONLY_PROTOCOL')
    require(a['fd_transfer'] is False and a['pickle_or_executable_serialization'] is False,'V10_CAPABILITY_LEAK_SURFACE')
    client=CLIENT.read_text(); broker=BROKER.read_text(); lowered=(client+'\n'+broker).lower()
    for banned in ('af_inet','af_inet6','import requests','import httpx','import urllib','import openai','import anthropic','boto3','scm_rights','send_handle','recv_handle'):
        require(banned not in lowered,f'V10_BANNED_NETWORK_OR_FD_SURFACE:{banned}')
    for banned in ('pickle','marshal','eval(','exec(','os.environ','os.getenv'):
        require(banned not in lowered,f'V10_BANNED_EXEC_OR_SECRET_SURFACE:{banned}')
    for banned in ('exact_v7_shared_engine','local_persistent_worker_v9','import db','import config','create_task(','.submit('):
        require(banned not in client.lower(),f'V10_CLIENT_AUTHORITY_LEAK:{banned}')
    require('socket.AF_UNIX' in client and 'socket.AF_UNIX' in broker,'V10_LOCAL_IPC_REQUIRED')
    require('ALLOWED_OPS = frozenset({"PING", "STEP", "STOP"})' in client,'V10_CLIENT_OPCODE_ALLOWLIST')
    require('ALLOWED_OPS = frozenset({"PING", "STEP", "STOP"})' in broker,'V10_BROKER_OPCODE_ALLOWLIST')
    require('LocalPersistentWorker' in broker,'V10_INHERITED_V9_BROKER_PATH_REQUIRED')
    readme=README.read_text().lower()
    for phrase in ('distinct local os process','not a deployed service','same-os-user debugger/root','remote-provider exactly-once','runtime activation'):
        require(phrase in readme,f'V10_PROOF_CEILING_DOC:{phrase}')
    env=dict(__import__('os').environ); env['PYTHONPATH']='automation/shared_engine:automation'
    cmd=[sys.executable,'-m','unittest','discover','-s','automation/shared_engine/tests','-p','v10_test_*.py','-v']
    completed=subprocess.run(cmd,cwd=ROOT,env=env,check=False); require(completed.returncode==0,'V10_TESTS_FAILED')
    print('V10_MECHANICAL_GATE=PASS'); print('V10_PROCESS_ISOLATION=local_os_address_space'); print('V10_IPC_OPS=PING,STEP,STOP')
    print('V10_TASK_CREATION_AUTHORITY=false'); print('V10_GENERIC_DISPATCH=false'); print('V10_FD_TRANSFER=false')
    print('V10_NETWORK=false'); print('V10_LIVE_PROVIDER=false'); print('V10_SPEND=false'); print('V10_RUNTIME=OFF')
if __name__=='__main__': main()
