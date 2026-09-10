# Opportunity Engine v0 — Execution Surface / AI Diversity Doctrine

Status: RESEARCH PROTOTYPE ONLY
Runtime: OFF

## Central MULTIVERSE is the AI council infrastructure

Opportunity Engine must not build a second provider-orchestration system. Reuse the canonical MULTIVERSE multi-model/provider path when it becomes governed and available. Opportunity Engine owns the business/opportunity questions, frozen evidence, economic hypotheses, leverage choices, forecasts and measured outcomes; canonical MULTIVERSE owns provider execution, evidence/receipt handling, role separation, review infrastructure and authority boundaries.

Multiple roles performed by the same provider/model are useful for structured critique but are not independent minds. Positive/no-blocker confidence for material opportunities should require cross-provider diversity. Negative evidence may block from one provider when sufficiently severe and evidence-bound. Majority vote never creates truth or execution authority.

Additional paid providers are a research expense, not a badge of quality. Prefer official/deterministic checks and cheap local falsification first. Add one cross-provider challenge only when decision value, uncertainty, disagreement or severity justifies the cost. A third provider is mainly useful when two providers remain materially divided after cheaper falsification.

## Short-wave / one-hit archetype

A very short-lived opportunity may be intentionally operated as a one-hit unit when:
- demand life is short;
- build time is a small fraction of demand life;
- payback is fast;
- attention/profit is concentrated in a brief spike;
- an explicit exit trigger exists;
- the tactic is lawful and non-deceptive.

Internal name: `SHORT_WAVE_ONE_HIT`.
Optional future UI label: `使い切り百人将`.

One large hit does not qualify a unit for durable promotion. Promotion requires repeated evidence, repeatability, residual assets, automation and a credible ceiling without proportional owner labor.

## Phone, Mac and cloud are execution surfaces, not strategy

The system must remain operable without a Mac where cloud services can carry the workload. A phone can serve as command surface for research, GitHub control, web-app creation, cloud-hosted agents/builders, hosted databases, hosted CI/builds and remote compute where the service supports those workflows.

A Mac is a force multiplier, especially for:
- Apple-native Xcode/simulator workflows;
- local iOS debugging;
- large local simulations and batch tests;
- local data analysis;
- multiple parallel development tools/windows;
- long-running local jobs;
- privacy-sensitive datasets that should remain local;
- offline/local development and reproducible test environments.

Do not make the entire Opportunity Engine depend on one physical Mac. Keep repository state, frozen evidence and portable workflows recoverable elsewhere. Prefer replaceable cloud services for commodity plumbing, and keep a migration path for important dependencies.

## App completion doctrine

Web applications can often be built and deployed through phone-accessible cloud development tools. Native mobile applications can also use cloud build systems, including remote macOS infrastructure for iOS, but local Apple-native work remains materially easier and more complete with a Mac/Xcode environment.

Therefore classify each task before execution:
- phone/cloud feasible;
- cloud Mac/build bridge feasible;
- Mac preferred for throughput/debugging;
- Mac required only for a deliberately selected local Apple toolchain.

The owner should not delay research or lightweight prototypes merely because a Mac is not yet available. When a Mac becomes available, use it first where it removes the highest bottleneck rather than moving every task to local execution.

See `execution_environment.py`, `test_execution_environment.py`, `opportunity_archetype.py`, `test_opportunity_archetype.py`, `review_independence_gate.py`, and `provider_escalation.py`.
