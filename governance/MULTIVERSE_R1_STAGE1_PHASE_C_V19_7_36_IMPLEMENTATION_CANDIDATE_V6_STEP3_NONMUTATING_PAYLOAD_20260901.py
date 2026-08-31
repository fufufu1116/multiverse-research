#!/usr/bin/env python3
"""V19.7.36 v6 exact NONMUTATING Step3 payload. REVIEW-ONLY / NO LIVE AUTHORITY."""
import json,os,sys
EXPECTED_MODE="NONMUTATING"
def deny(x):
    print("PHASE_C_V19_7_36_V6_STEP3_DENIED:"+x, flush=True)
    raise SystemExit(92)
def main():
    if os.environ.get("MULTIVERSE_V36_V6_STEP3_MODE") != EXPECTED_MODE:
        deny("MODE")
    if os.environ.get("MULTIVERSE_V36_V6_CONTROL_FD","").isdigit() is False:
        deny("CONTROL_FD")
    fd=int(os.environ["MULTIVERSE_V36_V6_CONTROL_FD"])
    req=b'{"action":"STEP3_NONMUTATING_PREFLIGHT","version":"V19.7.36-v6"}\n'
    os.write(fd,req)
    out=[]
    total=0
    while True:
        b=os.read(fd,65536)
        if not b: break
        total+=len(b)
        if total > 1<<20: deny("OUTPUT_TOO_LARGE")
        out.append(b)
    try: r=json.loads(b"".join(out))
    except Exception: deny("OUTPUT_JSON")
    if r.get("version")!="V19.7.36-v6" or r.get("action")!="STEP3_NONMUTATING_PREFLIGHT" or r.get("mutations")!=0:
        deny("OUTPUT_SCHEMA")
    print("PHASE_C_V19_7_36_V6_STEP3_NONMUTATING_PASS",flush=True)
    print(json.dumps(r,sort_keys=True,separators=(",",":")),flush=True)
if __name__=="__main__": main()
