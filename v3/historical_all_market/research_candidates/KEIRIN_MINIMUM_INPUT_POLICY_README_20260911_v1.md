# KEIRIN Minimum-Input Research Policy

This note exists to make the Owner's explicit policy difficult to lose across chat handoffs.

- Prediction simulation does **not** wait for live odds unless an exact frozen model mathematically requires odds.
- Odds are a downstream price/execution input and a formal ROI-validation input, not a universal prediction prerequisite.
- When live odds are absent, continue prediction/candidate-ticket generation and emit the minimum acceptable purchase odds threshold.
- Missing optional PRE-only fields do not block simulation. Use controlled ablation and retain only fields that materially improve prediction or are explicitly required by the exact frozen model.
- Never use result/payout/future data, post-result reconstruction, post-cutoff backfill, event-roster race-assignment inference, or fuzzy rider joins to fill missing PRE information.

See:
- `KEIRIN_MINIMUM_INPUT_POLICY_20260911_v1.json`
- `KEIRIN_RESEARCH_RESUME_INDEX_20260911_v71.json`
- `KEIRIN_MINIMUM_INPUT_ABLATION_PLAN_20260911_v1.json`
- `KEIRIN_HANDOFF_LOCK_20260911_v1.txt`
- `KEIRIN_MINIMUM_INPUT_EXECUTION_QUEUE_20260911_v1.json`

Progress remains: practical implementation 100%, large-scale simulation / win-pattern exploration 100%, formal scientific validation 85% until genuine scientific evidence increases.
