#!/usr/bin/env python3
"""Review-only pre-Lab mechanical gate. It cannot grant security/audit authority."""
from __future__ import annotations
import ast, hashlib, json, os, pathlib, py_compile, re, shutil, subprocess, sys, tempfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
RC=92
EXPECTED={
 '.devcontainer/Dockerfile':'dockerfile',
 '.devcontainer/devcontainer.json':'json',
 '.devcontainer/v19_7_36_requirements.txt':'text',
 'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7_ROOT_ANCHOR_PRODUCER_20260901.go':'go',
 'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7_CONTROL_PLANE_RUNNER_20260901.go':'go',
 'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7_CAPABILITY_TRIGGER_20260901.go':'go',
 'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7_OWNER_WAKE_CLIENT_20260901.go':'go',
 'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7_RUNTIME_20260901.py':'python',
 'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V7_RECURSIVE_CLOSURE_MANIFEST_20260901.py':'python',
 'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_BINDING_20260901.json':'json',
 'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_NONMUTATING_PAYLOAD_20260901.py':'python',
}

def fail(cat,msg):
 print(f'PRE_LAB_MECHANICAL_GATE_DENIED:{cat}:{msg}',file=sys.stderr);raise SystemExit(RC)
def data(rel): return (ROOT/rel).read_bytes()
def kind(rel,b):
 s=b.lstrip()
 if rel.endswith('.json'):
  try: json.loads(b)
  except Exception as e: fail('JSON_PARSE',f'{rel}:{type(e).__name__}')
  return 'json'
 if rel.endswith('.py'):
  try: ast.parse(b.decode('utf-8'),filename=rel)
  except Exception as e: fail('PYTHON_PARSE',f'{rel}:{type(e).__name__}')
  return 'python'
 if rel.endswith('.go'):
  if not s.startswith(b'package main'): fail('GO_CONTENT_TYPE',rel)
  return 'go'
 if pathlib.PurePosixPath(rel).name=='Dockerfile':
  if not re.search(br'(?m)^FROM\s+',b): fail('DOCKERFILE_CONTENT_TYPE',rel)
  return 'dockerfile'
 if rel.endswith('.sh'):
  return 'shell'
 return 'text'
def run(cmd,env=None):
 p=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
 if p.returncode: fail('BUILD_OR_SYNTAX',f'{cmd[0]}:{p.stderr[-500:]}')

def git_blob(b):
 import hashlib
 h=hashlib.sha1();h.update(f'blob {len(b)}\0'.encode());h.update(b);return h.hexdigest()

def check_binding():
 rel='governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_BINDING_20260901.json'
 q=json.loads(data(rel)); s=q['step3']; target=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_IMPLEMENTATION_CANDIDATE_V6_STEP3_NONMUTATING_PAYLOAD_20260901.py'; b=target.read_bytes()
 if s['git_blob']!=git_blob(b): fail('STEP3_BLOB_MISMATCH',target.name)
 if s['sha256']!=hashlib.sha256(b).hexdigest(): fail('STEP3_SHA256_MISMATCH',target.name)
 if s['size']!=len(b): fail('STEP3_SIZE_MISMATCH',target.name)
 if s.get('mode')!='NONMUTATING' or s.get('mutations')!=0: fail('STEP3_MODE',target.name)

def check_docker_sources():
 b=data('.devcontainer/Dockerfile').decode()
 for n,line in enumerate(b.splitlines(),1):
  m=re.match(r'^\s*(COPY|ADD)\s+(?:--\S+\s+)*([^\s]+)',line)
  if not m: continue
  src=m.group(2)
  if src.startswith('http://') or src.startswith('https://') or src.startswith('--from='): continue
  if any(c in src for c in '*?['): fail('DOCKER_GLOB_UNSUPPORTED',f'line{n}:{src}')
  if not (ROOT/src).exists(): fail('DOCKER_COPY_SOURCE_MISSING',f'line{n}:{src}')

def main():
 for rel,want in EXPECTED.items():
  p=ROOT/rel
  if not p.is_file(): fail('EXPECTED_FILE_MISSING',rel)
  got=kind(rel,p.read_bytes())
  if got!=want: fail('ROLE_CONTENT_MISMATCH',f'{rel}:{want}!={got}')
 # swapped-role sentinels
 if data('.devcontainer/Dockerfile').lstrip().startswith(b'{'): fail('ASSEMBLY_SWAP','Dockerfile_is_JSON')
 if data('.devcontainer/devcontainer.json').lstrip().startswith(b'FROM '): fail('ASSEMBLY_SWAP','devcontainer_is_Dockerfile')
 check_docker_sources(); check_binding()
 with tempfile.TemporaryDirectory(prefix='multiverse-prelab-') as td:
  for rel,want in EXPECTED.items():
   p=ROOT/rel
   if want=='python':
    try: py_compile.compile(str(p),cfile=str(pathlib.Path(td)/(p.name+'.pyc')),doraise=True)
    except Exception as e: fail('PY_COMPILE',f'{rel}:{type(e).__name__}')
   elif want=='go':
    if not shutil.which('go'): fail('GO_TOOL_UNAVAILABLE',rel)
    env=dict(os.environ);env['CGO_ENABLED']='0'
    run(['go','build','-trimpath','-buildvcs=false','-o',str(pathlib.Path(td)/(p.stem)),str(p)],env)
   elif want=='shell':
    if not shutil.which('bash'): fail('BASH_UNAVAILABLE',rel)
    run(['bash','-n',str(p)])
 # devcontainer semantics
 q=json.loads(data('.devcontainer/devcontainer.json'))
 if q.get('build',{}).get('dockerfile')!='Dockerfile' or q.get('build',{}).get('context')!='..': fail('DEVCONTAINER_BUILD_MAPPING','unexpected')
 print('PRE_LAB_MECHANICAL_GATE_PASS')
 print('DOCKER_STATIC_COPY_SOURCE_CHECK_PASS')
 print('REAL_DOCKER_IMAGE_BUILD_NOT_RUN_BY_THIS_SCRIPT')
 print('SECURITY_AUTHORITY_GRANTED=false')
if __name__=='__main__': main()
