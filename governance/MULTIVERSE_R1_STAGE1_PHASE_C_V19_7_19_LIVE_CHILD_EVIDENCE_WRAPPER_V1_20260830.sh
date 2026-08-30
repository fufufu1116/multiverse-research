#!/usr/bin/env bash
set +e
set +x
set -u
umask 077
TRANSPORT="${1:-}"
if [ -z "$TRANSPORT" ] || [ ! -f "$TRANSPORT" ] || [ -L "$TRANSPORT" ]; then
  printf '%s\n' 'PHASE_C_V19_7_19_WRAPPER_TRANSPORT_PATH_INVALID'
  exit 0
fi
bytes="$(wc -c < "$TRANSPORT" 2>/dev/null)"
blob="$(git hash-object "$TRANSPORT" 2>/dev/null)"
sha="$(sha256sum "$TRANSPORT" 2>/dev/null | awk '{print $1}')"
if [ "$bytes" != '7969' ] || [ "$blob" != '90369186f103e192674a711f58460b05fd0d8bee' ] || [ "$sha" != 'c7f4f15f3f2e5b29b495c42c86e39774e577cbf484ae4555d3262fb96b299136' ]; then
  printf '%s\n' 'PHASE_C_V19_7_19_WRAPPER_TRANSPORT_IDENTITY_MISMATCH'
  exit 0
fi
/bin/bash --noprofile --norc -n "$TRANSPORT" >/dev/null 2>&1
parse_rc=$?
if [ "$parse_rc" -ne 0 ]; then
  printf '%s\n' "PHASE_C_V19_7_19_WRAPPER_TRANSPORT_PARSE_FAILED_RC=$parse_rc"
  exit 0
fi
printf '%s\n' 'PHASE_C_V19_7_19_WRAPPER_TRANSPORT_IDENTITY_PASS'
printf '%s\n' 'PHASE_C_V19_7_19_LIVE_CHILD_START'
/bin/bash --noprofile --norc "$TRANSPORT"
child_rc=$?
printf '%s\n' "PHASE_C_V19_7_19_LIVE_CHILD_RETURN_RC=$child_rc"
printf '%s\n' 'PHASE_C_V19_7_19_WRAPPER_RETURNING_TO_PARENT_SHELL'
exit 0
