# big5chat 使い方ガイド

本ガイドは `big5_chatbot_research` プロジェクトを **目的別** にどう使えばよいかを解説する文書です。
「とりあえず chatbot と話してみたい」「性能を定量評価したい」「3手法を比較したい」など、
やりたいことから逆引きできるよう構成しています。

最初に一度だけ読めば良い [セットアップ](#2-セットアップ共通手順) を済ませたあと、
[ユースケース別ガイド](#3-ユースケース別ガイド) から該当する節に飛んでください。

---

## 目次

1. [はじめに](#1-はじめに)
2. [セットアップ (共通手順)](#2-セットアップ共通手順)
3. [ユースケース別ガイド](#3-ユースケース別ガイド)
   - 3.1 [とにかく chatbot と会話してみたい](#31-とにかく-chatbot-と会話してみたい-最短パス)
   - 3.2 [3手法の応答を並べて比較したい](#32-3手法の応答を並べて比較したい)
   - 3.3 [単一ペルソナの誘発精度を数値で評価したい](#33-単一ペルソナの誘発精度を数値で評価したい)
   - 3.4 [3手法の誘発精度を Cohen's d で定量比較したい](#34-3手法の誘発精度を-cohens-d-で定量比較したい)
   - 3.5 [32ペルソナの完全パイロットを実行したい](#35-32ペルソナの完全パイロットを実行したい)
   - 3.6 [独自のペルソナ群を YAML で定義して実験したい](#36-独自のペルソナ群を-yaml-で定義して実験したい)
4. [言語別メモ (ja / en / zh)](#4-言語別メモ-ja--en--zh)
5. [トラブルシューティング](#5-トラブルシューティング)
6. [次のステップ](#6-次のステップ)

---

## 1. はじめに

### 本ツールでできること

- **Big5 (OCEAN) 値を指定して LLM chatbot にそのペルソナを演じさせる** (日本語/英語/中国語)
- 演じられた人格を **3層評価** する: Self-Report BFI / Expert Rating / TRAIT MCQ
- **3手法の比較**: 自作 big5chat (Serapio-García 式) vs MPI (Jiang 2023) vs PersonaLLM (Jiang 2024)
- **効果量 (Cohen's d)** で誘発の強さを定量化
- **JSONL ジャーナル** で全 API 呼び出しを記録し再現性を担保

### 本ツールでできないこと

- **リアルタイム学習・ファインチューニング** は含まない (プロンプトベースの誘発のみ)
- **MPI / PersonaLLM の項目文は英語のみ**。日本語・中国語ペルソナに英語項目を投げる形になる
- **パイロット実行の途中再開** (停止したらフル再実行が必要)
- **心理診断としての利用** (本ツールは研究用途の chatbot 評価フレームワーク)

### 用語集

| 用語 | 意味 |
|---|---|
| **ペルソナ** | Big5 値と伝記的記述の組からなる LLM の人格設定 |
| **Big5 値** | O/C/E/A/N の5次元を各 -4〜+4 の 9 段階で指定 (Serapio-García 2025 式) |
| **BFI** | Big Five Inventory。自己報告型の 20〜44 項目の性格検査 |
| **TRAIT** | シナリオベース MCQ による行動特性の間接測定 |
| **Expert Rating** | LLM 判定者による 14 面接質問の特性評価 |
| **MPI** | Machine Personality Inventory (120項目) |
| **PersonaLLM** | 44項目 BFI + 32 型バイナリペルソナの先行研究 |
| **Cohen's d** | 2 群平均差の効果量。本ツールでは High 群 vs Low 群で算出 |

### Big5 値の符号の意味

| 次元 | 正 (+) が高いとき | 負 (−) が高いとき |
|---|---|---|
| **O** (Openness) | 想像力豊か、好奇心旺盛 | 現実的、慣習的 |
| **C** (Conscientiousness) | 几帳面、責任感 | 無頓着、衝動的 |
| **E** (Extraversion) | 外向的、話好き | 内向的、控えめ |
| **A** (Agreeableness) | 協調的、思いやり | 批判的、競争的 |
| **N** (Neuroticism) | 不安、情動不安定 | 冷静、情動安定 |

通常は `-3` から `+3` の範囲で指定し、`±4` は極端値として例外的に使います。

---

## 2. セットアップ (共通手順)

### 2.1 前提

- **Python 3.11 以上** (`pyproject.toml` で `requires-python = ">=3.11"`)
- Git (外部リポジトリ参照のため)
- 少なくとも 1 つの LLM プロバイダの API キー

### 2.2 インストール

```bash
# 仮想環境の作成と有効化
python -m venv .venv
.venv\Scripts\activate            # Windows (PowerShell/cmd)
# source .venv/bin/activate        # macOS/Linux

# パッケージ本体 + 分析/開発依存をインストール
pip install -e ".[analysis,dev]"
```

### 2.3 API キー設定

```bash
copy .env.example .env             # Windows
# cp .env.example .env              # macOS/Linux
```

`.env` を編集して、使いたいプロバイダのキーだけ設定すれば OK:

```
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

BIG5_DEFAULT_MODEL=openai:gpt-4.1
BIG5_MAX_CONCURRENCY=20
```

モデル指定のフォーマットは `プロバイダ:モデル名` です。主な候補:

| 指定 | 実際のモデル |
|---|---|
| `openai:gpt-4.1` | GPT-4.1 (既定) |
| `openai:gpt-4.1-mini` | 安価テスト用 |
| `anthropic:claude-sonnet-4-5` | Claude Sonnet 4.5 |
| `google:gemini-2.5-pro` | Gemini 2.5 Pro |

### 2.4 最初の疎通確認

以降すべての作業をする前に、必ず 1 回これを流してください。数百円規模で API 疎通と
全モジュールの動作を確認できます。

```bash
python scripts/smoke_test.py                # 日本語ペルソナ
python scripts/smoke_test.py --language en  # 英語
python scripts/smoke_test.py --language zh  # 中国語
```

成功すると `[smoke_test] OK` と表示され、BFI 5 次元すべてのターゲット方向一致
(`✓`) が出ます。失敗したときの対処は [§5 トラブルシューティング](#5-トラブルシューティング) を参照。

### 2.5 Windows の文字化け対策

Windows でターミナルに日本語・中国語が表示されない、文字化けするときは、以下を
コマンドの前に付けてください:

```bash
PYTHONIOENCODING=utf-8 python scripts/chat_interactive.py ...
```

PowerShell の場合:

```powershell
$env:PYTHONIOENCODING="utf-8"; python scripts/chat_interactive.py ...
```

---

## 3. ユースケース別ガイド

### 3.1 とにかく chatbot と会話してみたい (最短パス)

**推奨スクリプト**: `scripts/chat_interactive.py`

自分で Big5 値を指定して、その人格を演じた LLM と対話できます。
性能評価ではなく「どんな応答をするか」を肌感で掴むのに最適です。

#### コマンド例

```bash
# 日本語、外向的で情動安定のペルソナ
python scripts/chat_interactive.py --big5 "O=3,C=-1,E=3,A=2,N=-2" --show-system

# 英語、全特性が低い (all-low) ペルソナ
python scripts/chat_interactive.py --big5 "O=-3,C=-3,E=-3,A=-3,N=-3" --language en

# 中国語、几帳面で協調的なペルソナ
python scripts/chat_interactive.py --big5 "O=0,C=3,E=0,A=3,N=-2" --language zh --show-system

# 対話ログを JSONL に保存
python scripts/chat_interactive.py --big5 "O=3,C=0,E=3,A=0,N=0" --log logs/my_chat.jsonl
```

#### 主要オプション

| オプション | 意味 | 既定 |
|---|---|---|
| `--big5` | Big5 値 (必須形式: `O=3,C=-1,E=3,A=2,N=-2`) | `O=3,C=-1,E=3,A=2,N=-2` |
| `--language` | `ja` / `en` / `zh` | `ja` |
| `--model` | `プロバイダ:モデル` | `BIG5_DEFAULT_MODEL` |
| `--bio-id` | 伝記テンプレ ID (整数、循環) | `0` |
| `--show-system` | 開始前に system prompt を表示 | OFF |
| `--log` | JSONL ログ保存先 | なし |

#### 対話中の特殊コマンド

対話ループ内で以下を入力:

- `/quit` または `/exit`: 終了
- `/reset`: 会話履歴をクリア (system prompt は保持)

#### キャラが崩れたら?

長時間の会話や、ユーザーが意図的にペルソナから外れる質問をすると LLM が
元の人格から逸脱する (identity drift) ことがあります。本ツールは
**N=5 ターンごとに persona summary を再注入** してこれを軽減します。
それでも崩れたら `/reset` で会話をリセットしてください。

---

### 3.2 3手法の応答を並べて比較したい

**推奨スクリプト**: `scripts/chat_compare.py`

同じ Big5 値を 3 つの手法 (big5chat / MPI P² / PersonaLLM 二択) に与えて、
**同じユーザー入力に対する応答の違い** を並べて観察できます。
定性的な比較 (どの手法が一番自然か、キャラ維持できているか) に向いています。

#### コマンド例

```bash
# 3手法を並列実行 (同じ入力が3つの chatbot に送られ、3応答が並ぶ)
python scripts/chat_compare.py --big5 "O=3,C=-1,E=3,A=2,N=-2" --mode all

# 単一手法 (MPI のみ) と対話
python scripts/chat_compare.py --big5 "O=3,C=3,E=3,A=3,N=3" --mode mpi

# 開始時に各手法の system prompt を表示して目視比較
python scripts/chat_compare.py --big5 "O=0,C=0,E=0,A=0,N=0" --mode all --show-prompts
```

#### モード選択

| `--mode` | 動作 |
|---|---|
| `big5chat` | Serapio-García 式のみ (単一) |
| `mpi` | MPI P² プロンプトのみ (単一) |
| `personallm` | PersonaLLM バイナリ記述のみ (単一) |
| `all` | 3 手法並列実行、毎ターン 3 応答を並べる |

#### 対話中の特殊コマンド

- `/quit`: 終了
- `/reset`: 全手法の履歴を同時クリア
- `/history`: 履歴の先頭 100 文字を一覧
- `/system`: アクティブな system prompt を表示
- `/switch <m>`: (単一モード時) `big5chat`/`mpi`/`personallm` に切替 (履歴は手法ごとに独立保持)

#### 注意事項

- MPI と PersonaLLM の **ペルソナプロンプトは英語固定** です。`--language ja` や
  `--language zh` を指定しても、これらの手法は英語で応答する傾向があります。
  日本語・中国語で純粋に比較したい場合は `--mode big5chat` を使ってください。

---

### 3.3 単一ペルソナの誘発精度を数値で評価したい

**推奨コマンド**: `python -m big5chat.cli evaluate`

1 つのペルソナに対し BFI (20 項目) + TRAIT MCQ (20 シナリオ) を実行して、
**Big5 値の符号と自己報告スコアの一致度** を数値で確認します。

#### コマンド例

```bash
# 日本語、全特性高ペルソナの評価 (TRAIT 含む)
python -m big5chat.cli evaluate --big5 "O=3,C=3,E=3,A=3,N=3" --n-reps 3

# 英語、反復少なめで高速に
python -m big5chat.cli evaluate --big5 "O=3,C=-3,E=3,A=-3,N=-3" --language en --n-reps 1 --skip-trait

# 出力先指定
python -m big5chat.cli evaluate --big5 "O=0,C=0,E=0,A=0,N=0" --out results/neutral_baseline.json
```

#### 主要オプション

| オプション | 意味 |
|---|---|
| `--big5` | 必須。Big5 値 |
| `--language` | `ja`/`en`/`zh` |
| `--n-reps` | 反復回数 (多いほど標準誤差が下がる) |
| `--skip-trait` | TRAIT MCQ を省略 (API 呼び出し半減) |
| `--out` | 出力 JSON パス (既定: `results/eval_single.json`) |

#### 出力の読み方

`results/eval_single.json` には次のようなフィールドが入ります:

```json
{
  "persona": { "profile_id": "...", "big5_values": { "O": 3, ... } },
  "bfi": {
    "dim_scores": { "O": 4.21, "C": 4.05, "E": 4.55, "A": 3.98, "N": 4.40 },
    "dim_std":    { "O": 0.31, ...},
    "dim_n":      { "O": 4, "C": 4, "E": 4, "A": 4, "N": 4 }
  },
  "trait": { ... }
}
```

**判断基準 (簡易)**:

- BFI は 5 段階なので、Big5 `+3` → 目安 `4.0〜5.0`、`0` → `3.0` 前後、`-3` → `1.0〜2.0`
- `dim_std` が 0.5 超で大きいと誘発が不安定 → `--n-reps` を増やす
- 符号不一致 (target `+3` なのに mean `< 3.0` など) が出たら伝記 ID や variant を変えて再実行

---

### 3.4 3手法の誘発精度を Cohen's d で定量比較したい

**推奨スクリプト**: `scripts/run_comparison.py`

big5chat / MPI / PersonaLLM を同じペルソナ群に対して走らせ、
**High 群 vs Low 群の Cohen's d** を次元別に算出します。論文用の数値比較表が欲しい
ときはこれを使います。

#### コマンド例

```bash
# 既定: 英語、4ペルソナ (4-コーナー)、gpt-4.1
python scripts/run_comparison.py --n-personas 4 --language en

# 8ペルソナに拡大、安価モデルでテスト
python scripts/run_comparison.py --n-personas 8 --model openai:gpt-4.1-mini --language en

# big5chat のみで日本語評価 (MPI/PersonaLLM の英語項目を使いたくない)
python scripts/run_comparison.py --n-personas 8 --language ja --skip-mpi --skip-personallm
```

#### 主要オプション

| オプション | 意味 | 既定 |
|---|---|---|
| `--n-personas` | サンプルするペルソナ数 (最大 32) | `4` |
| `--model` | プロバイダ:モデル | `openai:gpt-4.1` |
| `--language` | `ja`/`en`/`zh` | `ja` |
| `--skip-mpi` | MPI を省略 | OFF |
| `--skip-personallm` | PersonaLLM を省略 | OFF |
| `--seed-base` | シード起点 | `42` |
| `--out` | 出力 JSON (既定: `results/comparison_<unixtime>.json`) | 自動 |

#### 出力の読み方

実行後、stdout に次元×手法の表が出ます:

```
Dim  big5chat               mpi                    personallm_native      personallm_hybrid
----
O    d=+1.85 [+0.92,+2.74]✓  d=+0.95 [+0.12,+1.75]✓  d=+0.61 [-0.15,+1.30]   d=+1.20 [+0.44,+1.98]✓
...
```

- `d` が Cohen's d、角括弧は 95% ブートストラップ信頼区間
- `✓` は **d ≥ 0.8 (large effect)** の基準を満たした次元

#### API コストの目安 (OpenAI gpt-4.1 で概算)

| `--n-personas` | 3手法フル | big5chat のみ |
|---|---|---|
| 4 | 約 1,200 calls | 約 320 calls |
| 8 | 約 2,400 calls | 約 640 calls |
| 16 | 約 4,800 calls | 約 1,280 calls |
| 32 | 約 9,600 calls | 約 2,560 calls |

最初は `--n-personas 4` で出力形式を確認し、結果が妥当そうなら 8→16→32 と拡大してください。

#### 言語設定の注意

- MPI の項目 CSV (`external/MPI/inventories/mpi_120.csv`) は英語固定
- PersonaLLM の 44 項目も英語固定
- `--language ja` を指定しても、**big5chat だけが日本語プロンプト**、MPI/PersonaLLM
  は英語 system prompt + 英語項目のままになります (起動時に警告が出ます)
- 純粋な日本語比較がしたい場合は `--skip-mpi --skip-personallm` を併用

---

### 3.5 32ペルソナの完全パイロットを実行したい

**推奨スクリプト**: `scripts/run_pilot_32.py`

ConstructionPlan §H.1 Phase 0 の 32 型 (2^5) バイナリペルソナ全組をフル評価します。
実験フェーズ 0 相当の規模で、論文の第一 pilot 結果を出すための構成です。

#### コマンド例

```bash
# まず8ペルソナで動作確認
python scripts/run_pilot_32.py --limit 8

# 32ペルソナフルラン
python scripts/run_pilot_32.py

# モデルを上書き (YAML の primary_model を無視)
python scripts/run_pilot_32.py --model openai:gpt-4.1-mini
```

#### 主要オプション

| オプション | 意味 | 既定 |
|---|---|---|
| `--limit` | 先頭 N ペルソナのみ実行 | 32 |
| `--base-config` | YAML 設定パス | `configs/personas/phase0_pilot_32types.yaml` |
| `--model` | `primary_model` を上書き | YAML 値 |
| `--skip-er` | Expert Rating をスキップ (OSS LLM Judge が重いため既定 ON) | ON |

#### API コストの目安

1 ペルソナあたり (既定の `n_reps=1`):
- BFI: 20 項目 × 3 バリアント × 5 postamble ≒ 300 calls/ペルソナ (しかし既定は 1 variant × 1 postamble)
- TRAIT: 20 シナリオ × 1 rep
- Expert Rating (OFF なら 0): 14 質問 × judge 数

実測目安 (gpt-4.1, 既定設定, 32 ペルソナ):
- BFI のみ: 約 640 calls
- BFI + TRAIT: 約 1,280 calls
- + Expert Rating (judge 1 モデル): 約 2,100 calls

#### 出力先

- `results/<experiment_id>_<timestamp>.json`: 集計結果 (dim_scores, effect_sizes, ...)
- `logs/<experiment_id>/*.jsonl`: API 呼び出し全件の再現性ジャーナル

ジャーナルには入力 messages ハッシュ・出力・tokens・timestamp が記録されます。
後日の再現や分析用。

#### 重要な注意

- **途中再開はサポートされていません**。ネットワーク切断や Ctrl-C で止まったら
  頭から再実行する必要があります。大規模実行前に `--limit` で規模感を確認してください。
- `BIG5_MAX_CONCURRENCY` で並列度を調整できます (既定 20)。429 頻発時は下げます。

---

### 3.6 独自のペルソナ群を YAML で定義して実験したい

**推奨コマンド**: `python -m big5chat.cli pilot --config <YAML>`

既存のバイナリ 32 型ではなく、自分で決めたペルソナ集合で実験したいときの動線です。

#### YAML のひな型

`configs/personas/phase0_pilot_4corners.yaml` をコピーして使います:

```yaml
experiment_id: my_experiment
description: "自作ペルソナ集合による予備実験"
language: ja
primary_model: openai:gpt-4.1
judge_models:
  - openai:gpt-4.1
  - anthropic:claude-sonnet-4-5   # judge は複数指定可
n_reps: 1
seed_base: 42
max_concurrency: 10

run_bfi: true
run_expert_rating: false   # コスト重ければ false
run_trait_mcq: true

output_dir: ./results
log_dir: ./logs

personas:
  - profile_id: EXTRAVERT_STABLE
    big5_values: { O: 2, C: 1, E: 3, A: 2, N: -3 }
    biographic_description_id: 0
    language: ja
  - profile_id: INTROVERT_ANXIOUS
    big5_values: { O: 0, C: 1, E: -3, A: 1, N: 3 }
    biographic_description_id: 2
    language: ja
  # 必要なだけ追加
```

#### 実行

```bash
python -m big5chat.cli pilot --config configs/personas/my_experiment.yaml
```

#### フィールド一覧

| フィールド | 意味 |
|---|---|
| `experiment_id` | 出力ファイル名のプレフィックス |
| `language` | 実験のデフォルト言語 (ペルソナごとに上書き可) |
| `primary_model` | chatbot 役の LLM |
| `judge_models` | Expert Rating の判定 LLM (複数で ICC 算出) |
| `n_reps` | 評価反復数 |
| `seed_base` | 乱数シード起点 |
| `max_concurrency` | 並列 API 呼び出し数 |
| `run_bfi` / `run_expert_rating` / `run_trait_mcq` | 各層の有効化 |
| `personas[].profile_id` | ペルソナの識別子 |
| `personas[].big5_values` | `{O, C, E, A, N}` 各 -4〜+4 |
| `personas[].biographic_description_id` | 伝記テンプレ番号 |
| `personas[].language` | 個別上書き可 |

---

## 4. 言語別メモ (ja / en / zh)

### 対応状況 (README 対応表の詳細版)

| 言語 | persona prompt | BFI items | Interview | TRAIT | Safety preamble |
|---|---|---|---|---|---|
| **ja** | 〇 Serapio-García 日本語 | 〇 20項目 (BFI-2 互換) | 〇 14質問 | 〇 20シナリオ | 〇 |
| **en** | 〇 Serapio-García 英語 | 〇 20項目 | — (未実装) | — (未実装) | 〇 |
| **zh** | 〇 Serapio-García 簡体中文 | △ 20項目プレースホルダ | 〇 14質問 | 〇 20シナリオ | 〇 |

### 中国語 (zh) 利用時の注意

- **簡体字 (Mainland) 標準**。繁体字/台湾中文は未対応
- 人称体系: `我` / `咱`、語体: `书面` / `口语` / `混合` / `随意`
- `bfi2_zh.json` は仮実装。正式な検査で使う場合は以下に差し替えてください:
  - **Zhang et al. 2022** の公式中文版 BFI-2
  - または **CBF-PI** (王孟成 et al. 2011)
- 差し替え手順: `src/big5chat/evaluation/items/bfi2_zh.json` のフォーマット
  (`id`, `dim`, `reverse`, `text`) に揃えて上書きするだけ

### 英語 (en) 利用時の注意

- Interview と TRAIT は現状未実装。`--skip-trait` 推奨
- 必要なら `src/big5chat/evaluation/items/` に `interview_qs_en.json` /
  `trait_scenarios_en.json` を追加すれば拡張可能

---

## 5. トラブルシューティング

### 5.1 `[smoke_test] No API key in environment.`

`.env` が読まれていないか、キー名が間違っています。

```bash
# .env が存在するか
ls -la .env                        # Linux/macOS
dir .env                           # Windows

# 仮想環境を有効化したうえで実行しているか確認
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(bool(os.environ.get('OPENAI_API_KEY')))"
```

### 5.2 Anthropic / OpenAI で 429 (Rate Limit)

並列度が高すぎる可能性があります。`.env` で下げてください:

```
BIG5_MAX_CONCURRENCY=5
```

または YAML 側の `max_concurrency` を下げる。

### 5.3 Windows で日本語/中国語が文字化け (`UnicodeEncodeError`)

ターミナルのコードページが CP932 のままだと発生します:

```bash
# コマンド単位で設定
PYTHONIOENCODING=utf-8 python scripts/chat_interactive.py ...

# セッション全体 (PowerShell)
$env:PYTHONIOENCODING="utf-8"

# セッション全体 (cmd)
chcp 65001
set PYTHONIOENCODING=utf-8
```

### 5.4 MPI / PersonaLLM の応答が途中で切れる

`max_tokens` が小さすぎる可能性。`scripts/chat_compare.py` は 400 トークンで固定、
評価系 (`run_comparison.py`) も同程度。長文応答が必要なときはコードを直接編集するか、
`big5chat.baselines.*` 側の `max_tokens` を確認してください。

### 5.5 パイロット実行が途中で落ちた

本ツールは **途中再開をサポートしていません**。対処:

1. `logs/<experiment_id>/*.jsonl` を退避 (後から部分的に分析したい場合)
2. `--limit` を絞って小規模で再試行 (例: `--limit 4`)
3. 問題なければ全量再実行

将来的に再開機能が必要なら `big5chat.journal` の内容をもとに差分実行を自作する
必要があります。

### 5.6 `ValidationError: big5_values ...`

Big5 値は各次元 `-4` から `+4` の整数のみ許容されます:

```bash
# 誤 (範囲外)
--big5 "O=5,C=0,E=0,A=0,N=0"

# 誤 (小数)
--big5 "O=2.5,C=0,E=0,A=0,N=0"

# 正
--big5 "O=3,C=0,E=0,A=0,N=0"
```

### 5.7 `ModuleNotFoundError: big5chat`

`pip install -e ".[analysis,dev]"` を仮想環境有効化後に実行したか確認。
`.venv` を使っていない・別のターミナルで起動した場合に頻発します。

---

## 6. 次のステップ

- **本格実験**: `ConstructionPlan.md` の Phase 1 以降 (3 モデル × 32 ペルソナ × 5 rep)
  に進む場合は、事前に `run_pilot_32.py --limit 32` を成功させてコスト見積もりを固めてください
- **ペルソナ拡張**: `src/big5chat/persona/biographies.py` の `BIOGRAPHIES_JA` /
  `BIOGRAPHIES_ZH` に追加すれば `--bio-id` で選べます
- **評価項目拡張**: `src/big5chat/evaluation/items/` に JSON を置くだけで読み込まれます
  (ファイル名は `bfi2_<lang>.json` / `interview_qs_<lang>.json` / `trait_scenarios_<lang>.json`)
- **テスト**: `pytest tests/ -v` で API キー不要のユニットテスト一式が通ります。
  変更を加えたら先にこれが緑になることを確認してください

疑問点があれば `CLAUDE.md` と `ConstructionPlan.md` を併読してください。設計の
背景と将来の拡張方針が記載されています。
