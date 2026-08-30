#!/usr/bin/env python3
import argparse, fcntl, importlib.util, os, pathlib, sys

HERE=pathlib.Path(__file__).resolve().parent
TP=HERE/'MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_17_EXECUTABLE_TRANSPORT_V1.py'
spec=importlib.util.spec_from_file_location('transport',TP)
t=importlib.util.module_from_spec(spec); spec.loader.exec_module(t)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('source'); a=ap.parse_args()
    src=pathlib.Path(a.source).read_bytes()
    dst=t.derive(src)
    fd=t.sealed_memfd(dst)
    try:
        st0=os.fstat(fd)
        seals0=fcntl.fcntl(fd,fcntl.F_GET_SEALS)
        snap0=os.pread(fd,t.DST_BYTES+1,0)
        assert t.verify(snap0,t.DST_BYTES,t.DST_BLOB,t.DST_SHA256)
        assert t.run_bash(fd,True)==0
        st1=os.fstat(fd)
        seals1=fcntl.fcntl(fd,fcntl.F_GET_SEALS)
        snap1=os.pread(fd,t.DST_BYTES+1,0)
        assert (st0.st_dev,st0.st_ino)==(st1.st_dev,st1.st_ino)
        assert seals0==seals1
        assert seals1==(fcntl.F_SEAL_WRITE|fcntl.F_SEAL_GROW|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_SEAL)
        assert snap0==snap1==dst
        assert t.verify(snap1,t.DST_BYTES,t.DST_BLOB,t.DST_SHA256)
        print('V19_7_17_SAME_OBJECT_NONLIVE_HARNESS_PASS')
        return 0
    finally:
        os.close(fd)

if __name__=='__main__':
    sys.exit(main())
