# KEIRIN_RULE_REGISTRY v1

Purpose: chat handoffで消失させてはいけない競輪研究の固定運用ルール。
Rule changes must be explicit/versioned. Chat summaries cannot silently override this registry.
Runtime OFF / automatic betting OFF.

## KR-001 Offline odds independence
オフラインの予測・シミュレーションでは、リアルタイムオッズを必須入力にしない。特定のオッズ研究を行う場合のみ別途入力する。

## KR-002 Odds at purchase boundary
オッズは主として実運用の購入判定境界で使う。研究段階で取得困難なリアルタイムオッズのためにシミュレーション進行を止めない。必要オッズ閾値を提示し、実運用時にOwnerが確認できる設計を許容する。

## KR-003 Forward-style hidden outcome
過去レースを前向き検証に使う場合、予測を固定するまで結果を見ない／結果データを分離する。予測固定後に答え合わせする。

## KR-004 Historical data first
実用精度向上のため、取得可能な過去レース情報を積極的に母数拡大へ使う。未来開催情報だけに依存しない。

## KR-005 Official-source evidence
公式サイトの過去レース・開催・結果情報は、競輪研究プロトコル上の主要なsource evidenceとして利用可能。必要に応じ複数情報源で補強する。

## KR-006 Explore race structure
決勝、単騎、ガールズ等のレース構造差は仮説として分離評価し、印象だけで固定ルール化しない。十分な母数で検証する。

## KR-007 Betting method is part of research
予測順位だけでなく、買い方、点数、資金配分、購入見送り条件、必要オッズ/期待値境界も別レイヤーとして検証する。

## KR-008 No automatic betting
Automatic betting OFF. Owner spend/live purchase/effect requires separate authority.

## KR-009 Compact chat output
通常の競輪実行報告は短くする。大量表、長いログ、全履歴、巨大ロードマップは原則repository/file artifactへ保存する。

## KR-010 Continuous owner-free progress
Owner操作が不要なデータ整理・シミュレーション・分析・仮説検証・checkpointは、会話上の追加承認待ちで止めない。

## KR-011 Progress reporting
ユーザー向け報告では、現在地、新発見、次の作業、進行度を分かりやすい日本語で示す。専門用語/英語は必要最小限にする。

## KR-012 Fresh-state rule
CURRENT/NOW/LATESTを古いhandoffやchat履歴だけから決めない。再開時はcanonical GitHubとactive Keirin artifactsをFresh Readする。

## KR-013 Exact circumference preservation
公式に観測された走路長は正確な値のまま別レーンで保存・研究する。333.3m、335m、400m、500mその他の公式長を近い長さへ丸めない。unsupported-length dropも禁止。

## KR-014 Frozen B1a no-retune binding
Confirmatory / prospective評価では凍結B1aを再学習・再重み付け・閾値調整しない。Current binding: `B1a_RECONSTITUTED_v1`, predictor blob `62ae4ebc17cda47dca1fffae190fa44caae58ca3`, temperature `1.15`.

## KR-015 Evidence-class separation
Prospective / preregistered-retrospective / ordinary retrospective を明示的に分離する。結果を見た後で、より強いevidence classへ格上げしない。

## KR-016 Missing PRE fail-closed
必須PRE項目が欠ける場合は推測・合成しない。結果参照前にfail-closedまたは除外し、理由を記録する。

## KR-017 No post-outcome cherry-picking
Full-day等を事前登録した場合、正常に凍結できた対象は結果後に都合よく削除しない。失格・落車等も事前ルールに従って保持する。

## KR-018 Scientific-progress discipline
科学検証進行度は、ファイル数や単純なレース件数増加だけでは上げない。独立追試・前向き証拠・漏洩耐性など、証拠強度が実質的に進んだ時だけ変更する。

## KR-019 Circumference challenger support boundary
現在凍結されているcircumference challengerは exact 333.3m/400m のみ対応。335m/500mへ流用・丸め適用しない。335m/500mは当面B1a-onlyで評価し、十分な同長証拠から別途検証されたchallengerを作る。

## KR-020 Canonical continuity store
GitHub repositoryが継続状態の正本。Chatは短命な実行端末として扱う。CURRENT_STATE / RULE_REGISTRY / EXPERIMENT_LEDGER / datasets-artifactsをFresh Readすれば巨大handoffなしで再開できる状態を維持する。

Detailed machine-readable registry on the active Keirin branch:
`v3/historical_all_market/continuity/KEIRIN_RULE_REGISTRY_v1.json`
