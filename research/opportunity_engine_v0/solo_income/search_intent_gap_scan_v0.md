# Solo Media Search-Intent Gap Scan v0 — qualitative only

Status: RESEARCH_ONLY / INTERNAL / NO PUBLICATION / NO MONETIZATION / RUNTIME OFF
Checked: 2026-09-14

## Purpose
Identify the next page candidate by **problem specificity + evidence gap + monetization fit**, without pretending that current search volume is known.

Important limitation:
- Ubersuggest daily report quota is exhausted.
- Semrush API units are insufficient for current keyword-volume research.
- Therefore this record uses current result composition and official-source complexity only.
- `SERP presence != search volume`; `few Japanese results != proven demand`.

## Candidate A — ClickUp AI plan-generation / price mismatch
Working user problem:
`ClickUp AIの料金が公開ページと自分のWorkspaceで違う。旧プラン/新プランのどちらが適用されるのか知りたい。`

### Fresh evidence
Official ClickUp Help currently says:
- only some Workspaces see the newer plan set;
- current paid plan and price do not automatically change;
- only available upgrade options change;
- new plans include AI instead of selling it only as separate add-ons;
- examples include Core / Business / Business Plus / Enterprise / Max with different AI-credit allowances;
- Business Plus may exist in the Workspace upgrade surface even when not shown on the public pricing page.

Fresh Japanese-result composition also exposes a stale-information risk:
- some Japanese secondary pages still describe older ClickUp AI add-on pricing (for example older $5/member/month material), while current official Help describes the newer partial-rollout AI-included plan model.
- this creates a real evidence-maintenance problem that generic evergreen articles can mishandle.

### Why this is interesting
- high condition complexity;
- official source itself explicitly says Workspace-dependent rollout;
- stale secondary Japanese content exists;
- existing internal checker already handles the state machine;
- monetization path exists through ClickUp affiliate, but commission is conditional/up-to and must not drive editorial recommendation.

### Missing proof
- search volume unknown;
- user pain frequency unknown;
- no external interaction evidence;
- free-workspace affiliate economics do not prove paid decision value.

Internal page priority: **1 — best differentiation test**, not best traffic forecast.

## Candidate B — n8n Cloud execution + AI-credit boundary
Working user problem:
`n8n Cloudはexecutionsだけ見れば料金が分かるのか。AI creditsや外部LLM費用はどう分かれるのか。`

### Fresh evidence
Current official n8n surfaces distinguish:
- workflow executions;
- plan-specific AI-credit allowances;
- external AI/API cost as separate where applicable;
- Starter/Pro execution buckets and AI-credit buckets are not the same measurement.

Current public support material includes distinct Pro-1 / Pro-2 execution and AI-credit tiers. A simple “n8n is charged per execution” article therefore omits an important AI-era boundary.

### Why this is interesting
- strong affiliate rate (official 30% for 12 months) if later approved;
- narrower problem than generic n8n pricing;
- clear official-source normalization task.

### Missing proof
- Japanese search volume unknown;
- exact AI-credit consumption semantics are not fully explained on every public surface, so some outputs must remain `REQUIRES_VENDOR_CONFIRMATION`;
- competitor calculators already discuss general AI/API cost.

Internal page priority: **2 — strong monetization fit, moderate differentiation**.

## Candidate C — Make vs n8n condition-aware workload cost
Working user problem:
`自分の実ワークフローで、Make creditsとn8n executionsのどちらが何単位発生するか。`

### Competitive falsification
Current competitors already cover:
- runs/month;
- Make operations/credits per run;
- scheduled trigger checks;
- n8n executions/run;
- AI/API calls;
- retries;
- hosting/monitoring/support in some calculators.

### Surviving differentiation
Only retain this candidate if it visibly includes the managed evidence layer:
- checked official facts;
- billing/plan generation;
- explicit conflicts/unknowns;
- material-change diff;
- decision invalidation/reconfirmation over time.

### Why it remains relevant
- strongest direct Make/n8n affiliate fit;
- broad buyer decision surface;
- can be the hub page for narrower calculators/checkers.

### Missing proof
- SERP is crowded;
- simple calculator differentiation is gone;
- search volume and achievable ranking are unmeasured.

Internal page priority: **3 — hub only after narrower proof**.

## Candidate D — generic CRM / project-management comparisons
Examples: HubSpot/Pipedrive/monday/ClickUp “best tool” lists.

Current disposition: **DOWNRANK**.
Reason:
- affiliate economics can be attractive;
- but generic comparison intent is heavily commoditized and editorial trust risk rises when commission differs by vendor;
- no current evidence that our managed condition/diff layer has a uniquely painful problem in those broad queries.

Revisit only after a narrow plan-generation/billing-conflict page proves interaction/return value.

## Current page-test ordering
1. `ClickUp AI料金世代チェッカー`
2. `n8n Cloud execution + AI-credit境界`
3. `Make vs n8n 実コスト診断` as hub with managed change-diff
4. broad comparison pages only as support, not first wedge

This ordering is based on current differentiation evidence, **not search-volume estimates**.

## Future lawful test design
When #430 is READY and a separate external-test/revenue boundary is authorized as required:
- publish one problem-specific page before a large content cluster;
- keep it useful with zero affiliate links first if testing information utility;
- measure qualified search/source traffic, checker starts, checker completions, conflict/unknown-state encounters and return visits after a vendor change;
- only then evaluate affiliate outbound behavior under the proper monetization gate.

Do not use pageviews alone as proof.

## Advance criteria
A narrow page deserves expansion when real users show that the managed condition layer matters, for example:
- they reach a different decision because of plan-generation/billing-state handling;
- they encounter a stale/conflicting public claim that the checker resolves safely;
- they return after pricing/packaging changes;
- they use more than the simple arithmetic result.

## Kill criteria
Downrank if:
- users only consume a static answer and ignore the checker/state logic;
- current official pages answer the question directly enough that our maintained layer adds no practical value;
- maintenance burden is high and repeat qualified usage is low;
- demand remains negligible after a valid distribution test.

`KEYWORD_VOLUME=NOT_MEASURED`
`CLICKUP_PLAN_DRIFT=PRIORITY_1_DIFFERENTIATION_TEST`
`N8N_AI_CREDIT_BOUNDARY=PRIORITY_2`
`MAKE_N8N_GENERIC=COMPETED`
`BROAD_CRM_COMPARISON=DOWNRANK`
`NO_PUBLICATION`
`NO_REVENUE`
`NO_NEW_SPEND`
`RUNTIME: OFF`

## Official references
- https://help.clickup.com/hc/en-us/articles/42972527662359-New-plans-and-pricing-options
- https://help.clickup.com/hc/en-us/articles/6303244318999-Pricing-per-user-role-and-plan
- https://help.clickup.com/hc/en-us/articles/6303314345623-Upgrade-your-plan
- https://support.n8n.io/article/n-8-n-cloud-subscription-features-per-tier
- https://n8n.io/pricing/
- https://n8n.io/affiliates/

Secondary Japanese pages were used only to detect staleness/competition risk, never as authority over current vendor terms.
