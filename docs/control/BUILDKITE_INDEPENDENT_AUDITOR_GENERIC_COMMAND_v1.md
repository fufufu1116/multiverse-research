# MULTIVERSE Independent Auditor — generic dispatcher command v1

Purpose: remove candidate-specific Buildkite head pinning while preserving canonical-main dispatcher loading and fail-closed request binding.

Recommended external command shape:

```bash
set -euo pipefail
git fetch origin main
DISPATCHER_REF="$(git rev-parse FETCH_HEAD)"
export MULTIVERSE_DISPATCHER_REF="$DISPATCHER_REF"
rm -rf .mv_dispatcher
mkdir -p .mv_dispatcher
git archive "$DISPATCHER_REF" automation/review_dispatcher_v1 | tar -x -C .mv_dispatcher
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

Do not include any equality assertion that pins `BUILDKITE_COMMIT` to a historical candidate SHA. The dispatcher itself must validate the exact open PR, request, head, tree, base/main and upstream review lineage.

This document is repository-only guidance. It does not mutate Buildkite, authorize a Build, grant merge/adoption authority, or change Runtime. Runtime remains OFF.
