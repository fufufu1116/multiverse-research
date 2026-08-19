# START HERE — Multiverse 競輪ver

このファイルは新チャット用の固定入口です。

## まず読む

1. `KEIRIN_NOW.md` — 主向けの簡単な現在地
2. `v3/historical_all_market/governance/CURRENT_STATE_KEIRIN.json` — 正確な機械用Current State
3. `v3/historical_all_market/governance/HANDOFF_BOOTSTRAP_PROTOCOL_v1.md` — 復旧手順
4. `v3/historical_all_market/governance/ARTIFACT_POINTER_REGISTRY_KEIRIN_v1.json` — Artifact場所

Repository: `fufufu1116/multiverse-research`

## 新チャットでNo.3がやること

主に過去説明をやり直させない。

GitHub → 必要なDrive実物 → SHA/保護状態を自動回収し、重要物を:

- RECOVERED
- UNPROVEN
- MISSING
- SEALED
- NEXT_GATE

に分類して続行する。

記憶にあるSHAやパスだけで「確認済み」扱いしない。

## 主への報告

原則、次の4点だけを平易な日本語で伝える。

- いま何をしてる
- 何が分かった
- 次に何をする
- 主がやること

専門用語は必要最小限。使う場合はすぐ日本語訳を付ける。

## 現在の固定境界

正本はCURRENT_STATE。少なくとも現在:

- 親lineageは `NO_B_VALIDATED_CONFIGURATION`
- current DEV2000 Cを新lineage救済には使わない
- `ECON_HOLDOUT1000 = SEALED`
- 現実のお金は使わず、経済指標は仮想資金のみ
- 外部業者への連絡はしない
- Synthetic世界/オッズは開発・ストレス試験用であり、現実で勝てる証拠にはしない

## 現在の研究方向

現実の競輪を最終目標にしつつ、まず複数の仮想競輪世界（Digital Twin）で旧モデルと新モデルを壊し、必要なレース情報・ライン構造・予測方法・仮想資金配分を高速に固める。

その後、現実のPREデータで段階的に検証する。

## 最小起動文

`Multiverse競輪ver 引き継ぎ起動。実物優先で自動回収し、CURRENT_STATEから続行。`

明確な「続きから」でも可。
