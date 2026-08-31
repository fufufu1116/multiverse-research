#!/bin/bash
# V19.7.36 v3 REVIEW-ONLY / NO LIVE AUTHORITY.
# This entry is NOT for raw interactive paste. It requires platform-inherited fds.
set +e
set -C
RC=92
: "${MULTIVERSE_V36_ENTRY_FD:=}"
: "${MULTIVERSE_V36_PYTHON_FD:=}"
: "${MULTIVERSE_V36_ATTEST_FD:=}"
R=/dev/shm/multiverse-r1-stage1-phase-c-v19-7-36-v3-receipt
fail(){ printf '%s\n' "PHASE_C_V19_7_36_V3_OUTER_DENIED:$1"; return "$RC"; }
# No external executable is used before the inherited-fd gate below.
case "$MULTIVERSE_V36_ENTRY_FD:$MULTIVERSE_V36_PYTHON_FD:$MULTIVERSE_V36_ATTEST_FD" in
  *[!0-9:]*|::*|:*:|:*) fail INHERITED_FD_SET_INVALID; exit "$RC";;
esac
# Pre-Python observability: bash noclobber creates a new pathname only; preexistence/symlink fails.
if ! : > "$R" 2>/dev/null; then fail PRE_PYTHON_RECEIPT_EXCLUSIVE_CREATE; exit "$RC"; fi
printf '%s\n' 'PHASE_C_V19_7_36_V3_PRE_PYTHON_ENTRY_STARTED' >&2
# The platform contract requires ENTRY_FD to already refer to these exact entry bytes. A caller
# that merely pasted this artifact has no authority to proceed and cannot satisfy that contract.
# Python is invoked by the already-open executable object. No Python pathname is reopened here.
MULTIVERSE_V36_ATTEST_FD="$MULTIVERSE_V36_ATTEST_FD" \
MULTIVERSE_V36_PLATFORM_ENTRY_FD="$MULTIVERSE_V36_ENTRY_FD" \
MULTIVERSE_V36_PLATFORM_PYTHON_FD="$MULTIVERSE_V36_PYTHON_FD" \
CODESPACES="${CODESPACES:-}" CODESPACE_NAME="${CODESPACE_NAME:-}" LANG=C LC_ALL=C \
/proc/self/fd/"$MULTIVERSE_V36_PYTHON_FD" -I -S -B -c 'import os,sys; fd=int(os.environ["MULTIVERSE_V36_ENTRY_FD_PAYLOAD"]); b=os.read(fd,16<<20); exec(compile(b,"<v19.7.36-v3-runtime>","exec"),{"__name__":"__main__"})' 2>/dev/null
P=$?
printf '%s\n' "PHASE_C_V19_7_36_V3_OUTER_RC=$P"
exit "$P"
