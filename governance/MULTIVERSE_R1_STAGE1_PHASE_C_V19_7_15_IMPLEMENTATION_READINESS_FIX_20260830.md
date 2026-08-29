# MULTIVERSE R1 STAGE 1 PHASE C — v19.7.15 IMPLEMENTATION-READINESS FIX

Status: REVISED REQUIREMENTS / NO EXECUTABLE APPROVAL / NO LIVE AUTHORITY
Runtime: OFF

Basis: Independent Lab implementation-readiness result PR #74 comment 5465194791 = FIX_REQUIRED. Incident root cause remains INDETERMINATE.

This amendment closes the missing requirements identified by Independent Lab. It does not approve any executable artifact already present on the remediation branch and does not authorize Auditor or live execution.

## 1. Fixed-marker-only error contract

Every guarded pre-OAuth failure path MUST suppress or transform all raw stdout/stderr before the fixed marker is emitted. No shell/tool diagnostic, Git diagnostic, dynamic fixture/path text, environment value, command-substitution error, exception body, or runner read/launch diagnostic may precede or accompany the allowlisted marker.

Each negative path MUST satisfy:
- stderr exactly equals one fixed allowlisted marker plus its required line ending;
- stdout is empty unless the specific reviewed boundary explicitly defines a fixed allowlisted success marker;
- exit status is nonzero;
- no retry, fallthrough, or failure-to-success conversion.

## 2. Mechanical classification before opaque shell failure

Every guarded command and assignment MUST be checked in a form that classifies command failure before shell expansion, positional parsing, or subsequent operations can produce an opaque exit under set -e/u/pipefail behavior.

Hash-command execution failure and hash mismatch are distinct conditions. `sha256sum` or equivalent command failure MUST be directly checked and mapped to a fixed marker before its output is parsed or compared.

## 3. Runner failure classes

Runner handling MUST distinguish at least:
- runner lookup/blob/file-trust failure;
- runner SHA command failure;
- runner SHA mismatch;
- runner prelaunch/read/parse failure;
- runner runtime nonzero return after successful launch;
- harmless controlled runner success fixture.

Prelaunch/read/parse failure MUST NOT be conflated with runtime nonzero.

## 4. Source-bound synthetic matrix

The final synthetic harness MUST exercise the actual loader/runner source-bound stopping boundaries, not Python-only simulation or representative-region substitution.

Minimum negative fixtures:
- platform mismatch;
- existing path and symlink collision;
- tmpfs type/mode/ownership failure;
- Git clone/control failure;
- canonical-main mismatch;
- post-checkout exact-head mismatch;
- symbolic/non-detached state;
- dirty state;
- runner lookup/blob/file-trust mismatch;
- hash command failure;
- hash mismatch;
- runner prelaunch/read/parse failure;
- runner runtime nonzero.

Minimum positive fixture:
- harmless controlled runner success that reaches the reviewed pre-OAuth transition boundary without performing OAuth.

Every negative fixture MUST assert exact stderr equality to the expected fixed marker and nonzero exit with no preceding dynamic output.

## 5. Exact transport proof

The final Owner-facing loader is reviewable only when all of the following are frozen together:
- exact repository path;
- Git blob SHA;
- exact byte count;
- SHA-256;
- exact internal LF count;
- final-LF YES/NO;
- exact shell-line profile;
- deterministic builder whose output is byte-for-byte identical to the frozen artifact;
- complete Bash parse of the full artifact;
- strict-prefix truncation proof for every nonempty strict prefix, or an independently justified proof with equivalent coverage;
- repository-artifact-only exact direct-copy source;
- final exact head/tree and all artifact identities.

Core MUST NOT manually reconstruct, retype, split, normalize, recompose, or regenerate Owner-facing executable text in chat. Chat-rendered/manual reconstruction is nonauthority. Owner delivery, after all required independent PASS results and fresh Owner approval, may originate only from the exact independently reviewed repository artifact with identical bytes.

## 6. Consolidated authority boundary

The final current exact review unit MUST bind:
fresh dedicated Codespace -> exact frozen pre-OAuth loader -> OAuth/device-code secrecy -> post-OAuth clean-shell reentry -> trusted Python -> Step2.6 -> exact effective scopes/admin gate -> unchanged NONMUTATING Step3 -> STOP/delete.

Success at an intermediate boundary creates no authority beyond the exact frozen chain. Historical PASS is evidence only.

## 7. v19.7.14 preservation

The existing v19.7.14 Step3 immutable-fetch, exact length/SHA/Git-blob verification, same verified bytes execution, no mutable-path reread, trusted Python isolation, NONMUTATING-only, no Step4, and no --apply protections remain required unchanged unless separately justified and independently reviewed.

## Governance status

CAN_PROCEED_TO_EXECUTABLE_IMPLEMENTATION: requires new Independent Lab readiness PASS on this revised requirements package.
CAN_SEND_TO_AUDITOR_NOW: NO
CAN_RUN_LIVE_NOW: NO
PRODUCTION_MUTATION_AUTHORITY: NONE
RUNTIME: OFF
