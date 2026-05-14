# Big5ペルソナ・チャットボット性格反映テスト 設計計画書

本計画書は、異なるLLMモデル・異なる言語条件下で、Big5ペルソナ設定がチャットボット応答に正しく反映されているかを検証するためのテスト設計を定める。

---

## 1. テスト目的

Big5チャットボットは各特性が7段階（-3〜+3）で設定可能であり、5次元すべてを列挙すると7^5 = 16,807通りの組み合わせとなりテストケースが爆発する。本計画書では、**心理学的に意義のある典型8型**を代表ペルソナとして固定し、それらを **3モデル × 3言語** の条件下でテストすることで、現実的なコストで性格反映の妥当性を評価する。

主な検証問い:

1. 各LLMは意図されたBig5プロファイルを再現できるか（個別ラン単位の正確性）
2. 言語間でペルソナ再現性に差があるか（日本語・英語・中国語の比較）
3. モデル間でペルソナ追従性に差があるか（OpenAI / Anthropic / Gemini の比較）
4. 言語×モデルの交互作用は存在するか（特定モデルが特定言語で性能を落とすか）

---

## 2. 設計次元（テスト軸）

| 軸 | 値 | 個数 |
|---|---|---|
| 性格パターン | 心理学典型8型 | 8 |
| 言語 | 日本語 (ja) / 英語 (en) / 中国語簡体 (zh) | 3 |
| LLMモデル | OpenAI GPT-4.1 / Anthropic Claude Sonnet 4.5 / Gemini 2.5 Pro | 3 |
| **総セル数** | | **8 × 3 × 3 = 72ラン** |

本テストでは BFI-44 自己報告を主要評価指標とし、副次的に Cohen's d による特性別効果量を算出する。

---

## 3. 心理学典型8型ペルソナ

8型はBig5の各次元に対し High / Low の両群が複数ペルソナに分散して出現するよう設計する。これにより、特性別 Cohen's d（高群 vs 低群）の算出に十分な統計力を確保する。

| profile_id | 名称 | O | C | E | A | N | 心理学的意図 |
|---|---|---|---|---|---|---|---|
| BALANCED_HIGH | 理想バランス型 | +3 | +3 | +3 | +3 | -3 | 全特性高機能、N低（理想的健全型） |
| BALANCED_LOW | 平坦無関心型 | -3 | -3 | -3 | -3 | +3 | 全特性低、典型的低機能対比 |
| EXTRAVERT_LEADER | 外向リーダー型 | +2 | +2 | +3 | +1 | -2 | E突出、社交的指導者 |
| INTROVERT_THINKER | 内向思索家型 | +3 | +2 | -3 | +1 | 0 | E低O高、内省的知識人 |
| NEUROTIC_ARTIST | 神経質芸術家型 | +3 | -2 | +1 | +1 | +3 | O高N高、創造的不安定 |
| STABLE_OPTIMIST | 安定楽観型 | +1 | +2 | +2 | +3 | -3 | A高N低、情緒安定 |
| CONSCIENTIOUS_MANAGER | 几帳面管理者型 | -1 | +3 | -1 | +2 | -1 | C突出、秩序型 |
| HOSTILE_REBEL | 敵対反逆者型 | +2 | -3 | +2 | -3 | +2 | A低C低、挑戦的 |

### 3.1 設計根拠

- **2型のアンカー**: BALANCED_HIGH と BALANCED_LOW は全特性極端化で識別感度を最大化する基準点
- **特性突出型6個**: 各Big5次元が突出するペルソナを最低1つ用意し、特性別検証を可能にする
- **混合プロファイル**: NEUROTIC_ARTIST や HOSTILE_REBEL のように、複数次元が独立に動くケースで弁別妥当性を検証

### 3.2 高群・低群の内訳（Cohen's d 算出用）

| 次元 | High群（値 > 0） | Low群（値 < 0） |
|---|---|---|
| O | 6型 | 1型 (CONSCIENTIOUS_MANAGER) |
| C | 5型 | 2型 (NEUROTIC_ARTIST, HOSTILE_REBEL) |
| E | 4型 | 2型 (INTROVERT_THINKER, CONSCIENTIOUS_MANAGER) |
| A | 6型 | 1型 (HOSTILE_REBEL) |
| N | 3型 | 4型 |

注: OとAは低群が1型のみとなり Cohen's d 算出の最小要件 (n>=2) を満たさないリスクがあるため、本計画書ではOとAの低群効果量は「参考値」として扱い、十分なn確保が必要な場合は将来的に CONSCIENTIOUS_MANAGER のO値や HOSTILE_REBEL のA値を更に低くした「拡張版」を別途用意する。

---

## 4. 多言語BFI-44アイテム

### 4.1 ベースデータ

既存 `src/big5chat/evaluation/items/bfi.json` （John & Srivastava 1999 のBFI-44英語版）をもとに、以下を新規作成する:

- `src/big5chat/evaluation/items/bfi_en.json` （44項目、英語、既存項目を統一スキーマへ整形）
- `src/big5chat/evaluation/items/bfi_ja.json` （44項目、日本語訳）
- `src/big5chat/evaluation/items/bfi_zh.json` （44項目、中国語簡体訳）

### 4.2 統一スキーマ

既存の `bfi.py` の `_load_items()` および `bfi2_ja.json` 等と互換性のあるスキーマに統一する:

```json
{
  "_description": "BFI-44 (John & Srivastava 1999) for cross-lingual chatbot persona evaluation. Non-English translations are content-equivalent placeholders, not psychometrically validated.",
  "language": "ja",
  "version": "bfi44-v1",
  "items": [
    {"id": "E01", "text": "話好きである", "dim": "E", "reversed": false}
  ]
}
```

### 4.3 翻訳ポリシー

- 日本語訳: 和田 (1996) BFS / Yoshino (2022) BFI-2-J に存在する語彙と一致させるよう努めるが、本研究目的の試験用版 (placeholder) としてヘッダに明示
- 中国語訳: 内容等価性を担保した簡体字訳。Wang ら (2011) Chinese Big Five Inventory を参照したいが、本計画書では同様に試験用版として扱う
- 逆転項目フラグ (`reversed`) は元の `bfi.json` の `metadata.reverse` を継承

### 4.4 既存BFI-44 44項目の次元別分布

| 次元 | 項目数 | 内訳 (順転/逆転) |
|---|---|---|
| Extraversion (E) | 8 | 5 / 3 |
| Agreeableness (A) | 9 | 5 / 4 |
| Conscientiousness (C) | 9 | 5 / 4 |
| Neuroticism (N) | 8 | 4 / 4 |
| Openness (O) | 10 | 8 / 2 |
| **合計** | **44** | **27 / 17** |

---

## 5. 新規作成・修正ファイル

### 5.1 新規

| パス | 役割 |
|---|---|
| `src/big5chat/evaluation/items/bfi_en.json` | BFI-44 英語版（既存bfi.jsonを統一スキーマ化） |
| `src/big5chat/evaluation/items/bfi_ja.json` | BFI-44 日本語版（44項目訳） |
| `src/big5chat/evaluation/items/bfi_zh.json` | BFI-44 中国語簡体版（44項目訳） |
| `configs/personas/psychology_8types.yaml` | 8型ペルソナ定義（言語別生成元） |
| `scripts/run_8types_matrix.py` | 72ラン実行スクリプト |
| `src/big5chat/analysis/report_writer.py` | Markdown表 + CSV出力モジュール |

### 5.2 修正

| パス | 修正内容 |
|---|---|
| `src/big5chat/evaluation/bfi.py` | `_load_items()` に `items_filename` パラメータを追加し、`bfi2_{lang}.json` 既定の挙動を保ったまま、`bfi_{lang}.json` も読み込み可能にする |
| `src/big5chat/experiments/config.py` | `ExperimentConfig` にオプションフィールド `bfi_items_filename` を追加し、YAMLから切り替え可能にする |

既存挙動は変更せず、後方互換を保持する。

---

## 6. 実行フロー

```
[1] 8型ペルソナ定義の読み込み (configs/personas/psychology_8types.yaml)
[2] 言語ごとに PersonaConfig 生成: 8型 × 3言語 = 24 PersonaConfig
[3] 3モデルでループ:
      for model in [openai:gpt-4.1, anthropic:claude-sonnet-4-5, gemini:gemini-2.5-pro]:
          for lang_personas in grouped_by_language:
              config = ExperimentConfig(primary_model=model, personas=lang_personas,
                                        bfi_items_filename="bfi_{lang}.json")
              run_experiment(config)
[4] 各 (persona, language, model) の dim_scores を 72行に集約
[5] report_writer による集計表生成 (Markdown + CSV)
```

### 6.1 API呼び出し見積

| 単位 | 計算 | 呼び出し数 |
|---|---|---|
| 1ペルソナのBFI評価 | 44 items × 2 postamble × 3 variant | 264 |
| 1モデル × 1言語 × 8ペルソナ | 264 × 8 | 2,112 |
| 1モデル × 3言語 × 8ペルソナ | 2,112 × 3 | 6,336 |
| **3モデル × 全体** | 6,336 × 3 | **19,008** |

### 6.2 想定費用

GPT-4.1 換算で平均 入力 400tok / 出力 4tok と仮定:

- 入力: 19,008 × 400 × ($2.00/M) ≈ $15.2
- 出力: 19,008 × 4 × ($8.00/M) ≈ $0.6
- 1モデル小計 ≈ $16
- 3モデル合計 ≈ **$50〜$100**（Anthropic / Gemini の単価差を考慮）

---

## 7. 結果テーブル設計

### 7.1 Table A: 実測Big5スコア表（72行、1-5スケール）

| persona_id | language | model | O | C | E | A | N |
|---|---|---|---|---|---|---|---|
| BALANCED_HIGH | ja | openai:gpt-4.1 | 4.8 | 4.7 | 4.6 | 4.5 | 1.5 |
| BALANCED_HIGH | en | openai:gpt-4.1 | ... | ... | ... | ... | ... |
| ... | ... | ... | ... | ... | ... | ... | ... |

各セルは BFI-44 の該当次元項目（逆転処理済み）の平均スコア。

### 7.2 Table B: 期待値からの偏差表

| persona_id | language | model | O偏差 | C偏差 | E偏差 | A偏差 | N偏差 | MAE |

期待値は big5_values (-3〜+3) を 1〜5 スケールに線形変換: `expected = 3 + value * (2/3)`

具体例:
- big5_value = +3 → expected = 5.0
- big5_value = 0 → expected = 3.0
- big5_value = -3 → expected = 1.0

MAE (Mean Absolute Error) = 5次元の |偏差| の平均。

### 7.3 Table C: モデル × 言語別 Cohen's d（5次元）

| model | language | d_O | d_C | d_E | d_A | d_N | d_平均 |
|---|---|---|---|---|---|---|---|
| openai:gpt-4.1 | ja | ... | ... | ... | ... | ... | ... |
| openai:gpt-4.1 | en | ... | ... | ... | ... | ... | ... |
| openai:gpt-4.1 | zh | ... | ... | ... | ... | ... | ... |
| anthropic:... | ja | ... | ... | ... | ... | ... | ... |
| ... | ... | ... | ... | ... | ... | ... | ... |

9行（3モデル × 3言語）。Cohen's d は各セル内で 8ペルソナを High/Low 群に分け算出。

### 7.4 Table D: ペルソナ別再現度ランキング

各ペルソナについて 9セル (3言語 × 3モデル) を MAE 昇順で並べ、最良条件を特定。

| persona_id | best_model | best_language | best_MAE | worst_MAE | range |
|---|---|---|---|---|---|

### 7.5 出力ファイル配置

```
results/8types_matrix/
  report.md            人間可読、Table A〜D を含む統合レポート
  scores_long.csv      long-format (1行 = 1次元 1ラン、計72×5=360行)
  scores_wide.csv      wide-format (1行 = 1ラン、計72行)
  effect_sizes.csv     Table C 相当のCohen's d 一覧
  raw_responses.jsonl  全API応答ログ（再現用）
```

---

## 8. 評価指標の詳細定義

### 8.1 主要指標

1. **絶対偏差 MAE**: `mean(|measured_i - expected_i|)` for i in {O,C,E,A,N}
2. **方向一致率**: 期待値の符号（>3.0 or <3.0）と実測値の符号の一致率
3. **Cohen's d**: `(M_high - M_low) / s_pooled` を各次元で算出
4. **特性間順位相関**: 期待5値の順位 vs 実測5値の順位 Spearman ρ

### 8.2 合否判定の閾値（参考）

ConstructionPlan §A.2 に準拠:

| 指標 | 閾値 | 解釈 |
|---|---|---|
| Cohen's d | >= 1.0（理想 >= 2.0） | 性格誘発が成功 |
| MAE | <= 1.0（1-5 スケール） | 期待値±1点以内に収まる |
| 方向一致率 | >= 80% | 大半の特性で意図方向と一致 |
| Spearman ρ | >= 0.7 | 特性間の相対順位が保たれている |

---

## 9. 段階実装プラン

| Phase | 内容 | 想定工数 |
|---|---|---|
| A1 | BFI-44 多言語JSON 3ファイル作成（en整形、ja翻訳、zh翻訳） | 中 |
| A2 | 8型ペルソナYAML作成 | 小 |
| A3 | `bfi.py` の `_load_items` にファイル名パラメータ追加 | 小 |
| A4 | `ExperimentConfig` にBFIアイテムファイル名フィールド追加 | 小 |
| A5 | `scripts/run_8types_matrix.py` 作成 | 中 |
| A6 | `report_writer.py` 作成（Markdown + CSV 出力） | 中 |
| A7 | 1ペルソナ × 1言語 × 1モデルでのスモークテスト | 小 |
| A8 | 全72ランのフル実行（API費用発生、ユーザー実行） | 大 |
| A9 | 結果集計・レポート生成、考察 | 中 |

A7 完了時点で一旦ユーザー確認を取り、A8 のフル実行に進む。

---

## 10. リスクと対策

| リスク | 影響 | 対策 |
|---|---|---|
| BFI日中翻訳の妥当性不足 | 言語比較の信頼性低下 | ヘッダで placeholder 明示、将来的に妥当化版へ置換可能なスキーマ設計 |
| API費用が想定超過 | 予算逼迫 | A7 スモーク後に費用再見積、必要に応じ n_reps=1 / max_concurrency 調整 |
| Anthropic seed 非対応 | 再現性低下 | temperature=0.0 と n_reps を増やして近似、ConstructionPlan §J.1 と同方針 |
| Gemini の trait stability 低下 | Neuroticism等の誘発困難 | 結果として記録、考察に「モデル特性の差」として記述 |
| 中国語BFI項目のLLM応答品質 | パース失敗 | スモーク時に zh ラン応答を目視確認、必要に応じプロンプト調整 |
| Cohen's d 算出時 n 不足（OとA） | 効果量推定不安定 | 注記付きで参考値出力、または将来的にペルソナ拡張 |

---

## 11. 留意事項

- BFI翻訳は研究妥当化版ではなく、内容等価性に基づく試験用版。論文化時は和田 1996 / Yoshino 2022 / Wang 2011 等への置換を推奨
- 既存の `bfi2_{lang}.json` は本テストでは利用せず、`bfi_{lang}.json` を新規導入。既存テストやスクリプトは無影響
- `git commit` はユーザーの明示依頼があるまで行わない（CLAUDE.md 準拠）
- ファイル出力では絵文字を使用しない（CLAUDE.md 準拠）
- A8 のフル実行には OpenAI / Anthropic / Gemini の API キーが `.env` に設定されている必要がある

---

## 12. 完了条件

1. `results/8types_matrix/report.md` に Table A〜D が出力されている
2. `scores_long.csv`, `scores_wide.csv`, `effect_sizes.csv`, `raw_responses.jsonl` が生成されている
3. 主要指標（MAE, Cohen's d, 方向一致率）がモデル × 言語 9条件すべてで算出されている
4. 1モデル × 1言語のスモークが成功し、A8 で全72ランが完走している

以上。
