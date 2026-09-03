#!/bin/bash
set -euo pipefail
launcher_src=/src/governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R9_PREARM_RATE_COMMIT_SANITIZER_20260903.c
attack_py=/src/governance/MULTIVERSE_R1_STAGE1_PHASE_C_V19_7_36_V7R13_WHOLE_PROCESS_ATTACK_SELFTEST_20260903.py
cat >/tmp/v7r13-hold.c <<'EOF'
#define _GNU_SOURCE
#include <sys/types.h>
#include <unistd.h>
#include <time.h>
#include <fcntl.h>
volatile unsigned char target_byte __attribute__((used)) = 0x35;
int main(void){
  uid_t r=0,e=0,s=0;
  if(getresuid(&r,&e,&s)!=0||r==0||e!=64173||s!=64173)return 93;
  int fd=open("/tmp/v7r13-hold-reached",O_WRONLY|O_CREAT|O_TRUNC,0644);
  if(fd>=0){if(write(fd,"ok\n",3)!=3)return 94;close(fd);}
  struct timespec ts={2,0};nanosleep(&ts,0);
  return target_byte==0x35?0:95;
}
EOF
gcc -O2 -no-pie -o /tmp/v7r13-hold /tmp/v7r13-hold.c
addr="$(nm -n /tmp/v7r13-hold | grep ' target_byte$' | head -n1 | cut -d' ' -f1)"
test -n "$addr"
gcc -nostdlib -static -fno-stack-protector -fno-asynchronous-unwind-tables -fno-unwind-tables -fno-ident -Wl,--build-id=none -Wl,-z,noexecstack -DV7R13_PROBE_PATH=/tmp/v7r13-hold -o /tmp/v7r13-launcher "$launcher_src"
chown root:root /tmp/v7r13-launcher /tmp/v7r13-hold
chmod 4555 /tmp/v7r13-launcher
chmod 0555 /tmp/v7r13-hold
rm -f /tmp/v7r13-hold-reached
setpriv --reuid=codespace --regid=codespace --init-groups /usr/bin/python3 "$attack_py" "$addr"
printf 'PRELAB_V7R13_WHOLE_PROCESS_INTEGRITY_ATTACK_GATE_PASS=true\n'
