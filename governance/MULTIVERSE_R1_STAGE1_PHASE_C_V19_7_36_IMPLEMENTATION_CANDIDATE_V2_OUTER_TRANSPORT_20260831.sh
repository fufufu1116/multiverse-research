#!/bin/bash
# V19.7.36 v2 REVIEW-ONLY outer transport. NO LIVE AUTHORITY.
set +e
RC=92
R=/dev/shm/multiverse-r1-stage1-phase-c-v19-7-36-v2-receipts
BLOB=c81345c30c6ad73b016cef6bfc8c36af359e7ee5
SHA256=6fe58f8e89d8029faa78a007ee11796f9c73517123f19a6dcb7b9af70aa85a00
SIZE=4174
deny(){ printf '%s\n' "PHASE_C_V19_7_36_V2_OUTER_DENIED:$1"; [ -d "$R" ] && /bin/mkdir "$R/DENIED_$1" 2>/dev/null; return "$RC"; }
classc(){ P=$(/usr/bin/readlink -f -- "$1") || return 1; [ -n "$P" ] || return 1; while [ "$P" != / ]; do S=$(/usr/bin/stat -Lc '%u %a %F' -- "$P") || return 1; set -- $S; [ "$1" = 0 ] || return 1; M=$2; O=${M: -1}; G=${M: -2:1}; case "$G$O" in *2*|*3*|*6*|*7*) return 1;; esac; P=${P%/*}; [ -n "$P" ] || P=/; done; return 0; }
for P in /bin/bash /bin/mkdir /usr/bin/env /usr/bin/git /usr/bin/python3 /usr/bin/readlink /usr/bin/stat /usr/bin/sha1sum /usr/bin/sha256sum; do classc "$P" || { deny CLASS_C_BOOTSTRAP_TOOL; exit "$RC"; }; done
[ "${CODESPACES:-}" = true ] && [ -n "${CODESPACE_NAME:-}" ] || { deny CODESPACES; exit "$RC"; }
[ ! -e "$R" ] || { printf '%s\n' PHASE_C_V19_7_36_V2_OUTER_DENIED:RECEIPT_ROOT_PREEXISTS; exit "$RC"; }
/bin/mkdir -m 700 "$R" || { printf '%s\n' PHASE_C_V19_7_36_V2_OUTER_DENIED:RECEIPT_ROOT_CREATE; exit "$RC"; }
/bin/mkdir "$R/PRE_PYTHON_STARTED" || { deny PRE_PYTHON_RECEIPT; exit "$RC"; }
X=$(/usr/bin/git -c core.pager=cat -c credential.helper= -c protocol.file.allow=never cat-file blob "$BLOB"; printf x); GRC=$?; [ "$GRC" = 0 ] || { deny BOOTSTRAP_GIT_CAT_FILE; exit "$RC"; }; B=${X%x}; unset X
N=$(LC_ALL=C printf %s "$B" | /usr/bin/stat -c %s /dev/stdin 2>/dev/null); [ "$N" = "$SIZE" ] || { deny BOOTSTRAP_SIZE; exit "$RC"; }
H=$(LC_ALL=C printf %s "$B" | /usr/bin/sha256sum); H=${H%% *}; [ "$H" = "$SHA256" ] || { deny BOOTSTRAP_SHA256; exit "$RC"; }
G=$( { printf 'blob %s\0' "$SIZE"; printf %s "$B"; } | /usr/bin/sha1sum ); G=${G%% *}; [ "$G" = "$BLOB" ] || { deny BOOTSTRAP_GIT_BLOB; exit "$RC"; }
/bin/mkdir "$R/BOOTSTRAP_EXACT_BYTES_PASS" || { deny RECEIPT_EXACT_BYTES; exit "$RC"; }
printf %s "$B" | /usr/bin/env -i CODESPACES=true CODESPACE_NAME="$CODESPACE_NAME" LANG=C LC_ALL=C /usr/bin/python3 -I -S -B -c 'import sys; b=sys.stdin.buffer.read(); exec(compile(b,"<V19.7.36-v2-bootstrap>","exec"),{"__name__":"__main__"})'
P=$?
/bin/mkdir "$R/BOOTSTRAP_RETURNED_RC_$P" 2>/dev/null
printf '%s\n' "PHASE_C_V19_7_36_V2_OUTER_RC=$P"
exit "$P"
