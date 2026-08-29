set +e
set +x
set -u
umask 077
CANONICAL_SHA='74ea95e59ac0654e1a0c1f811a178b3eef7b073c'
CANONICAL_ORIGIN='https://github.com/fufufu1116/multiverse-research.git'
EXEC_ROOT='/dev/shm/multiverse-r1-stage1-phase-c-execution'
git_clean() {
  command env -i PATH='/usr/local/bin:/usr/bin:/bin' HOME="$HOME" LANG='C' LC_ALL='C' GIT_CONFIG_NOSYSTEM='1' GIT_CONFIG_SYSTEM='/dev/null' GIT_CONFIG_GLOBAL='/dev/null' GIT_ATTR_NOSYSTEM='1' GIT_NO_REPLACE_OBJECTS='1' GIT_TERMINAL_PROMPT='0' git "$@"
}
phase_c_verify() (
  set -eu -o pipefail
  test "${CODESPACES:-}" = 'true'
  test -n "${CODESPACE_NAME:-}"
  test "${GH_CONFIG_DIR:-}" = '/dev/shm/multiverse-r1-stage1-phase-c-gh-auth'
  test -d "$EXEC_ROOT"; test ! -L "$EXEC_ROOT"
  test "$(command stat -c '%a' "$EXEC_ROOT")" = '700'
  test "$(command stat -c '%u' "$EXEC_ROOT")" = "$(command id -u)"
  fs="$(command stat -f -c '%T' "$EXEC_ROOT")"; test "$fs" = 'tmpfs' || test "$fs" = 'ramfs'
  test -d "$EXEC_ROOT/.git"; test ! -L "$EXEC_ROOT/.git"
  test "$(git_clean -C "$EXEC_ROOT" rev-parse --verify 'HEAD^{commit}')" = "$CANONICAL_SHA"
  if git_clean -C "$EXEC_ROOT" symbolic-ref -q HEAD >/dev/null 2>&1; then exit 41; else test "$?" -eq 1; fi
  test "$(git_clean -C "$EXEC_ROOT" remote)" = 'origin'
  test "$(git_clean -C "$EXEC_ROOT" config --local --get remote.origin.url)" = "$CANONICAL_ORIGIN"
  if git_clean -C "$EXEC_ROOT" ls-files -v | command grep -q '^[a-z]'; then exit 42; fi
  if git_clean -C "$EXEC_ROOT" ls-files -t | command grep -q '^S '; then exit 43; fi
  for p in tools/multiverse_r1_stage1_phase_c_execution_preflight_v1.py tools/multiverse_r1_stage1_writer_key_provisioner_v1.py tools/multiverse_r1_stage1_writer_key_admin_channel_v1.py; do
    entry="$(git_clean -C "$EXEC_ROOT" ls-tree "$CANONICAL_SHA" -- "$p")"
    mode="${entry%% *}"; rest="${entry#* }"; type="${rest%% *}"; rest="${rest#* }"; oid="${rest%%$'\t'*}"; listed="${rest#*$'\t'}"
    test "$mode" = '100644'; test "$type" = 'blob'; test "$listed" = "$p"
    test -f "$EXEC_ROOT/$p"; test ! -L "$EXEC_ROOT/$p"; test ! -x "$EXEC_ROOT/$p"
    test "$(command stat -c '%h' "$EXEC_ROOT/$p")" = '1'
    test "$(command stat -c '%u' "$EXEC_ROOT/$p")" = "$(command id -u)"
    perm="$(command stat -c '%a' "$EXEC_ROOT/$p")"; (( (8#$perm & 022) == 0 ))
    test "$(git_clean -C "$EXEC_ROOT" hash-object --no-filters -- "$p")" = "$oid"
  done
  test -z "$(git_clean -C "$EXEC_ROOT" status --porcelain=v1 --untracked-files=all)"
)
test -x '/usr/local/python/current/bin/python' || { command printf '%s\n' 'PHASE_C_POST_OAUTH_TRUSTED_PYTHON_BINARY_MISSING_STOP_DELETE_CODESPACE' >&2; return 93; }
test "$(command -v python)" = '/usr/local/python/current/bin/python' || { command printf '%s\n' 'PHASE_C_POST_OAUTH_TRUSTED_PYTHON_RESOLUTION_MISMATCH_STOP_DELETE_CODESPACE' >&2; return 93; }
for p in "$HOME" "$GH_CONFIG_DIR" "$EXEC_ROOT"; do
  test -d "$p" && test ! -L "$p" && test "$(command stat -c '%a' "$p")" = '700' && test "$(command stat -c '%u' "$p")" = "$(command id -u)" || { command printf '%s\n' 'PHASE_C_POST_OAUTH_MEMORY_ROOT_TRUST_FAILED_STOP_DELETE_CODESPACE' >&2; return 93; }
  fs="$(command stat -f -c '%T' "$p")"; { test "$fs" = 'tmpfs' || test "$fs" = 'ramfs'; } || { command printf '%s\n' 'PHASE_C_POST_OAUTH_MEMORY_ROOT_NOT_RAMFS_STOP_DELETE_CODESPACE' >&2; return 93; }
done
test "$(command awk 'END{print NR}' /proc/swaps)" = '1' || { command printf '%s\n' 'PHASE_C_POST_OAUTH_SWAP_PRESENT_STOP_DELETE_CODESPACE' >&2; return 93; }
phase_c_verify
rc=$?
if [ "$rc" -ne 0 ]; then command printf '%s\n' "PHASE_C_POST_OAUTH_EXTERNAL_REVERIFY_FAILED_RC=$rc" >&2; unset rc; return 93; fi
unset rc
command printf '%s\n' 'PHASE_C_POST_OAUTH_CLEAN_SHELL_REENTRY_PASS'