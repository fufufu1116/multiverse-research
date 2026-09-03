"""Mechanical gate for Shared Engine Local Persistent Worker v9 Candidate."""
from __future__ import annotations

import inspect
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKER = ROOT / 'automation' / 'shared_engine' / 'local_persistent_worker_v9.py'
MANIFEST = ROOT / 'automation' / 'shared_engine' / 'LOCAL_PERSISTENT_WORKER_V9.json'
README = ROOT / 'automation' / 'shared_engine' / 'README_LOCAL_PERSISTENT_WORKER_V9.md'
EXPECTED_BRANCH = 'agent/automation-shared-engine-persistent-worker-v9-20260904-v1'
EXPECTED_PREDECESSOR = '61f4e330fd5b1945dbfbceb223cbc71d205860f2'
EXPECTED_V7 = '4a72ef46116043094c7a8e494404956925a5b3bf'
EXPECTED_MAIN = '040d37f0a4e426cf2e119706484c90cbb48f0e56'


def require(condition, code):
    if not condition:
        raise SystemExit(code)


def main():
    manifest = json.loads(MANIFEST.read_text())
    require(manifest['candidate_only'] is True, 'V9_CANDIDATE_ONLY_REQUIRED')
    require(manifest['branch'] == EXPECTED_BRANCH, 'V9_BRANCH_BINDING')
    require(manifest['predecessor_head'] == EXPECTED_PREDECESSOR, 'V9_PREDECESSOR_BINDING')
    require(manifest['stacked_v7_head'] == EXPECTED_V7, 'V9_V7_BINDING')
    require(manifest['canonical_main'] == EXPECTED_MAIN, 'V9_MAIN_BINDING')
    require(all(v is False for v in manifest['authority'].values()), 'V9_AUTHORITY_MUST_BE_FALSE')
    require(manifest['worker']['task_creation_authority'] is False, 'V9_TASK_CREATION_AUTHORITY')
    require(manifest['worker']['sole_task_state_authority'] == 'automation/shared_engine/db.py', 'V9_SECOND_TASK_AUTHORITY')
    require(manifest['proof']['deployed_daemon'] is False, 'V9_DAEMON_OVERCLAIM')
    require(manifest['proof']['continuous_autonomous_operation'] is False, 'V9_AUTONOMY_OVERCLAIM')

    source = WORKER.read_text()
    lowered = source.lower()
    for banned in ('import requests', 'import httpx', 'import socket', 'import urllib', 'import openai', 'import anthropic', 'boto3', 'subprocess'):
        require(banned not in lowered, f'V9_BANNED_RUNTIME_SURFACE:{banned}')
    for banned in ('os.environ', 'os.getenv', 'create_task(', '.submit('):
        require(banned not in source, f'V9_BANNED_AUTHORITY_SURFACE:{banned}')
    require('def _open_exact_engine' not in source, 'V9_FULL_ENGINE_FACTORY_EXPOSED')
    require('return engine' not in source, 'V9_FULL_ENGINE_CAPABILITY_RETURNED')
    require('db.claim_next_task' in source, 'V9_EXISTING_CLAIM_API_REQUIRED')
    require('engine.reclaim_expired' in source, 'V9_EXISTING_RECLAIM_API_REQUIRED')
    require('engine.renew' in source, 'V9_HEARTBEAT_REQUIRED')
    require('engine.execute_role' in source, 'V9_EXACT_V7_EXECUTION_REQUIRED')
    require('MAX_RUN_CYCLES = 1000' in source, 'V9_BOUNDED_CYCLES_REQUIRED')
    require('MAX_POLL_SECONDS = 5.0' in source, 'V9_BOUNDED_POLL_REQUIRED')

    readme = README.read_text()
    for phrase in ('not a deployed service', 'not authenticated external worker identity', 'remote-provider exactly-once', 'Runtime activation'):
        require(phrase.lower() in readme.lower(), f'V9_PROOF_CEILING_DOC:{phrase}')

    env = dict(__import__('os').environ)
    env['PYTHONPATH'] = 'automation/shared_engine:automation'
    cmd = [sys.executable, '-m', 'unittest', 'discover', '-s', 'automation/shared_engine/tests', '-p', 'test_*.py', '-v']
    completed = subprocess.run(cmd, cwd=ROOT, env=env, check=False)
    require(completed.returncode == 0, 'V9_TESTS_FAILED')

    print('V9_MECHANICAL_GATE=PASS')
    print('V9_SOLE_TASK_STATE_AUTHORITY=shared_engine_sqlite')
    print('V9_TASK_CREATION_AUTHORITY=false')
    print('V9_FULL_ENGINE_FACTORY_EXPOSED=false')
    print('V9_LIVE_PROVIDER=false')
    print('V9_NETWORK=false')
    print('V9_EXTERNAL_EFFECT=false')
    print('V9_SPEND=false')
    print('V9_SECRET_CREDENTIAL=false')
    print('V9_DEPLOYED_DAEMON=false')
    print('V9_RUNTIME=OFF')


if __name__ == '__main__':
    main()
