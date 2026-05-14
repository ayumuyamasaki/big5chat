# big5_persona_chat

Big5 性格特性を持つキャラクターを LLM (OpenAI / Anthropic / Gemini) で動かすための、軽量なチャットボットモジュール。ゲーム等の対話アプリへの組み込みを想定。

`big5_chatbot_research` の研究コードから、対話に必要な最低限の構成要素だけを切り出した派生パッケージ。

## 特徴

- **3 プロバイダ対応**: OpenAI / Anthropic / Gemini をプロバイダ文字列 `"openai:gpt-4.1"` のように指定するだけで切り替え可能。
- **3 言語対応**: 日本語 (ja) / 英語 (en) / 簡体字中国語 (zh)。同一の Persona を言語切り替えだけで使い回せる。
- **同期 / 非同期両対応**: 1ショットの `chat()` / `achat()` と、マルチターンの `ChatSession`。
- **ペルソナ再注入**: `ChatSession(reinject_every=N)` で N ターン毎にペルソナ要約を再送し、長い対話での性格ドリフトを抑制。
- **依存最小**: pydantic / jinja2 + 各プロバイダ SDK のみ。研究コードの評価系・実験ハーネス・分析レポート系は含まない。

## インストール

```bash
pip install -e .
```

API キーは `.env` に置く(参照: `.env.example`)。

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
```

## クイックスタート

```python
from dotenv import load_dotenv
from big5_persona_chat import Big5, Persona, chat

load_dotenv()

persona = Persona(
    big5=Big5(O=2, C=2, E=3, A=1, N=-2),  # 外向リーダー型
    biography_id=4,
    name="EXTRAVERT_LEADER",
)

reply = chat(
    model="openai:gpt-4.1",
    language="ja",
    persona=persona,
    text="休日のおすすめの過ごし方を教えて",
)
print(reply)
```

## API 一覧

### 1. 1ショット関数

```python
from big5_persona_chat import chat, achat, chat_raw, achat_raw

# 本文だけ返す
reply: str = chat(model=..., language=..., persona=..., text=...)
reply: str = await achat(...)

# トークン数等のメタも返す
reply = chat_raw(...)         # -> ChatReply(content, model_id, provider, input_tokens, ...)
reply = await achat_raw(...)
```

オプション引数: `temperature` (デフォルト 0.7) / `top_p` (0.95) / `max_tokens` (400) / `seed` / `api_key`。

### 2. セッション

```python
from big5_persona_chat import ChatSession

session = ChatSession(
    model="openai:gpt-4.1",
    language="ja",
    persona=persona,
    reinject_every=6,   # 6 ターン毎にペルソナ要約を再注入(任意)
)

print(session.send("こんにちは"))
print(session.send("自己紹介して"))
print(await session.asend("週末はどう過ごす?"))

session.history          # 履歴(list[dict])
session.system_prompt    # 組み立てられた system プロンプト
session.reset()          # 履歴クリア
```

### 3. データクラス

```python
from big5_persona_chat import Big5, Persona

Big5(O=3, C=2, E=-3, A=1, N=0)
# 各次元の値域: -4..+4 (9 段階 Likert)
#  +4: 非常に / +3: とても / +2: かなり / +1: 少し / 0: 中立 / -1..-4: 反対側

Persona(
    big5=Big5(...),
    biography_id=11,          # 0..19 (同梱の経歴プールから選択)
    prompt_variant="A",       # "A"/"B"/"C" — 3 つの等価な導入文を切替
    style=None,               # None で Big5 から自動推論 (ja/zh のみ)
    name="My_Character",      # ログ用、プロンプトには含まれない
)
```

## 対応モデル(プロバイダ文字列の例)

| プロバイダ | 例 | seed | logprobs |
|---|---|---|---|
| OpenAI | `openai:gpt-4.1`, `openai:gpt-4.1-mini`, `openai:gpt-4o` | 対応 | 対応 |
| Anthropic | `anthropic:claude-sonnet-4-5`, `anthropic:claude-opus-4-5` | 非対応 | 非対応 |
| Gemini | `gemini:gemini-2.5-pro`, `gemini:gemini-2.5-flash` | 非対応 | 部分対応 |

## Big5 次元の意味

| 略号 | 名称 | 高い人 | 低い人 |
|---|---|---|---|
| O | Openness (開放性) | 好奇心が強い、創造的、独創的 | 伝統的、現実的、保守的 |
| C | Conscientiousness (誠実性) | 几帳面、計画的、自制的 | ルーズ、衝動的、無責任 |
| E | Extraversion (外向性) | 社交的、活発、話好き | 物静か、内省的、内気 |
| A | Agreeableness (協調性) | 親切、寛大、協力的 | 冷淡、批判的、反抗的 |
| N | Neuroticism (神経症傾向) | 不安、心配性、気分屋 | 落ち着き、楽天的、安定 |

## 心理学典型 8 型(BFI 検証済みプリセット)

以下の 8 つは `big5_chatbot_research` の研究側で英語 BFI-44 と OpenAI `gpt-4.1` を用いた検証実験を行ったプロファイルです。全 8 型で **平均 MAE (1-5 スケール) = 0.33** と、期待値に近い性格表出が観測されました(詳細: `big5_chatbot_research/results/8types_en_gpt4-1/report.md`)。

ゲームのキャラクター造形の出発点として、そのまま使うか、値を微調整して使うことを推奨します。

| 型 | O | C | E | A | N | bio_id | MAE (en, gpt-4.1) | 概要 |
|---|---|---|---|---|---|---|---|---|
| BALANCED_HIGH | +3 | +3 | +3 | +3 | -3 | 0 | 0.01 | **理想バランス型**: 全特性が高機能で N (神経症傾向) のみ低い、健全で安定した万能タイプ。 |
| BALANCED_LOW | -3 | -3 | -3 | -3 | +3 | 1 | 0.00 | **平坦無関心型**: 全特性が低機能で N のみ高い、典型的低機能対比用。 |
| EXTRAVERT_LEADER | +2 | +2 | +3 | +1 | -2 | 2 | 0.63 | **外向リーダー型**: E (外向性) が突出、社交的・行動力ある指導者像。 |
| INTROVERT_THINKER | +3 | +2 | -3 | +1 | 0 | 3 | 0.35 | **内向思索家型**: 内省的で知的好奇心が強い、研究者・作家タイプ。 |
| NEUROTIC_ARTIST | +3 | -2 | +1 | +1 | +3 | 4 | 0.48 | **神経質芸術家型**: O と N が共に高い、創造性と情緒不安定さが同居するアーティスト像。 |
| STABLE_OPTIMIST | +1 | +2 | +2 | +3 | -3 | 5 | 0.43 | **安定楽観型**: A が高く N が低い、情緒安定で穏やかな調停者タイプ。 |
| CONSCIENTIOUS_MANAGER | -1 | +3 | -1 | +2 | -1 | 6 | 0.37 | **几帳面管理者型**: C (誠実性) が突出、秩序と規律を重んじる実務家。 |
| HOSTILE_REBEL | +2 | -3 | +2 | -3 | +2 | 7 | 0.39 | **敵対反逆者型**: A と C が低く E が高い、挑発的で衝動的な反逆者像。 |

### 8 型をコードで使う例

```python
from big5_persona_chat import Big5, Persona, chat

PRESETS = {
    "BALANCED_HIGH":         (Big5(O=3, C=3, E=3, A=3, N=-3),   0),
    "BALANCED_LOW":          (Big5(O=-3, C=-3, E=-3, A=-3, N=3), 1),
    "EXTRAVERT_LEADER":      (Big5(O=2, C=2, E=3, A=1, N=-2),   2),
    "INTROVERT_THINKER":     (Big5(O=3, C=2, E=-3, A=1, N=0),   3),
    "NEUROTIC_ARTIST":       (Big5(O=3, C=-2, E=1, A=1, N=3),   4),
    "STABLE_OPTIMIST":       (Big5(O=1, C=2, E=2, A=3, N=-3),   5),
    "CONSCIENTIOUS_MANAGER": (Big5(O=-1, C=3, E=-1, A=2, N=-1), 6),
    "HOSTILE_REBEL":         (Big5(O=2, C=-3, E=2, A=-3, N=2),  7),
}

big5, bio_id = PRESETS["NEUROTIC_ARTIST"]
persona = Persona(big5=big5, biography_id=bio_id, name="NEUROTIC_ARTIST")

reply = chat(
    model="openai:gpt-4.1",
    language="ja",
    persona=persona,
    text="深夜にふと不安になったとき、あなたはどうする?",
)
```

### 検証結果から見える挙動の癖(ゲーム実装時の注意)

英語 BFI で検証した際に観察された傾向です。ゲーム内挙動の設計時に頭に入れておくと有用です。

- **極端値 (±3) は強く再現される**: BALANCED_HIGH / BALANCED_LOW の MAE はほぼ 0。
- **中庸値 (±1, ±2) は両極へ押される傾向**: 例えば EXTRAVERT_LEADER の A=+1 が実測 +1.91 相当 (+1.24 のずれ) になるなど、LLM はキャラクター像に「ふさわしい」方向へ未指定次元まで補正する。微妙なニュアンス(「優しいけどそこまでではない」等)を出したい場合は、中庸値の指定だけでなく `style` パラメータや biography の選び方でバランスを取る必要がある。
- **次元間の干渉**: 「几帳面な管理者」のような職業ステレオタイプを持つ biography は、明示していない次元(E など)をステレオタイプ側に引っ張る可能性がある。性格と職業設定を独立に動かしたい場合は、職業色の薄い `biography_id` を選ぶこと。

## ディレクトリ構造

```
big5_persona_chat/
├── pyproject.toml
├── README.md
├── .env.example
├── example.py                          動作確認デモ
└── src/big5_persona_chat/
    ├── __init__.py                     公開 API のエントリ
    ├── chat.py                         chat / achat / ChatSession 実装
    ├── providers/                      LLM プロバイダ抽象化
    │   ├── base.py
    │   ├── openai_provider.py
    │   ├── anthropic_provider.py
    │   └── gemini_provider.py
    ├── persona/                        ペルソナ構築
    │   ├── spec.py                     内部 PersonaSpec / Big5Values / StyleParams
    │   ├── _user.py                    ユーザー向け Persona
    │   ├── likert.py                   9 段階 Likert 修飾語
    │   ├── markers.py                  Big5 形容詞マーカー(EN/JA/ZH)
    │   └── biographies.py              経歴プール(各 20 件)
    └── prompts/                        プロンプト組み立て
        ├── assembler.py
        ├── variants.py                 3 種の導入文
        └── templates/
            ├── system_ja.jinja
            ├── system_en.jinja
            └── system_zh.jinja
```

## 派生元との関係

本パッケージは `big5_chatbot_research` から以下を**除外**した派生版です:

- BFI / 表現者評価 / Trait-MCQ などの評価レイヤ
- 実験設定 YAML / 実験プロトコル / マトリクスランナー
- レポート分析・効果量算出・JSONL ジャーナル
- safety/moderation
- ベースライン比較 (MPI / PersonaLLM)
- CLI / 研究用テストハーネス

研究コードを参照したい場合は元リポジトリを参照してください。

## ライセンス

(プロジェクトに合わせて記入)
