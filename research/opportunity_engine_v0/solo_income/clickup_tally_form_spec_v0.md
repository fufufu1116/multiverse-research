# ClickUp external falsification — anonymous Tally form spec v0

Status: INTERNAL / NOT CREATED EXTERNALLY / NO DATA COLLECTION / RUNTIME OFF
Prepared: 2026-09-14
Parent gate: #465

## Purpose
Exact no-PII form payload so, if #465 is authorized, form creation does not require improvisation or widening scope.

## Form title
`ClickUp AI料金・プラン表示の匿名チェック`

## Intro copy
`ClickUpでは、公開されているAI料金と、WorkspaceのPlans / Billing画面に表示される料金体系が異なる場合があります。この匿名調査では、どの表示が出ているかだけを確認します。名前・メール・Workspace名・スクリーンショット・請求情報は送らないでください。研究用で、ClickUp公式サポートや請求保証ではありません。`

## Question 1 — required single choice
Label:
`現在のWorkspaceに一番近いものは？`

Options / stored values:
- `Free Forever` -> `FREE`
- `以前から使っている有料Workspace` -> `EXISTING_PAID`
- `最近作成したWorkspace` -> `RECENTLY_CREATED`
- `わからない` -> `UNKNOWN`

## Question 2 — required single choice
Label:
`Plans / Billing / Upgrade画面では、どの表示が見えますか？`

Options / stored values:
- `Brain AI / Everything AIなどを別アドオンとして追加する表示` -> `CLASSIC_ADDON`
- `Core / Business / Business Plus / Enterprise / Maxなど、AI込みの新しいプラン表示` -> `NEW_INCLUDED_AI`
- `両方の表示が見える` -> `BOTH`
- `まだ確認していない / わからない` -> `UNKNOWN`

Help text:
`Workspace名やスクリーンショットは送らないでください。`

## Question 3 — required single choice
Label:
`そのWorkspace専用の実際の価格は画面で確認できましたか？`

Options / stored values:
- `はい` -> `YES`
- `いいえ / わからない` -> `NO`

## Question 4 — optional single choice
Label:
`請求周期は？`

Options / stored values:
- `月払い` -> `MONTHLY`
- `年払い / 年払い換算` -> `YEARLY`
- `わからない` -> `UNKNOWN`

## Result-support question 5 — required single choice
Label:
`この確認は、実際に迷っていたClickUpの料金・AIプラン判断に役立ちましたか？`

Options / stored values:
- `はい。実際の判断で迷っていた` -> `YES_REAL_DECISION_CONFUSION`
- `いいえ。一般的な興味で見ただけ` -> `NO_GENERAL_CURIOSITY`
- `いいえ。役に立たなかった` -> `NO_NOT_HELPFUL`
- `まだわからない` -> `UNSURE`

## Result-support question 6 — required single choice
Label:
`ClickUp公式の現在の画面だけで、同じ判断は迷わずできましたか？`

Options / stored values:
- `はい。公式画面だけで十分だった` -> `YES_OFFICIAL_UI_SUFFICIENT`
- `いいえ。このチェックで整理できた` -> `NO_CHECKER_ADDED_VALUE`
- `わからない` -> `UNSURE`

## Hidden fields
- `source`
- `variant`
- `test_id`

Frozen values for first test:
- `test_id=clickup_plan_generation_v1`
- `variant=A`
- `source` set by distribution URL; examples only after approval: `organic_search`, `instagram_org_1`, `instagram_org_2`, `instagram_org_3`.

## Explicitly prohibited form elements
Do not add:
- name/email/phone;
- free-text;
- file/image upload;
- Workspace/company/customer name or ID;
- login credentials;
- billing document;
- exact invoice/contract amount;
- payment/card data;
- consent to marketing;
- newsletter opt-in.

## Internal classification mapping
Using Q1/Q2/Q3:

- Q2 `NEW_INCLUDED_AI` + Q3 YES -> `NEW_INCLUDED_AI_PLAN_PRICE_OBSERVED`
- Q2 `NEW_INCLUDED_AI` + Q3 NO -> `NEW_INCLUDED_AI_PLAN_CONFIRMED_PRICE_UNKNOWN`
- Q2 `CLASSIC_ADDON` + Q3 YES -> `CLASSIC_ADDON_MODEL_PRICE_OBSERVED`
- Q2 `CLASSIC_ADDON` + Q3 NO -> `CLASSIC_ADDON_MODEL_CONFIRMED_PRICE_UNKNOWN`
- Q2 `BOTH` -> `CONFLICTING_SURFACES_HUMAN_REVIEW`
- Q2 UNKNOWN + Q1 FREE or RECENTLY_CREATED -> `NEW_PLAN_SET_EXPECTED_SURFACE_NOT_CONFIRMED`
- Q2 UNKNOWN + Q1 EXISTING_PAID -> `UPGRADE_SURFACE_UNKNOWN`
- otherwise -> `INSUFFICIENT_EVIDENCE`

Do not expose this mapping as a billing guarantee.

## Completion copy
`回答ありがとうございました。公開されているClickUpの価格は参考情報ですが、実際のWorkspaceで見えるPlans / Billing / Upgrade画面が購入判断には重要です。表示が矛盾する場合や契約価格が不明な場合は、公開価格をそのまま請求額として扱わず、Workspace内の表示またはClickUp公式サポートで確認してください。`

## Analytics to read after approval
- visits / views;
- starts;
- completions;
- source/variant;
- response distribution for Q1–Q6.

No submission may be interpreted as WTP or revenue intent.

`FORM_SPEC=FROZEN_INTERNAL`
`EXTERNAL_FORM=NOT_CREATED`
`PII=OFF`
`FREE_TEXT=OFF`
`MONETIZATION=OFF`
`OWNER_GATE=#465`
`RUNTIME=OFF`
