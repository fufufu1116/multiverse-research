# MULTIVERSE Independent Auditor — Hosted explicit canonical-main ref v1

Purpose: make the external Hosted Buildkite Auditor command robust against `FETCH_HEAD` ambiguity while preserving canonical-main dispatcher loading, Hosted queue routing, and exact candidate-head binding.

Recommended full Steps YAML:

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

      export MULTIVERSE_DISPATCHER_REF="$(git rev-parse refs/remotes/origin/main)"
      export PYTHONPATH="$PWD/.mv_dispatcher"

      python3 .mv_dispatcher/automation/review_dispatcher_v1/dispatcher.py \
        --lane AUDITOR \
        --repo fufufu1116/multiverse-research \
        --head "$BUILDKITE_COMMIT" \
        --output review_job.json

      rm -f .mv_review_pass

      if python3 .mv_dispatcher/automation/review_dispatcher_v1/review.py \
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

Do not use `FETCH_HEAD` as the dispatcher archive source. Do not hard-pin `BUILDKITE_COMMIT` to a historical candidate SHA. The dispatcher remains responsible for exact PR/request/head/tree/base/upstream validation.

This document is repository-only guidance. It does not mutate Buildkite or authorize a Build, Retry, merge, adoption, deployment, provider call, credential use, spend, live effect, or Runtime activation. Runtime OFF.
