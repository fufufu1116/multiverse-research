#!/usr/bin/env python3
import argparse, fcntl, hashlib, os, subprocess, sys

SRC_BYTES=5301
SRC_BLOB='bc2b638b0db7fa8a0c23f0988cd9946f9e24b590'
SRC_SHA256='370c95f4fa7ec5e390d5fc994fa6954658001c5cfaf524aa96fac1c079be693c'
DST_BYTES=5302
DST_BLOB='fe51117fd3fcaa41537b5f92c84841716af27f74'
DST_SHA256='248dcde06d07902543d480462ebab732d034771820f407fe2cd05fcae54d119e'
ANCHOR=b"tail='''phase_c_bootstrap"
REPL=b"tail=r'''phase_c_bootstrap"

def blob_id(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def verify(data,n,blob,sha):
    return len(data)==n and blob_id(data)==blob and hashlib.sha256(data).hexdigest()==sha

def derive(src):
    if not verify(src,SRC_BYTES,SRC_BLOB,SRC_SHA256):
        raise SystemExit('SOURCE_IDENTITY_FAIL')
    if src.count(ANCHOR)!=1:
        raise SystemExit('SOURCE_ANCHOR_COUNT_FAIL')
    dst=src.replace(ANCHOR,REPL,1)
    if not verify(dst,DST_BYTES,DST_BLOB,DST_SHA256):
        raise SystemExit('TRANSFORM_IDENTITY_FAIL')
    return dst

def sealed_memfd(data):
    fd=os.memfd_create('multiverse-v19-7-17-runner', os.MFD_ALLOW_SEALING)
    os.write(fd,data)
    os.lseek(fd,0,os.SEEK_SET)
    seals=fcntl.F_SEAL_WRITE|fcntl.F_SEAL_GROW|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_SEAL
    fcntl.fcntl(fd,fcntl.F_ADD_SEALS,seals)
    if fcntl.fcntl(fd,fcntl.F_GET_SEALS)!=seals:
        raise SystemExit('MEMFD_SEAL_FAIL')
    snap=os.pread(fd,DST_BYTES+1,0)
    if not verify(snap,DST_BYTES,DST_BLOB,DST_SHA256):
        raise SystemExit('SEALED_OBJECT_IDENTITY_FAIL')
    return fd

def run_bash(fd,parse_only):
    path=f'/proc/self/fd/{fd}'
    argv=['/bin/bash','--noprofile','--norc']
    if parse_only:
        argv.append('-n')
    argv.append(path)
    return subprocess.run(argv,pass_fds=(fd,),check=False).returncode

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('source')
    ap.add_argument('--review-only',action='store_true')
    a=ap.parse_args()
    with open(a.source,'rb',buffering=0) as f:
        src=f.read()
    dst=derive(src)
    fd=sealed_memfd(dst)
    try:
        if run_bash(fd,True)!=0:
            raise SystemExit('BASH_PARSE_FAIL')
        if not verify(os.pread(fd,DST_BYTES+1,0),DST_BYTES,DST_BLOB,DST_SHA256):
            raise SystemExit('POST_PARSE_IDENTITY_FAIL')
        if a.review_only:
            print('V19_7_17_REVIEW_ONLY_PASS')
            return 0
        rc=run_bash(fd,False)
        if rc!=0:
            raise SystemExit(rc)
        return 0
    finally:
        os.close(fd)

if __name__=='__main__':
    sys.exit(main())
