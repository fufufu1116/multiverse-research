# Multiverse Keirin — Provider Inquiry Questions Draft v1

Status: PREPARED ONLY — DO NOT SEND WITHOUT OWNER APPROVAL
Date: 2026-08-19 JST

## Purpose

Ask only the minimum questions required to determine whether a provider can support a reproducible PRE-only research and future operational pipeline.

Do not disclose proprietary model details beyond what is necessary.

## Verified public contact targets

### JKA / KEIRIN.JP general inquiry

Public contact:
`webmaster@keirin-autorace.or.jp`

Role status:
`GENERAL_KEIRIN_JP/JKA_INQUIRY_CONTACT — NOT VERIFIED AS DATA-LICENSING DESK`

If used, the message must explicitly ask to be redirected to the correct department if data licensing / authorized feed provision is handled elsewhere.

### Team-Nave product/service inquiry

Public contact:
`support@team-nave.com`

Role status:
`VERIFIED_PUBLIC_PRODUCT_SERVICE_INQUIRY_CONTACT`

Public product pages currently confirm keirin AI and CTC betting API, but not an equivalent public keirin database/data-feed API.

## Core questions for JKA / official feed route

1. Is there an official data provision/feed/service for keirin race information available to external researchers, developers, businesses, or contracted information providers?
2. If yes, what application/contract path governs access and reuse?
3. Does the feed include point-in-time pre-race race-card data with historical snapshots, including rider score/class/style, S/B/H, and finishing-technique counts (逃/捲/差/マ)?
4. Is rider-introduction / leg-show lineup information available as structured data with observation timestamp and within-line order?
5. Is there a structured field identifying race rule/regime, including standard original keirin versus international fixed-pacer formats such as Girls KEIRIN / KEIRIN ADVANCE?
6. Are pre-race odds snapshots available with timestamps for all official ticket markets, and can historical snapshots be obtained under the same semantics?
7. What are the permitted uses concerning local storage, statistical analysis, machine-learning model training/evaluation, publication of aggregate findings, and future operational decision support?
8. Are there rate limits, retention rules, redistribution restrictions, or attribution requirements?
9. Is there a test/sandbox or schema specification that can be reviewed before contracting?
10. Which contact/department is the correct one for data licensing if this inquiry has reached the wrong department?

## Core questions for Team-Nave / authorized third-party route

1. Do you provide, or can you provide under a business/custom contract, a keirin database/data-feed API distinct from the CTC betting API?
2. Can it provide historical and live/pre-race structured race-card data?
3. Does it include line/並び grouping and within-line order, and is the observation/publish timestamp available?
4. Does it include S/B/H, 逃/捲/差/マ, rider class/style/score and race/venue context?
5. Does it identify race regime/rules such as standard line keirin versus international fixed-pacer races?
6. Are timestamped odds histories available for 3連単, 3連複, 2車単, 2車複, ワイド and applicable frame markets?
7. For historical data, are values true point-in-time snapshots rather than present-day recomputed profile values?
8. Do license terms permit automated research, local storage, machine-learning training/evaluation and operational model use?
9. What retention, API-rate, redistribution, publication and commercial-use restrictions apply?
10. Is a schema/sample payload or limited trial dataset available for pre-contract technical verification?

## Required answers before provider admission

The provider is not admitted if any of these remain unresolved:
- exact source identity;
- exact timestamp semantics;
- line semantics;
- race-regime semantics;
- historical point-in-time fidelity;
- actionable odds timing if used;
- storage/training/operational-use rights;
- reproducible machine interface;
- no prohibited bypass requirement.

## Owner approval boundary

No.3 may prepare/refine this inquiry, but MUST NOT:
- send it;
- create an account;
- start a paid trial;
- purchase a license;
- accept terms;
- make an external commitment;

without explicit Owner approval.

END
