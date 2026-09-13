# MULTIVERSE Independent Auditor — executable bootstrap v2

Status: repository-only candidate
Parent: Issue #450
Runtime: OFF

This successor preserves PR #444's explicit canonical-main ref repair but restores the proven bootstrap semantics from the canonical fixed Lab pipeline.

## Required full Steps YAML

```yaml
steps:
  - label: "MULTIVERSE Independent Auditor"
    agents:
      queue: "independent-auditor"
    command: |
      set -euo pipefail

      git fetch origin main:refs/remotes/origin/main
      git rev-parse --verify refs/remotes/origin/main^{commit}

      rm -rf .mv_dispatcher
      mkdir -p .mv_dispatcher

      git archive refs/remotes/origin/main automation/review_dispatcher_v1 \
        | tar -x -C .mv_dispatcher

      DISPATCHER_REF="$(git rev-parse refs/remotes/origin/main)"
      export MULTIVERSE_DISPATCHER_REF="$$DISPATCHER_REF"

      PYTHONPATH=.mv_dispatcher \
        python3 -c 'import automation.review_dispatcher_v1.dispatcher'

      PYTHONPATH=.mv_dispatcher \
        python3 .mv_dispatcher/automation/review_dispatcher_v1/dispatcher.py \
        --lane AUDITOR \
        --repo fufufu1116/multiverse-research \
        --head "$$BUILDKITE_COMMIT" \
        --output review_job.json

      rm -f .mv_review_pass

      if PYTHONPATH=.mv_dispatcher \
        python3 .mv_dispatcher/automation/review_dispatcher_v1/review.py \
        --job review_job.json \
        --output review_artifact.json \
        --repo-root .; then
        touch .mv_review_pass
      fi

      buildkite-agent artifact upload "review_job.json"
      if [ -f review_artifact.json ]; then
        buildkite-agent artifact upload "review_artifact.json"
      fi

      test -f .mv_review_pass
```

## Why this differs from v1

Build #2314 proved that static token checks were insufficient. The saved pipeline must preserve two separate stages correctly:

1. Buildkite YAML/upload interpolation;
2. runtime shell/Python bootstrap.

The canonical working Lab pipeline already uses inline `PYTHONPATH=.mv_dispatcher` and doubled-dollar runtime variables. v2 deliberately reuses those semantics instead of inventing a new environment-export shape.

## Mandatory pre-external proof

Before any new Owner-gated Auditor Build:
- static v2 preflight passes;
- isolated archive/import smoke test passes;
- focused CI passes;
- no single-dollar `$BUILDKITE_COMMIT` remains in the stored YAML payload;
- no dependency on ambient/exported `$PWD` for Python import root;
- no `FETCH_HEAD` archive source.

This document grants no authority to change external Buildkite Steps or create/retry a Build. Any external mutation and every one-shot review attempt require their own normal authority chain.

`RUNTIME: OFF`
