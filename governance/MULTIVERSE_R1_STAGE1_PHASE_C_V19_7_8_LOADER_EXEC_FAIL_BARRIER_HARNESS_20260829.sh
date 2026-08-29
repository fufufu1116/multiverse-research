#!/usr/bin/env bash
set -eu

fail() {
  printf '%s\n' "PHASE_C_V19_7_8_LOADER_BARRIER_HARNESS_FAIL:$1" >&2
  exit 1
}

run_case() {
  label="$1"
  script="$2"
  expected_rc="$3"
  expected_marker="$4"
  forbidden_marker="$5"
  out="$(mktemp)"
  err="$(mktemp)"
  set +e
  /bin/bash --noprofile --norc -c "$script" >"$out" 2>"$err"
  rc=$?
  set -e
  test "$rc" -eq "$expected_rc" || fail "$label:RC=$rc"
  if [ -n "$expected_marker" ]; then
    /usr/bin/grep -Fqx "$expected_marker" "$err" || fail "$label:EXPECTED_MARKER"
  fi
  if [ -n "$forbidden_marker" ]; then
    if /usr/bin/grep -Fq "$forbidden_marker" "$out" "$err"; then
      fail "$label:FORBIDDEN_MARKER"
    fi
  fi
  rm -f "$out" "$err"
  printf '%s\n' "$label:PASS"
}

run_case \
  "shell_exec_failure_barrier" \
  "shopt -s execfail; exec /definitely/not/present || { command printf '%s\\n' 'PHASE_C_V19_7_8_LOADER_EXEC_FAILURE_STOP_DELETE_CODESPACE' >&2; exit 92; }; command printf '%s\\n' 'UNREACHABLE_SHELL_CONTINUATION'" \
  92 \
  "PHASE_C_V19_7_8_LOADER_EXEC_FAILURE_STOP_DELETE_CODESPACE" \
  "UNREACHABLE_SHELL_CONTINUATION"

run_case \
  "exec_success_child_nonzero_no_shell_fallback" \
  "shopt -s execfail; exec /bin/sh -c 'exit 37' || { command printf '%s\\n' 'BARRIER_SHOULD_NOT_RUN' >&2; exit 92; }; command printf '%s\\n' 'UNREACHABLE_SHELL_CONTINUATION'" \
  37 \
  "" \
  "BARRIER_SHOULD_NOT_RUN"

run_case \
  "env_replacement_child_exec_failure_no_shell_fallback" \
  "shopt -s execfail; exec /usr/bin/env -i /definitely/not/present || { command printf '%s\\n' 'BARRIER_SHOULD_NOT_RUN' >&2; exit 92; }; command printf '%s\\n' 'UNREACHABLE_SHELL_CONTINUATION'" \
  127 \
  "" \
  "BARRIER_SHOULD_NOT_RUN"

printf '%s\n' 'PHASE_C_V19_7_8_LOADER_BARRIER_HARNESS_PASS'
