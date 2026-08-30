#!/usr/bin/env python3
import os
import subprocess
import sys
import tempfile
LIVE_INVOCATION=b'/bin/bash --noprofile --norc "$TRANSPORT"'
HARMLESS_INVOCATION=b'/bin/bash --noprofile --norc -c "exit 37"'
def main() -> None:
    if len(sys.argv)!=3:
        raise SystemExit('usage: harness WRAPPER CORRECTED_TRANSPORT')
    wrapper_path,transport_path=sys.argv[1],sys.argv[2]
    wrapper=open(wrapper_path,'rb').read()
    if wrapper.count(LIVE_INVOCATION)!=1:
        raise SystemExit('LIVE_INVOCATION_MULTIPLICITY_FAILURE')
    mutated=wrapper.replace(LIVE_INVOCATION,HARMLESS_INVOCATION,1)
    with tempfile.TemporaryDirectory(prefix='mv-v19-7-19-wrapper-harness-') as td:
        p=os.path.join(td,'wrapper.sh')
        open(p,'wb').write(mutated)
        os.chmod(p,0o700)
        run=subprocess.run(['/bin/bash','--noprofile','--norc',p,transport_path],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    if run.returncode!=0 or run.stderr!=b'':
        raise SystemExit('HARNESS_EXECUTION_FAILURE')
    required=[
        b'PHASE_C_V19_7_19_WRAPPER_TRANSPORT_IDENTITY_PASS\n',
        b'PHASE_C_V19_7_19_LIVE_CHILD_START\n',
        b'PHASE_C_V19_7_19_LIVE_CHILD_RETURN_RC=37\n',
        b'PHASE_C_V19_7_19_WRAPPER_RETURNING_TO_PARENT_SHELL\n',
    ]
    for marker in required:
        if run.stdout.count(marker)!=1:
            raise SystemExit('HARNESS_REQUIRED_MARKER_FAILURE')
    print('V19_7_19_EVIDENCE_PRESERVATION_HARNESS_PASS')
if __name__=='__main__':
    main()
