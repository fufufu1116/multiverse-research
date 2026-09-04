"""Mechanical gate for process-isolated consume-only worker v10 Candidate."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

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
EXPECTED_OWNER_APPROVAL=5535323028
EXPECTED_PRIOR_REPLAY_LAB=5530712282
EXPECTED_REPLAY_CAPACITY=256


def require(condition, code):
    if not condition:
        raise SystemExit(code)


def main():
    manifest=json.loads(MANIFEST.read_text())
    require(manifest['candidate_only'] is True,'V10_CANDIDATE_ONLY_REQUIRED')
    require(manifest['branch']==EXPECTED_BRANCH,'V10_BRANCH_BINDING')
    require(manifest['predecessor_head']==EXPECTED_PREDECESSOR,'V10_PREDECESSOR_BINDING')
    require(manifest['base_pr91_head']==EXPECTED_PR91,'V10_PR91_BINDING')
    require(manifest['stacked_v7_head']==EXPECTED_V7,'V10_V7_BINDING')
    require(manifest['canonical_main']==EXPECTED_MAIN,'V10_MAIN_BINDING')
    require(manifest['owner_approval_durable_replay']==EXPECTED_OWNER_APPROVAL,'V10_OWNER_APPROVAL_BINDING')
    require(manifest['prior_replay_lab_fix_required']==EXPECTED_PRIOR_REPLAY_LAB,'V10_PRIOR_REPLAY_LAB_BINDING')
    require(all(v is False for v in manifest['authority'].values()),'V10_AUTHORITY_MUST_BE_FALSE')

    architecture=manifest['architecture']
    require(architecture['client_and_engine_distinct_os_processes'] is True,'V10_PROCESS_ISOLATION_REQUIRED')
    require(architecture['ipc_ops']==['PING','STEP','STOP'],'V10_EXACT_IPC_OPS')
    require(architecture['request_id_replay_denied'] is True,'V10_REPLAY_DENIAL_REQUIRED')
    require(architecture['durable_request_id_replay_denied_across_broker_restart'] is True,'V10_DURABLE_REPLAY_REQUIRED')
    require(architecture['reservation_commits_before_dispatch'] is True,'V10_RESERVE_BEFORE_DISPATCH_REQUIRED')
    require(architecture['replay_capacity']==EXPECTED_REPLAY_CAPACITY,'V10_REPLAY_CAPACITY_BINDING')
    require(architecture['replay_ttl_or_eviction'] is False,'V10_REPLAY_EVICTION_FORBIDDEN')
    require(architecture['replay_reset_or_rotation_api'] is False,'V10_REPLAY_RESET_FORBIDDEN')
    require(architecture['anti_replay_is_workflow_authority'] is False,'V10_ANTI_REPLAY_NONAUTHORITY_REQUIRED')
    require(architecture['task_creation_opcode'] is False and architecture['generic_dispatch'] is False,'V10_CONSUME_ONLY_PROTOCOL')
    require(architecture['fd_transfer'] is False and architecture['pickle_or_executable_serialization'] is False,'V10_CAPABILITY_LEAK_SURFACE')

    client=CLIENT.read_text()
    broker=BROKER.read_text()
    lowered=(client+'\n'+broker).lower()

    for banned in (
        'af_inet','af_inet6','import requests','import httpx','import urllib',
        'import openai','import anthropic','boto3','scm_rights','send_handle','recv_handle'
    ):
        require(banned not in lowered,f'V10_BANNED_NETWORK_OR_FD_SURFACE:{banned}')
    for banned in ('pickle','marshal','eval(','exec(','os.environ','os.getenv'):
        require(banned not in lowered,f'V10_BANNED_EXEC_OR_SECRET_SURFACE:{banned}')
    for banned in ('exact_v7_shared_engine','local_persistent_worker_v9','import db','import config','create_task(','.submit('):
        require(banned not in client.lower(),f'V10_CLIENT_AUTHORITY_LEAK:{banned}')

    require('socket.AF_UNIX' in client and 'socket.AF_UNIX' in broker,'V10_LOCAL_IPC_REQUIRED')
    require('ALLOWED_OPS = frozenset({"PING", "STEP", "STOP"})' in client,'V10_CLIENT_OPCODE_ALLOWLIST')
    require('ALLOWED_OPS = frozenset({"PING", "STEP", "STOP"})' in broker,'V10_BROKER_OPCODE_ALLOWLIST')
    require('class DurableReplayStore' in broker,'V10_DURABLE_REPLAY_STORE_REQUIRED')
    require('REPLAY_CAPACITY = 256' in broker,'V10_REPLAY_CAPACITY_CODE_BINDING')
    require('BEGIN IMMEDIATE' in broker,'V10_REPLAY_SERIALIZED_RESERVATION_REQUIRED')
    require('PRAGMA synchronous=FULL' in broker,'V10_REPLAY_DURABILITY_PRAGMA_REQUIRED')
    require('replay_store.reserve(request)' in broker,'V10_REPLAY_RESERVATION_CALL_REQUIRED')
    require('V10_REQUEST_REPLAY_DENIED' in broker,'V10_REPLAY_REJECTION_REQUIRED')
    require('V10_REQUEST_ID_CONFLICT' in broker,'V10_REPLAY_CONFLICT_REQUIRED')
    require('V10_REPLAY_STORE_FULL' in broker,'V10_REPLAY_CAPACITY_FAIL_CLOSED_REQUIRED')
    require(broker.index('replay_store.reserve(request)') < broker.index('broker.dispatch(request)'),'V10_RESERVATION_MUST_PRECEDE_DISPATCH')
    broker_lower=broker.lower()
    for banned in ('delete from ipc_replay','drop table ipc_replay','vacuum ipc_replay','ttl','expire request_id','evict'):
        require(banned not in broker_lower,f'V10_REPLAY_FORGETTING_SURFACE:{banned}')
    require('LocalPersistentWorker' in broker,'V10_INHERITED_V9_BROKER_PATH_REQUIRED')

    readme=README.read_text().lower()
    for phrase in (
        'distinct local os process',
        'broker/serve-loop/process restart',
        'non-evicting',
        'capacity exhaustion',
        'no reset/rotation api',
        'not a deployed service',
        'same-os-user debugger/root',
        'remote-provider exactly-once',
        'runtime activation',
    ):
        require(phrase in readme,f'V10_PROOF_CEILING_DOC:{phrase}')

    env=dict(__import__('os').environ)
    env['PYTHONPATH']='automation/shared_engine:automation'
    cmd=[sys.executable,'-m','unittest','discover','-s','automation/shared_engine/tests','-p','v10_test_*.py','-v']
    completed=subprocess.run(cmd,cwd=ROOT,env=env,check=False)
    require(completed.returncode==0,'V10_TESTS_FAILED')

    print('V10_MECHANICAL_GATE=PASS')
    print('V10_PROCESS_ISOLATION=local_os_address_space')
    print('V10_IPC_OPS=PING,STEP,STOP')
    print('V10_REQUEST_ID_REPLAY_DENIED=true')
    print('V10_DURABLE_REPLAY_ACROSS_BROKER_RESTART=true')
    print('V10_REPLAY_CAPACITY=256')
    print('V10_REPLAY_EVICTION=false')
    print('V10_REPLAY_RESET_ROTATION=false')
    print('V10_ANTI_REPLAY_WORKFLOW_AUTHORITY=false')
    print('V10_TASK_CREATION_AUTHORITY=false')
    print('V10_GENERIC_DISPATCH=false')
    print('V10_FD_TRANSFER=false')
    print('V10_NETWORK=false')
    print('V10_LIVE_PROVIDER=false')
    print('V10_SPEND=false')
    print('V10_RUNTIME=OFF')


if __name__=='__main__':
    main()
