#!/bin/bash
# V19.7.36 v3 REVIEW-ONLY / NO LIVE AUTHORITY.
# Must be executed by an inherited exact-object fd; raw paste/path execution is forbidden.
set +e
set -C
RC=92
: "${MULTIVERSE_V36_ENTRY_FD:=}"
: "${MULTIVERSE_V36_PYTHON_FD:=}"
: "${MULTIVERSE_V36_RUNTIME_FD:=}"
: "${MULTIVERSE_V36_ATTEST_FD:=}"
R=/dev/shm/multiverse-r1-stage1-phase-c-v19-7-36-v3-receipt
fail(){ printf '%s\n' "PHASE_C_V19_7_36_V3_OUTER_DENIED:$1"; return "$RC"; }
case "$MULTIVERSE_V36_ENTRY_FD:$MULTIVERSE_V36_PYTHON_FD:$MULTIVERSE_V36_RUNTIME_FD:$MULTIVERSE_V36_ATTEST_FD" in *[!0-9:]*|::*|:*:|:*) fail INHERITED_FD_SET_INVALID; exit "$RC";; esac
EXPECTED_SOURCE=/proc/self/fd/$MULTIVERSE_V36_ENTRY_FD
[ "${BASH_SOURCE[0]:-}" = "$EXPECTED_SOURCE" ] || { fail OUTERMOST_ENTRY_NOT_FD_BOUND; exit "$RC"; }
if ! : > "$R" 2>/dev/null; then fail PRE_PYTHON_RECEIPT_EXCLUSIVE_CREATE; exit "$RC"; fi
printf '%s\n' PHASE_C_V19_7_36_V3_PRE_PYTHON_ENTRY_STARTED >&2
# No external verifier/pathname is used before this point. The already-running bash process and
# inherited fd set are the external Class-A handoff defined by the platform-anchor contract.
MULTIVERSE_V36_ATTEST_FD="$MULTIVERSE_V36_ATTEST_FD" \
MULTIVERSE_V36_PLATFORM_ENTRY_FD="$MULTIVERSE_V36_ENTRY_FD" \
MULTIVERSE_V36_PLATFORM_PYTHON_FD="$MULTIVERSE_V36_PYTHON_FD" \
MULTIVERSE_V36_RUNTIME_FD="$MULTIVERSE_V36_RUNTIME_FD" \
CODESPACES="${CODESPACES:-}" CODESPACE_NAME="${CODESPACE_NAME:-}" LANG=C LC_ALL=C \
/proc/self/fd/"$MULTIVERSE_V36_PYTHON_FD" -I -S -B -c 'import os; fd=int(os.environ["MULTIVERSE_V36_RUNTIME_FD"]); chunks=[]
while True:
 b=os.read(fd,65536)
 if not b: break
 chunks.append(b)
payload=b"".join(chunks); exec(compile(payload,"<v19.7.36-v3-runtime>","exec"),{"__name__":"__main__"})'
P=$?
printf '%s\n' "PHASE_C_V19_7_36_V3_OUTER_RC=$P"
exit "$P"
