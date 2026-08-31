#!/usr/bin/env python3
import os, pathlib, subprocess, sys
PY='/usr/local/python/current/bin/python'
ROOT=pathlib.Path('/dev/shm/multiverse-r1-stage1-phase-c-v19-7-30-review')
TARGET=ROOT/'governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_30_PRE_OAUTH_READINESS_LAUNCHER_V1_20260831.py'
RESULT=pathlib.Path('/dev/shm/multiverse-r1-stage1-phase-c-v19-7-31-readiness-result.txt')
def emit(s):
    print(s, flush=True)
    RESULT.write_text(s+'\n', encoding='utf-8')
def main():
    if os.environ.get('CODESPACES')!='true' or not os.environ.get('CODESPACE_NAME'):
        emit('PHASE_C_V19_7_31_DENIED:CODESPACES'); return 92
    if not TARGET.is_file():
        emit('PHASE_C_V19_7_31_DENIED:TARGET_MISSING'); return 92
    env={'PATH':'/usr/local/bin:/usr/bin:/bin','CODESPACES':os.environ['CODESPACES'],'CODESPACE_NAME':os.environ['CODESPACE_NAME']}
    cp=subprocess.run([PY,'-I','-S','-B',str(TARGET)],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if cp.stdout:
        print(cp.stdout,end='' if cp.stdout.endswith('\n') else '\n',flush=True)
    if cp.returncode:
        reason=''
        for line in cp.stdout.splitlines():
            if line.startswith('PHASE_C_V19_7_30_READINESS_DENIED:'):
                reason=line
        emit(reason or f'PHASE_C_V19_7_31_DENIED:UNKNOWN_RC_{cp.returncode}')
        return 92
    emit('PHASE_C_V19_7_31_PRE_OAUTH_READINESS_PASS')
    return 0
if __name__=='__main__':
    raise SystemExit(main())
