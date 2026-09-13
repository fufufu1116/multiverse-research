# Independent Auditor genericization evidence v1

Observed failure source from Buildkite build #2186 command log:

- external pipeline fetched canonical `main`;
- before `dispatcher.py` ran, it executed an equality test pinning `BUILDKITE_COMMIT` to the historical PR #395 candidate head;
- PR #422 correctly used a different head, so `set -euo pipefail` terminated the step immediately;
- therefore the failure was external pipeline configuration drift, not PR #422 review-request arbitration.

Repository candidate in this branch adds:

1. a static preflight that rejects candidate-specific `BUILDKITE_COMMIT` SHA hard pins;
2. tests covering generic pass, hard-pin fail, missing main fetch, and missing dynamic head binding;
3. a canonical-main generic command template for the external Independent Auditor pipeline.

External Buildkite mutation remains a separate Owner-gated action. No Build, Retry, merge, adoption, deployment, provider, credential, spend, live effect, or Runtime authority is granted here. Runtime OFF.
