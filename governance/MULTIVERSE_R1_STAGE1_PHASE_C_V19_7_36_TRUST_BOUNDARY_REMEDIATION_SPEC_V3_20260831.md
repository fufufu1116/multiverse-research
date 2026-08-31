# MULTIVERSE R1 Stage 1 Phase C — V19.7.36 Trust-Boundary Remediation Spec v3

Status: REVIEW-ONLY / NONCANONICAL / NO LIVE AUTHORITY
Date: 2026-08-31 JST
Supersedes v2 for successor-design review.

All requirements of V19.7.36 spec v2 remain mandatory. This v3 adds a mandatory subprocess trust closure so an implementation cannot validate only the top-level `git`/`gh` executable.

## Mandatory subprocess trust closure
Any separate process started after the authenticated Python boundary is itself a new execution trust boundary. Before first invocation, the frozen implementation MUST enumerate and close the complete effective execution/dependency/configuration authority for that process.

This applies at minimum to `git`, `gh`, browser/device-flow helpers if any, and every helper or executable they can transitively spawn.

For EACH allowed subprocess program, the reviewed implementation MUST freeze a concrete inventory and trust predicate covering:

1. **Top-level executable** — exact absolute path; no PATH discovery at execution time; exact digest/size or independently justified root-controlled immutable platform anchor; owner/mode/type/link/path-chain checks where platform-anchor trust is used.
2. **ELF interpreter / dynamic loader** — exact resolved loader and same trust treatment.
3. **Transitive shared libraries** — complete loader-resolved dependency closure, including indirect dependencies and dynamically loaded libraries that are reachable on the authorized code path. Each must be exact-digest bound or independently immutable/root-controlled against same UID.
4. **Runtime loader authority** — `LD_PRELOAD`, `LD_LIBRARY_PATH`, `LD_AUDIT`, `LD_DEBUG`, loader cache/config and other loader-influencing variables/files must be absent or explicitly frozen/trusted. No same-UID writable loader search directory may participate.
5. **Helper / exec-path closure** — Git exec-path helpers, remote helpers, credential helpers, pager/editor/askpass, shell hooks, protocol helpers, `ssh` or other transports if reachable, `gh` extension/helper mechanisms, browser launchers and any child executable must either be explicitly forbidden or enumerated with the same full executable+loader+library trust closure. Dynamic discovery from user-writable directories is forbidden.
6. **Configuration closure** — system/global/local Git config, includes/includeIf, attributes, hooks path, aliases capable of shell execution, protocol configuration, credential configuration, GH config and extension/config locations must be mechanically reduced to a reviewed closed set. Ambient `$HOME`, repository-local config, XDG config, and user-writable config are not authority unless created fresh in the memory-backed session root with exact reviewed contents and restrictive permissions.
7. **Credential-helper closure** — ambient credential helpers/stores/keychains are forbidden. OAuth/session credentials may exist only in the reviewed memory-backed GH config/credential location. No command may print/export the token to chat or invoke `gh auth token`.
8. **CA/TLS trust material** — effective CA bundle/path and TLS-related environment/config for `git`/`gh` must be explicitly identified and trusted. Custom CA/proxy/curl config/netrc or user-controlled TLS material is forbidden unless exact reviewed material is intentionally provided. Git/gh must not silently inherit ambient `SSL_CERT_*`, `GIT_SSL_*`, `CURL_*`, proxy variables, `.curlrc`, `.netrc`, or equivalent authority.
9. **PATH/environment closure** — subprocesses MUST receive an explicit minimal `env -i`-equivalent environment or exact allowlist. PATH, HOME, XDG paths, locale, proxy, Python, Git, GH, SSL/TLS, loader, pager/editor/askpass and debug variables must be fixed or absent. No shell function, alias, inherited exported function, or current-directory lookup may alter executable resolution.
10. **Working-directory/repository closure** — cwd and repository path must be exact. Git must not discover an unintended parent repository or unsafe repository/config. `GIT_DIR`, `GIT_WORK_TREE`, `GIT_CEILING_DIRECTORIES` and related discovery controls must be explicitly fixed where relevant.
11. **Network protocol closure** — only the exact reviewed HTTPS GitHub endpoints/control-plane operations needed by the authorized stage may be reachable through the subprocess path. Alternate transports (`ssh`, `git://`, arbitrary remote helpers) are forbidden unless separately reviewed. Redirect/proxy behavior must be explicitly constrained where security relevant.
12. **Post-auth drift barrier** — immediately before each security-sensitive subprocess invocation, verify the frozen executable/config/session identities that can change within the same UID threat model, or execute from an immutable/exact-byte-bound substrate that makes re-verification unnecessary. “Verified once earlier in the session” is insufficient for mutable same-UID material.

### No top-level-only shortcut
A statement such as “git executable trusted” or “gh trust predicate passed” is insufficient unless the complete closure above is mechanically proven. If any reachable loader/library/helper/config/credential/CA/PATH/environment authority is outside the frozen closure, fail closed before that subprocess can affect a security decision.

## Updated pre-OAuth matrix requirements
The v2 matrix remains mandatory, with these strengthened interpretations:

- Matrix #11 (`git`) MUST preflight the full subprocess trust closure above for the exact git operations expected pre- and post-OAuth, including loader/libs, exec-path/helpers, config, credential helper, CA/TLS, PATH/env, cwd/repository discovery and network protocol authority.
- Matrix #14 (`gh` / browser device flow) MUST preflight the same full closure for `gh` and any browser/helper process. Anything that necessarily depends on credentials not yet issued may be marked `POST_OAUTH_ONLY`, but executable/loader/library/helper/config/CA/environment trust MUST be closed before OAuth begins.
- Any additional subprocess discovered by the implementation becomes a mandatory matrix entry; it may not be silently invoked because it is a common system utility.

## Receipt taxonomy additions
The frozen implementation MUST provide stage-specific nonsecret failures at minimum for:
- `SUBPROCESS_EXECUTABLE_IDENTITY_*`
- `SUBPROCESS_ELF_LOADER_*`
- `SUBPROCESS_SHARED_LIBRARY_*`
- `SUBPROCESS_LOADER_AUTHORITY_*`
- `SUBPROCESS_HELPER_EXEC_PATH_*`
- `SUBPROCESS_CONFIG_*`
- `SUBPROCESS_CREDENTIAL_HELPER_*`
- `SUBPROCESS_CA_TLS_*`
- `SUBPROCESS_ENVIRONMENT_*`
- `SUBPROCESS_REPOSITORY_DISCOVERY_*`
- `SUBPROCESS_NETWORK_PROTOCOL_*`
- `SUBPROCESS_PREEXEC_DRIFT_*`

Python-not-started and receipt-primary/fallback requirements from v2 remain mandatory.

## Preserved requirements
The v2 bootstrap root of trust, authenticated Python runtime boundary, pure stdlib/zip/lib-dynload exact-byte closure, native transitive ELF dependency closure, non-circular authenticated source/verifier, 16-item pre-OAuth matrix, once-open/same-memory rule, sealed memfd PyNaCl/cffi, isolated `-I -S -B`, sanitized environment, current-main rebootstrap, exact ADMIN/PREFLIGHT/Step3 bindings, parent-shell survival, observability and Owner-burden gate all remain mandatory without weakening.

## Explicit nonauthority
This design spec authorizes no Live execution, OAuth, Step3, Step4, `--apply`, production mutation, main/ruleset mutation, writer-secret work, merge, workflow dispatch, Runtime state/tasks/Sources/scheduler, Runtime branch/sequence0, activation receipt/tag, or Runtime activation.

Runtime remains OFF.