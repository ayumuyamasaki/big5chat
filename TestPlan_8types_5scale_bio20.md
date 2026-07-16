# Big5チャットボット性格反映テスト 改修計画書（5段階スケール化 + bio_id 20人平均）

本計画書は、既存の `TestPlan_8types_matrix.md` / `configs/personas/psychology_8types.yaml` を対象に、以下2つの変更を行うための設計・実装計画を定める。

1. **性格特性の入力値スケールを、BFIテスト結果と完全に同じ `1〜5` の5段階に統一する**（現状: 入力は-4〜+4の9段階、BFI出力は1〜5の5段階で不整合）
2. **心理学典型8型それぞれについて、bio_id（経歴設定）を1人分ではなく20人分実行し、その平均をそのペルソナ型のBFIテスト結果として扱う**

ユーザーとの事前確認により、以下の方針で進める。

- 入力スケール: `1〜5` の5段階（BFIの1-5スケールと完全一致。`expected = big5_value` そのまま、変換不要）
- 8型ペルソナの再設計: 心理学的意図を保ちつつ手動で再設計
- bio20実験のスコープ: まず1モデル（openai:gpt-4.1）× 1言語（ja）で実施
- 集計方針: 20人分のBFIスコアの平均値のみを、そのペルソナ型の代表スコアとする

---

## 1. 現状整理

| 項目 | 現状 | ファイル |
|---|---|---|
| 性格特性の入力値域 | `-4〜+4`（9段階） | `src/big5chat/persona/spec.py` の `Big5Values` |
| BFIテスト結果のスケール | `1〜5`（5段階） | `src/big5chat/evaluation/bfi.py` の `_normalize_to_5` |
| 8型ペルソナの入力値 | `-3〜+3`（7段階）を使用、`expected = 3 + value*(2/3)` で1-5に線形変換 | `configs/personas/psychology_8types.yaml`, `src/big5chat/analysis/report_writer.py` |
| bio_id（経歴） | 各8型に1個（0〜7）のみ割当。言語ごとに20個の経歴プールが存在するが未活用 | `configs/personas/psychology_8types.yaml`, `src/big5chat/persona/biographies.py` |

---

## 2. 変更A: 性格特性入力値を1〜5スケールに変更

### 2.1 スケール設計

- `Big5Values` の各次元の値域を `-4〜+4` → `1〜5` に変更する。**中央値（ニュートラル）は3**。
- 期待値変換は不要になる。`expected = big5_value` で1-5スケールのまま直接BFI測定値と比較できる（現行の `expected = 3 + value*(2/3)` という変換式そのものが不要になり、計画がシンプルになる）。
- 一方、既存コードには「符号（正/負）」で高群・低群やスタイル分岐を判定している箇所が複数あり、`1〜5`スケール（常に正の値）ではそのままでは動かない。

**方針（当初のオフセット変換案から変更）**: 単純な高低の閾値判定（真偽値のみを使う箇所）は、オフセット変数を作らず**閾値の定数を+3した直接比較**に書き換える（例: `value > 0` → `value > 3`、`E <= -2` → `E <= 1`）。これは数学的に完全に等価であり、コード変更箇所を減らせる。

`likert.py` の強調表現選択も、算術演算（引き算）を使わずに済ませられる。現状の `LIKERT_*_POSITIVE` 辞書はキー`1〜4`（オフセット的な強度）だが、実は `LIKERT_*_NEGATIVE` 辞書（`-1〜-4`をキーとする）は定義されているだけで現在のコードでは未使用（`likert_phrase_ja`等は全て`POSITIVE`辞書に`abs(value)`でアクセスしている）。この未使用の`NEGATIVE`辞書を「低群側の生値`{1,2}`をキーとする辞書」として再定義し、`POSITIVE`辞書を「高群側の生値`{4,5}`をキーとする辞書」として再定義すれば、`likert_phrase_*`関数は `value > 3` なら`POSITIVE[value]`、`value < 3` なら`NEGATIVE[value]`を直接引くだけで完結し、引き算そのものが不要になる。呼び出し元（`assembler.py`）は一切変更しない。

### 2.2 修正が必要なファイル

| ファイル | 修正内容 |
|---|---|
| `src/big5chat/persona/spec.py` | `Big5Values` の `O/C/E/A/N` を `Field(ge=1, le=5)` に変更。デフォルト値がある場合は3に見直す |
| `src/big5chat/persona/spec.py` | `_default_style_ja` / `_default_style_zh` 内の閾値定数をそれぞれ+3した直接比較に書き換える（`E>=2`→`E>=5`、`A<=0`→`A<=3`、`A<=-2`→`A<=1`、`E<=-2`→`E<=1`）。オフセット変数は作らない。`E>=3`系の分岐は新レンジで到達不能（最大5、+3後は`E>=6`相当）になるので統合・削除する |
| `src/big5chat/persona/likert.py` | `LIKERT_*_POSITIVE` 辞書を高群側の生値`{4,5}`をキーとする形に再定義（例: `{5: "非常に", 4: "少し"}`）。現状未使用の `LIKERT_*_NEGATIVE` 辞書を低群側の生値`{1,2}`をキーとする形に再定義（例: `{1: "全く", 2: "あまり"}`）。`likert_phrase_en/ja/zh` と `*_intensifier` 関数群は、`value > 3` なら `POSITIVE[value]`、`value < 3` なら `NEGATIVE[value]` を直接引くだけに書き換える（`-value`等の算術演算は不要になる） |
| `src/big5chat/prompts/assembler.py` | **変更不要**。`likert_phrase_*` に生の1-5値をそのまま渡し続ければよい（変換ロジックが`likert.py`内部に移ったため） |
| `src/big5chat/safety/constraints.py` | `big5.N >= 2`（62行目）→ `big5.N >= 5`、`big5.A <= -2`（69行目）→ `big5.A <= 1` に閾値の定数を直接書き換える |
| `src/big5chat/experiments/protocol.py` | `_compute_effect_sizes` 内の高群/低群判定 `val > 0` / `val < 0` を `val > 3` / `val < 3`（中央値3を除外して高群・低群に分岐）に変更 |
| `src/big5chat/analysis/report_writer.py` | `expected_score_1to5()` の中身を `return float(big5_value)` に簡素化（変換不要になったため）。`compute_effect_sizes()` 内の `r["big5_expected"][d] > 0` / `< 0` も `> 3` / `< 3` に変更 |
| `src/big5chat/experiments/config.py` | `generate_32_profiles()` の値生成式を `dim: bit * amplitude` → `dim: 3 + bit * amplitude` に変更し、`amplitude` デフォルトを `3` → `2` に変更（3+2=5, 3-2=1で新レンジに収まる） |

### 2.3 心理学典型8型ペルソナの再設計（たたき台）

現行の`-3〜+3`の値を、各型の「どの特性が突出しているか」という心理学的意図を保ったまま`1〜5`（中央値3）に手動で再マップする。以下は実装時の初期案（ユーザー確認の上で最終化する）。

| profile_id | O | C | E | A | N | 意図（変更なし） |
|---|---|---|---|---|---|---|
| BALANCED_HIGH | 5 | 5 | 5 | 5 | 1 | 全特性高機能、N低（健全型アンカー） |
| BALANCED_LOW | 1 | 1 | 1 | 1 | 5 | 全特性低（低機能アンカー） |
| EXTRAVERT_LEADER | 4 | 4 | 5 | 4 | 2 | E突出、社交的指導者 |
| INTROVERT_THINKER | 5 | 4 | 1 | 4 | 3 | E低O高、内省的知識人 |
| NEUROTIC_ARTIST | 5 | 2 | 4 | 4 | 5 | O高N高、創造的不安定 |
| STABLE_OPTIMIST | 4 | 4 | 4 | 5 | 1 | A高N低、情緒安定 |
| CONSCIENTIOUS_MANAGER | 3 | 5 | 2 | 4 | 2 | C突出、秩序型 |
| HOSTILE_REBEL | 4 | 1 | 4 | 1 | 4 | A低C低、挑戦的 |

**高群/低群バランスの確認**（Cohen's d算出用、中央値3を基準に `>3`=高群 / `<3`=低群、n>=2が望ましい）:

| 次元 | High群(n) | Low群(n) | 現行(7段階)比 |
|---|---|---|---|
| O | 6 | 1 | 同一（既知の課題として継続、参考値扱い） |
| C | 5 | 3 | 改善（現行2→3） |
| E | 5 | 3 | ほぼ同等（現行4→5, 2→3） |
| A | 6 | 2 | 改善（現行1→2、Cohen's d算出の最小要件n>=2を満たす） |
| N | 3 | 4 | 同一 |

O低群のみ引き続きn=1のため参考値扱いとする点は現行のTestPlan_8types_matrix.mdの注記を踏襲する。

### 2.4 影響を受ける既存configとテスト

現行の値域外（1未満または5超）の値を使っている箇所は、新しい `ge=1, le=5` バリデーションでエラーになるため、以下を合わせて修正する。

| ファイル | 内容 |
|---|---|
| `configs/personas/phase0_pilot_4corners.yaml` | `ALL_HIGH: {O:5,C:5,E:5,A:5,N:5}` / `ALL_LOW: {O:1,C:1,E:1,A:1,N:1}` / `HIGH_E_LOW_N: {O:4,C:3,E:5,A:4,N:1}` / `LOW_E_HIGH_N: {O:2,C:3,E:1,A:2,N:5}` に再設計（意図は維持、値域のみ1-5化） |
| `configs/personas/phase0_pilot_32types.yaml` | `generate_32_profiles()` 経由の生成であれば §2.2 のコード修正のみで自動的に1-5化される。静的に値を記述している場合は同様に `3+bit*amplitude`（amplitude=2）の値に書き換える |
| `tests/test_persona.py` | 境界値テスト（現行 `O=4`が有効/`O=5`が無効、`O=-5`が無効）を `O=5`が有効/`O=6`が無効、`O=0`が無効に変更。他、値域外(3以上のマイナス値等)を使うテストケースも `1〜5` に収まるよう修正 |
| `tests/conftest.py`, `tests/test_baselines.py`, `tests/test_prompts.py`, `tests/test_zh.py`, `tests/test_journal.py` | `Big5Values(...)` の呼び出しをすべて `1〜5`（中央値3）に収まる値に修正。例: `Big5Values(O=2, C=1, E=3, A=2, N=-2)` → `Big5Values(O=4, C=3, E=5, A=4, N=1)`（オフセット+3変換） |

修正後、`pytest tests/` を実行し既存59テスト（+ `big5_persona_chat/tests/` の新規テスト）が全てパスすることを確認する。

---

## 3. 変更B: bio_id 20人分平均実験

### 3.1 実行スコープ

- モデル: `openai:gpt-4.1` のみ
- 言語: `ja` のみ
- ペルソナ: 心理学典型8型（変更A適用後の1-5スケール版）
- bio_id: `biographies.py` の `BIOGRAPHIES_JA`（20件）を全て使用（`biographic_description_id = 0〜19`）

3モデル×3言語のフルマトリクスへの拡張は、本実験で妥当性を確認した後の将来課題としてスコープ外にする。

### 3.2 実行方式

新規スクリプト `scripts/run_8types_bio20.py` を作成する。

```
[1] configs/personas/psychology_8types.yaml（1-5スケール版）を読み込み、8型のPersonaConfigを取得
[2] 各型について bio_id = 0..19 の20通りの PersonaConfig バリアントを生成
    （biographic_description_id のみ書き換え、他フィールドは型ごとの値を継承）
[3] 型 × bio の 8 × 20 = 160 通りについて、BFIEvaluator.evaluate() を実行
    （コスト抑制のため run_expert_rating / run_trait_mcq は無効のまま、BFIのみ実行）
[4] 型ごとに、20bio分の dim_scores を平均し、bio間の標準偏差も併せて記録
[5] 平均値を big5_measured としてTestPlan_8types_matrix.md §7 と同形式の
    Table A〜D 相当のレポートを出力（expected は big5_value をそのまま使用）
```

### 3.3 出力ファイル

`results/8types_bio20_ja_gpt4-1/` に以下を出力する（既存 `report_writer.py` の関数を再利用・拡張）。

| ファイル | 内容 |
|---|---|
| `report.md` | Table A〜D相当（1行=1ペルソナ型、measuredは20bio平均） |
| `scores_wide.csv` / `scores_long.csv` | 既存形式を踏襲（1行=1ペルソナ型の平均値） |
| `effect_sizes.csv` | 8型の平均スコアを高群/低群（中央値3基準）に分けたCohen's d |
| `bio_raw.csv`（新規） | 型 × bio_id × 次元 の生スコア一覧（20人分の個別値。将来的な個体差分析・統計的検定の再設計に利用可能） |

### 3.4 想定コスト

BFI-44評価1回（1型×1bio）あたりの呼び出し数は既存と同じ `44項目 × 2 postamble × 3 variant = 264回`。

| 単位 | 計算 | 呼び出し数 |
|---|---|---|
| 1型 × 20bio | 264 × 20 | 5,280 |
| 8型 × 20bio | 5,280 × 8 | 42,240 |

GPT-4.1換算（入力400tok/出力4tok、$2.00/M・$8.00/M想定）:

- 入力: 42,240 × 400 × $2.00/M ≈ $33.8
- 出力: 42,240 × 4 × $8.00/M ≈ $1.4
- **合計 ≈ $35〜$40**

### 3.5 スモークテスト

全160ラン（本番実行）の前に、1型 × bio_id 2件程度でスモークテストを行い、疎通・パース成功率を確認してからユーザー承認を得て本番実行する。

---

## 4. 実装フェーズ

| Phase | 内容 | 備考 |
|---|---|---|
| B1 | `Big5Values` の値域を `1〜5` に変更（spec.py） | |
| B2 | `spec.py` のスタイル閾値を直接+3した比較に書き換え、`likert.py` の `POSITIVE`/`NEGATIVE` 辞書を生値`{4,5}`/`{1,2}`キーに再定義し関数を直接引きに書き換え | `assembler.py`は変更不要 |
| B3 | `safety/constraints.py`（2箇所）の閾値定数を+3した比較に書き換え | |
| B4 | `protocol.py`・`report_writer.py` の高群/低群判定を `>3` / `<3` に、期待値計算を恒等関数に変更 | |
| B5 | `config.py` の `generate_32_profiles` を `3+bit*amplitude` 方式に変更（amplitude既定値2） | |
| B6 | `psychology_8types.yaml` を1-5スケール版に書き換え（本計画書§2.3のたたき台をベースに最終化） | |
| B7 | `phase0_pilot_4corners.yaml` / `phase0_pilot_32types.yaml` を新レンジに調整 | |
| B8 | 既存テスト（境界値テスト含む）を新レンジ・オフセット変換後の期待挙動に合わせて修正 | |
| B9 | `pytest tests/` 実行、全件パス確認 | |
| C1 | `scripts/run_8types_bio20.py` 作成（bio20ループ + 集計ロジック） | |
| C2 | `report_writer.py` にbio平均・bio_raw出力用の拡張関数を追加 | |
| C3 | スモークテスト（1型×2bio、ドライラン→実API） | ユーザー確認後に本番実行へ |
| C4 | 本番実行（8型×20bio、API費用 約$35〜$40発生） | ユーザー実行 |
| C5 | 結果集計・レポート確認 | |

B系（スケール変更）を先に完了させ、既存テストが全てパスした状態でC系（bio20実験）に着手する。

---

## 5. リスク・注意点

| リスク | 影響 | 対策 |
|---|---|---|
| 閾値定数の+3し忘れ | `spec.py`のスタイル判定、`safety/constraints.py`、`effect_size`集計のいずれかで閾値定数を+3し忘れると、符号判定が常にtrue（1-5は常に正）になり、全ペルソナが「高群」扱いになるなど深刻なバグになる。特に`likert.py`は`POSITIVE`/`NEGATIVE`辞書のキーを生値`{4,5}`/`{1,2}`に正しく再定義しないと、存在しないキーでの`KeyError`（例: 旧キー`3,4`のまま残す等）や強度の逆転が起きる | §2.2の修正箇所一覧を実装チェックリストとして使用し、修正後に全ての5次元×境界値（1,3,5）で手動確認する。`assembler.py`は変更不要なので、誤って触らないよう注意する |
| 5段階化により型同士の弁別性が下がる（値の刻みが粗くなる） | Cohen's dが縮小する可能性 | §2.3のたたき台で高群/低群バランスを事前確認済み。実測後、必要なら型定義を再調整 |
| 8型再設計の妥当性 | 意図と異なる型になるリスク | B6着手前にたたき台をユーザーと最終確認してから実装 |
| bio20の平均のみを採用（個体差データを分析に使わない） | 将来Cohen's dをbio単位のnで再計算したい場合、集計方法の再設計が必要 | `bio_raw.csv`に生データを必ず残し、将来の再分析に備える |
| 既存configの値域超過によるバリデーションエラー | `phase0_pilot_*.yaml`実行が壊れる | §2.4のファイル一覧に沿って値を修正してからテスト実行 |
| API費用 | 約$35〜$40（1モデル×1言語のみ） | C3のスモーク完了後、ユーザー承認を得てからC4を実行 |

---

## 6. 完了条件

1. `Big5Values` が `1〜5` の5段階に変更され、`pytest tests/` が全件パスしている
2. `spec.py` / `likert.py` / `safety/constraints.py` / `protocol.py` / `report_writer.py` の閾値・中央値判定がすべて1-5スケールに合わせて修正され、`expected_score_1to5` が恒等関数（`big5_value`をそのまま返す）になっている（`assembler.py`は無変更）
3. `psychology_8types.yaml` が1-5スケール版に更新されている
4. `scripts/run_8types_bio20.py` により、8型 × 20bio（ja, gpt-4.1）のBFI評価が完走している
5. `results/8types_bio20_ja_gpt4-1/` に `report.md`, `scores_wide.csv`, `scores_long.csv`, `effect_sizes.csv`, `bio_raw.csv` が出力されている
6. 各型の代表スコア（20bio平均）と、bio間の標準偏差が記録されている

以上。

---

## 7. 実施記録（2026-07-16 実行分・計画からの変更点）

本計画書のB系・C1・C2までを実装した上で、C3（スモークテスト）・C4（本番実行）を
以下の内容で実施した。計画時点（§3）からの変更点を中心に記録する。

### 7.1 postamble × variant を1×1に削減（§3.4からの変更）

§3.4では「44項目 × 2postamble × 3variant = 264回/組」を前提にコストを試算していたが、
実行段階でユーザーと協議の上、C4本番実行では **1postamble × 1variant（44回/組）** に
削減して実施した。

- 理由: bio_id 20人分の平均によって「経歴設定によるブレ」は吸収できるが、
  postamble/variantが打ち消す「プロンプト言い回し・回答形式によるブレ」は別軸のノイズ源であり、
  bio平均では代替できない。ただし今回はコストを優先し、この軸の頑健性チェックは簡略化する判断とした。
- 実装: `scripts/run_8types_bio20.py` に `--postambles` / `--variants` オプションを追加
  （カンマ区切りでpostamble ID / variantキーを指定可能。デフォルトは従来通り `0,1` / `A,B,C` を維持し、
  他用途での頑健性重視の実行にも対応できるようにした）。
  `src/big5chat/evaluation/bfi.py` の `BFIEvaluator` 自体は変更前から `postambles` / `variants` を
  受け取れる設計だったため、`bfi.py` の変更は不要だった。
- 実行コマンド: `python scripts/run_8types_bio20.py --postambles 0 --variants A`
  （8型×20bio×44回 = 7,040回/言語、約$6弱/言語）

### 7.2 3言語（ja/en/zh）への拡張（§3.1からの変更）

§3.1では「まず1モデル×1言語（ja）で実施」とスコープしていたが、
実行段階でユーザーからen/zhへの拡張依頼があり、3言語すべてで本番実行した。

- 事前確認事項: BFIアイテム（`bfi_en.json` / `bfi_zh.json`）、bio経歴プール
  （`BIOGRAPHIES_EN` / `BIOGRAPHIES_ZH`、各20件）、postamble文言、prompt variant文言、
  安全制約プリアンブルがいずれもen/zh分すでに実装済みであることを確認した上で着手した
  （心理学8型ペルソナ自体は `big5_values` が数値のみでlanguage非依存のため、
  `psychology_8types.yaml` の追加修正やコード変更は不要だった）。
- 実行方式: `scripts/run_8types_bio20.py --language {ja,en,zh}` をそれぞれ個別に実行し、
  出力も `results/8types_bio20_{lang}_openai_gpt-4.1/` に言語ごとに分けた
  （3言語を1つのレポートに統合する対応は今回は行っていない）。
- 3言語合計コスト: 約7,040回×3 ≈ 21,000回、約$18弱。

### 7.3 実施結果サマリ

| 言語 | 全ランMAE平均 | Cohen's d（5次元平均） |
|---|---|---|
| ja | 0.33 | 10.90 |
| en | 0.18 | 12.63 |
| zh | 0.47 | 10.70 |

3言語ともMAE・Cohen's dの目安（MAE<=1.0、d>=2.0）を大きく上回った。
詳細な分析・所見は `Report_8types_bio20_3lang.md` を参照。

### 7.4 完了条件との対応

§6の完了条件4・5は、当初想定の「ja・1言語のみ」から「ja/en/zh・3言語」に
実施範囲を拡大した形で満たされている（bio間標準偏差は各言語の `bio_raw.csv` から算出可能。
CSV出力への標準偏差列の追加は今回のスコープでは対応していない）。
