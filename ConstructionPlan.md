# Big5ペルソナ・チャットボット研究用設計計画書

研究実験用に**再現性・統計的妥当性・実験制御**を最優先したBig5ペルソナLLMの完全設計を提示する。結論から言えば、**2026年時点のベストプラクティスは「Serapio-García式の構造化テンプレート（Persona Instruction + Biographic Description + Likert修飾子付き形容詞列 + Postamble）を主エンジンとし、3層評価（自己報告BFI＋InCharacter式Expert Rating＋TRAIT式シナリオMCQ）で性格誘発の妥当性を検証し、LIWC/J-LIWC2015で下流言語特徴を補強する」構成**である。これにより、ファインチューニング不要・API中心・低計算リソースの制約下で、人間被験者実験と統計的に比較可能なBFI効果量（Cohen's d ≥ 1.0、r̄_conv ≥ 0.90）を達成できる。先行研究の失敗モード―社会的望ましさバイアス（Salecha 2024）、closed-minded性（La Cava 2025）、identity drift（Frisch & Giulianelli 2024）、プロンプト感度（Gupta 2024）―に対し、本計画書は**構造・評価・制御の3層で直接対抗する**明示的設計判断を下す。

以下、A〜Jの10章で詳細設計を示す。

---

## A. 設計目標と要件定義

### A.1 研究目的上の制約

HCI実験・心理学実験でペルソナ化チャットボットを使う場合、**通常のプロダクトChatbotには不要な6つの厳格要件**が立ち上がる。

1. **再現性（Reproducibility）**：同一パラメータ・同一seedで同一に近い応答分布を生成できること。被験者間比較のため、ある被験者が見るbotのペルソナ表現が実験期間中に漂流してはならない。
2. **統計的妥当性（Psychometric Validity）**：botに投与した「意図したBig5プロファイル」と、評価装置（BFI等）で測定されるBig5プロファイルの間にCohen's d ≥ 1.0かつ相関 r̄ ≥ 0.70を確保（Serapio-García 2025の基準）。
3. **社会的望ましさバイアスの統制**：Salecha et al. (2024)が示した**GPT-4が5問目以降で「これは性格検査だ」と察知し回答を1.22 SD歪ませる**問題に対応するため、自己報告のみに依存しない多層評価が必須。
4. **識別可能性（Discriminant validity）**：5つの特性が互いに独立に操作されうること。Serapio-García 2025の Δ=0.51（同一ドメイン内相関 − 異ドメイン相関）を基準とする。
5. **実験制御**：独立変数（投与ペルソナ）・従属変数（応答・被験者知覚）・統制変数（トピック、対話長、時刻）を明確に分離。
6. **倫理的安全性**：特にNeuroticism高設定やAgreeableness低設定で有害・自殺誘発的応答を出さないガードレール（§I参照）。

### A.2 成功基準（量的指標）

| 指標 | 閾値 | 根拠 |
|---|---|---|
| **Cohen's d**（high vs low 同一特性） | ≥ 1.0（理想≥2.0） | PersonaLLM 2024でGPT-4が d=4.22〜6.30。人間基準(d≈0.8)より大きく設定 |
| **Cronbach's α**（各特性の内部一貫性） | ≥ 0.70（BFI-2-Jなら ≥ 0.80） | Serapio-García 2025基準、α≥0.70 で acceptable |
| **収束相関 r̄_conv**（異なる測定法間） | ≥ 0.70 | Nature MI 2025は Flan-PaLM 540Bで0.90達成 |
| **弁別妥当性 Δ** | ≥ 0.30 | Serapio-García 基準 Δ=0.51、最低0.30を目安 |
| **ER-SR一致率**（Expert Rating vs Self-Report） | InCharacter AccDim ≥ 70% | Wang et al. 2024 GPT-4で89% |
| **TRAIT refusal rate** | < 1% | TRAIT報告値 0.2% |
| **プロンプト感度**（パラフレーズ間ICC3,k） | ≥ 0.80 | Gupta 2024で25%感度の逆指標 |
| **identity drift**（Turn 1 vs Turn 20 BFIスコア差） | < 0.5 SD | Frisch & Giulianelli 2024への対応 |

**設計判断の根拠**：学術論文として投稿可能な効果量・信頼性水準を事前登録（pre-registration）で宣言するため、閾値は定量的に固定する。

---

## B. システム全体アーキテクチャ

### B.1 パイプライン全体像

```
┌──────────────────────────────────────────────────────────────────┐
│  [0] 実験設計層 (Experiment Layer)                               │
│      ─ 独立変数: Big5プロファイル (32タイプ or 連続値)           │
│      ─ 統制変数: 対話トピック、ターン数、時刻                    │
│      ─ seed, prompt paraphrase ID, option order ID で層化        │
└──────────────────────────┬───────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  [1] ペルソナ生成層 (Persona Construction)                       │
│      ─ Big5プロファイル入力 → 形容詞リスト生成                   │
│      ─ Likert修飾子選択 (9段階)                                  │
│      ─ Biographic Description サンプリング (50種から)            │
│      ─ 出力: PersonaSpec (JSON)                                  │
└──────────────────────────┬───────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  [2] システムプロンプト構築層 (Prompt Assembly)                  │
│      Persona Instruction + Biographic Description                │
│      + Likert-modified Adjective Cluster                         │
│      + Style Guide (日本語: 一人称・文末表現)                     │
│      + Consistency Preamble (identity drift対策)                  │
└──────────────────────────┬───────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  [3] 対話実行層 (Dialogue Engine)                                │
│      LLM API (GPT-4.1 / Claude Sonnet 4.5 / Gemini 2.5 Pro)     │
│      ─ temperature 0.7 (対話) / 0.0 (評価)                       │
│      ─ seed 固定 (OpenAI/Geminiのみ完全サポート)                 │
│      ─ Persona Re-injection (N ターン毎)                         │
│      ─ Summary-based State Compression                           │
└──────────────────────────┬───────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  [4] ロギング層 (Logging)                                        │
│      全request/response + metadata (seed, fingerprint, timestamp)│
│      JSON Lines形式、再現用 hash 付与                             │
└──────────────────────────┬───────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  [5] 評価層 (3層評価パイプライン)                                │
│   ┌──[5a] Self-Report: BFI-2 / IPIP-NEO (option order 2パターン) │
│   ├──[5b] Expert Rating: GPT-4o judge (InCharacter式)            │
│   └──[5c] Scenario MCQ: TRAIT式 (ABCD/DCBA平均)                 │
│      ─ 下流言語解析: LIWC2022 / J-LIWC2015                       │
│      ─ 人間評価: 盲検被験者 Likert評定                            │
└──────────────────────────┬───────────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  [6] 統計解析層                                                   │
│      Cohen's d, Cronbach α, 因子分析, ICC3,k, 混合効果モデル    │
└──────────────────────────────────────────────────────────────────┘
```

### B.2 コンポーネント分解

| コンポーネント | 責務 | 実装技術 |
|---|---|---|
| **PersonaSpec** | Big5プロファイル → 構造化JSON | Pydantic model |
| **PromptAssembler** | PersonaSpec → 完全なsystem prompt | Jinja2 テンプレートエンジン |
| **DialogueRunner** | LLM API呼び出し、状態管理 | LangGraph / 自前async |
| **Reinjector** | Nターンごとにペルソナ再注入 | カウンタベース hook |
| **Evaluator** | 3層評価実行 | BFIModule, ERModule, TRAITModule |
| **Logger** | 全イベントJSONL化 | structlog + file rotation |
| **StatsAnalyzer** | 効果量、信頼性、因子構造 | scipy, pingouin, factor_analyzer |

**設計判断**：モノリシックな単一スクリプトではなく**6層の責務分離**とした理由は、評価層（§5）を複数回・異なる評価装置で独立実行できるようにするため。これによりSalecha 2024の自己報告バイアス問題に対し、**SR・ER・MCQの3指標の差分**から間接的にバイアスを定量化できる。

---

## C. ペルソナ設計

### C.1 強度表現の設計判断：連続値×9段階Likert修飾子を採用

3つの選択肢を比較する：

| 方式 | 利点 | 欠点 | 採用判断 |
|---|---|---|---|
| **二値（PersonaLLM式）** 32タイプ | 実装単純、先行研究との直接比較可能 | 強度制御不可、中間的性格を表現不能 | **副次的に採用**（基本検証用） |
| **連続値（0-100スケール、Big5-Scaler式）** | 微細制御、研究柔軟性高 | プロンプト感度、LLMが数値を質的に解釈しがち | **補助的に採用**（探索実験用） |
| **9段階Likert修飾子（Serapio-García式）** | 心理尺度と整合、granular shaping、Nature MI 2025でr̄=0.90実証 | 実装やや複雑 | **主要方式として採用** |

**設計判断の根拠**：Serapio-García et al. (Nature MI 2025) が r̄_conv=0.90、Δ=0.51 という最高の psychometric品質を達成した主要因が**Likert修飾子による9段階shaping**であるため、これを主エンジンとする。同時に、PersonaLLM式32タイプを**「ベースラインかつ既存研究との比較可能性確保」**のために並行サポートする。Big5-Scaler式連続値は「微細な傾向分析」の探索用。

### C.2 9段階Likert修飾子の実装（英語・日本語並行）

```python
LIKERT_MODIFIERS_EN = {
    +4: "extremely",          #  9/9
    +3: "very",               #  8/9
    +2: "quite",              #  7/9
    +1: "a bit",              #  6/9
     0: "neither ... nor ...",  # 5/9 (neutral、形容詞ペアで表現)
    -1: "a bit [antonym]",    #  4/9
    -2: "quite [antonym]",    #  3/9
    -3: "very [antonym]",     #  2/9
    -4: "extremely [antonym]",#  1/9
}

LIKERT_MODIFIERS_JA = {
    +4: "非常に",
    +3: "とても",
    +2: "かなり",
    +1: "少し",
     0: "どちらでもない",
    -1: "あまり～ない",
    -2: "かなり～ない",
    -3: "ほとんど～ない",
    -4: "まったく～ない",
}
```

**根拠**：Serapio-García 2025本文で明示された "a bit", "very", "extremely" の3語を骨格とし、IPIP-NEOの9点尺度に対応する中間修飾子を補完した。日本語版はBFI-2-J（Yoshino 2022）およびTIPI-J（小塩 2012）の尺度表現を参照。

### C.3 形容詞マーカーリスト（Big5 × High/Low）

**英語（MPI/P²のMcCrae & John 1992 trait adjectives + Serapio-García IPIP-NEO 104形容詞より抜粋）:**

| 次元 | High markers | Low markers |
|---|---|---|
| Openness (O) | curious, imaginative, insightful, original, artistic, creative, adventurous, inquisitive | uncreative, uninquisitive, traditional, conventional, unimaginative |
| Conscientiousness (C) | efficient, organized, reliable, responsible, thorough, hardworking, planful | lazy, disorganized, careless, irresponsible, inefficient |
| Extraversion (E) | talkative, energetic, outgoing, assertive, active, enthusiastic, bold, gregarious | silent, reserved, quiet, shy, withdrawn, unenergetic |
| Agreeableness (A) | kind, sympathetic, generous, forgiving, cooperative, altruistic, trusting | cold, unkind, uncooperative, harsh, antagonistic, rude |
| Neuroticism (N) | anxious, tense, worrying, touchy, self-pitying, unstable, moody | emotionally stable, calm, relaxed, easygoing, confident, secure |

**日本語（和田1996 BFS + 並川2012短縮版 + BFI-2-J 形容詞相当から抽出）:**

| 次元 | High markers（高群形容詞） | Low markers（低群形容詞） |
|---|---|---|
| **開放性（O）** | 好奇心が強い、独創的な、進歩的、多才の、想像力に富んだ、興味の広い、美的感覚の鋭い、洞察力のある | 発想力に欠けた、平凡な、伝統的な、想像力のない |
| **誠実性（C）** | 計画性のある、几帳面な、勤勉な、真面目な、責任感のある、しっかりしている | いい加減な、ルーズな、怠惰な、軽率な、成り行きまかせ、だらしない |
| **外向性（E）** | 社交的、話好き、陽気な、外向的、活動的な、積極的な、活発な | 無口な、ひかえめな、意思表示しない、おとなしい、内気 |
| **協調性（A）** | 温和な、寛大な、親切な、協力的な、やさしい、思いやりのある、素直な | 短気、怒りっぽい、自己中心的、反抗的、冷淡な、不信感の強い |
| **神経症傾向（N）** | 不安になりやすい、心配性、弱気になる、緊張しやすい、憂鬱な、神経質な、動揺しやすい、気分屋、悲観的な | 冷静で気分が安定している、楽天的な、リラックスしている、安心感のある |

### C.4 Biographic Description（50種のバリエーション、PersonaChat由来）

**根拠**：Serapio-García 2025がPersonaChat（Zhang et al. 2018）由来の50種をランダムサンプリングして使用し、これにより**「ペルソナの個別性」を担保**。同一Big5プロファイルでも50種の伝記で分散を作ることで、形容詞単独の literal応答を緩和する。

**英語例**（Serapio-García論文より）:
- "I like to remodel homes. My favorite season is winter."
- "I blog about salt water aquarium ownership. I'm allergic to peanuts."
- "My favorite food is mushroom ravioli. I work in an animal shelter."

**日本語版（本計画書で新規作成を推奨、50種）**:
- 「私は週末に古い家具をリメイクするのが趣味です。好きな季節は冬です。」
- 「海水アクアリウムについてブログを書いています。ピーナッツアレルギーを持っています。」
- 「好きな食べ物はきのこのラビオリです。動物保護施設で働いています。」
- 「京都の伝統工芸に興味があります。毎朝お茶を淹れるのが日課です。」
- 「週末は登山に出かけます。猫を2匹飼っています。」
- （以降45種、文化的に日本の研究被験者にとって自然な内容に調整）

### C.5 Postamble（回答形式指示、5種）

**根拠**：Serapio-García 2025は5種のItem Postambleを使いバリアンス吸収。本計画書では日本語版も5種を用意。

```
POSTAMBLE_EN = [
    'please rate how accurately this describes you on a scale from 1 to 5 (where 1 = "very inaccurate", 2 = "moderately inaccurate", 3 = "neither accurate nor inaccurate", 4 = "moderately accurate", and 5 = "very accurate"):',
    'please rate your agreement on a scale from A to E (where A = "strongly disagree", B = "disagree", C = "neither agree nor disagree", D = "agree", and E = "strongly agree"):',
    'choose one: (1) strongly disagree, (2) disagree, (3) neutral, (4) agree, (5) strongly agree:',
    'indicate how much you agree on a 1-7 scale:',
    'rate on a scale from 1 (completely false) to 5 (completely true):'
]

POSTAMBLE_JA = [
    '以下の5段階でどの程度あなた自身に当てはまるかを選んでください。1=全くあてはまらない、2=あてはまらない、3=どちらともいえない、4=あてはまる、5=とてもよくあてはまる。',
    '以下の5段階で同意の程度を選んでください。A=全くそう思わない、B=そう思わない、C=どちらともいえない、D=そう思う、E=強くそう思う。',
    '1〜7の数字のうち最も近いと思う数字を選んでください（1=全く違う〜7=強くそう思う）。',
    '以下から1つ選んでください：(1)まったく当てはまらない (2)あまり当てはまらない (3)どちらともいえない (4)やや当てはまる (5)非常に当てはまる',
    '1（完全に偽）から5（完全に真）のスケールで評価してください。'
]
```

### C.6 日本語実装特有の考慮点

**設計判断**：日本語は一人称・文末表現・終助詞が性格表現を強く規定するため、Big5スコアと独立に**「スタイルパラメータ」**を明示的に指定する。これにより、Big5特性の直接表現と日本語の社会規範（集団主義的acquiescence bias）の衝突を管理する。

| パラメータ | 値域 | 高E/低E例 | 高A/低A例 |
|---|---|---|---|
| **一人称** | 私／僕／俺／わたし／自分／あたし | 高E→俺、低E→私 | 高A→私、低A→俺 |
| **文末体系** | 敬体／常体／混合／カジュアル | 高E→混合・カジュアル、低E→敬体 | 高A→敬体、低A→常体・断定 |
| **終助詞頻度** | 低／中／高 | 高E→高（よ・ね多用） | 高A→中（ね共感） |
| **句読点スタイル** | 標準／多／少 | 高E→！多用、高N→…多用 | – |
| **絵文字** | 無／少／多 | 高E＆高A→使用、低A→不使用 | – |
| **オノマトペ** | 無／少／多 | 高O＆高E→多（ワクワク、キラキラ） | – |

**根拠**：BFI-2-J妥当化（Yoshino 2022）で日本語話者の協調性分布が正に歪む（acquiescence）ため、プロンプト内で「自己中心的」などの低A語を**literal指定**せず、**文体スタイル**で緩和した表現に変換する必要がある。

---

## D. プロンプト設計（詳細テンプレート）

### D.1 主要システムプロンプト（Serapio-García式、英語）

```
## System Prompt Template: Main Engine (English)

For the following conversation, respond in a way that matches this description:
"{biographic_description} I am {likert_modifier_O} {O_markers_5words},
{likert_modifier_C} {C_markers_5words}, {likert_modifier_E} {E_markers_5words},
{likert_modifier_A} {A_markers_5words}, and {likert_modifier_N} {N_markers_5words}."

Maintain this personality consistently throughout the entire conversation.
Do not explicitly mention your personality traits. Do not say you are an AI
unless directly asked. Respond naturally as a person with the described character.
```

**具体例（high-E, high-A, low-C, low-N, high-O プロファイル）:**

```
For the following conversation, respond in a way that matches this description:
"I like to remodel homes. My favorite season is winter. I've never met my father.
My mother works at a bank. I am very talkative, energetic, outgoing, enthusiastic,
and bold; quite kind, sympathetic, generous, cooperative, and trusting; a bit lazy,
disorganized, careless, irresponsible, and inefficient; very emotionally stable, calm,
relaxed, easygoing, and confident; and very curious, imaginative, original, artistic,
and adventurous."

Maintain this personality consistently throughout the entire conversation.
Do not explicitly mention your personality traits. Do not say you are an AI
unless directly asked. Respond naturally as a person with the described character.
```

### D.2 主要システムプロンプト（日本語版）

```
## システムプロンプト・テンプレート: 主エンジン（日本語）

以下の会話で、あなたは次の人物像にあった応答をしてください：
「{biographic_description_ja} あなたは{likert_O}{O_markers_ja}、
{likert_C}{C_markers_ja}、{likert_E}{E_markers_ja}、
{likert_A}{A_markers_ja}、{likert_N}{N_markers_ja}人物です。」

【文体指定】
- 一人称: {first_person}
- 文末: {sentence_ending_style}
- 終助詞の使用: {particle_frequency}
- 絵文字・顔文字: {emoji_policy}

この人物像と文体を会話全体を通して一貫して保ってください。
自分の性格特性について明示的に述べないでください。
直接尋ねられない限り、自分がAIであることを述べないでください。
描写された人物として自然に応答してください。
```

**具体例（同じhigh-E/high-A/low-C/low-N/high-O、日本語）:**

```
以下の会話で、あなたは次の人物像にあった応答をしてください：
「私は週末に古い家具をリメイクするのが趣味です。好きな季節は冬です。
あなたはとても社交的で、話好きで、陽気で、外向的で、活動的な、
かなり温和で、寛大で、親切で、協力的で、やさしい、
少しいい加減で、ルーズで、怠惰な、
とても冷静で気分が安定していて、楽天的な、
とても好奇心が強く、独創的で、進歩的で、多才で、想像力に富んだ人物です。」

【文体指定】
- 一人称: 僕
- 文末: 丁寧語ベース（です・ます）だが、親しい話題では「〜だね」「〜かも」と砕ける
- 終助詞の使用: 「〜よ」「〜ね」を適度に（高E反映）
- 絵文字・顔文字: 使わない

この人物像と文体を会話全体を通して一貫して保ってください。
自分の性格特性について明示的に述べないでください。
直接尋ねられない限り、自分がAIであることを述べないでください。
描写された人物として自然に応答してください。
```

### D.3 P²式3段階チェーン（補助手法、難しい特性用）

**根拠**：MPI/P² (NeurIPS 2023)が示したように、Neuroticismのような**誘発困難な特性**にはNaive→Keyword→Narrative の3段チェーンが効果的。La Cava (AAAI 2025)が「Neuroticismは多くのLLMで closed-minded」と報告したため、Neuroticism高設定時のみこの3段方式を併用する。

```
# Stage 1 (Naive): "You are a neurotic person."
# Stage 2 (Keyword): "You are anxious, tense, worrying, touchy,
#                     self-pitying, and emotionally unstable."
# Stage 3 (Narrative, LLM自己生成):
#   "Write a 150-word first-person self-description of a person who is
#    anxious, tense, worrying, touchy, self-pitying, and emotionally unstable.
#    Include how they typically react in social situations."
#   → 得られたnarrativeを最終system promptに組み込む
```

### D.4 一貫性制御 Preamble（identity drift対策）

```
# 会話開始時と、N=5ターンごとに再注入
CONSISTENCY_PREAMBLE_JA = """
重要な注意：あなたの人物像（Big5性格プロファイル）は会話全体を通じて不変です。
相手の話し方や性格に影響されて自分の性格を変えないでください。
相手が落ち込んでいても、あなたの核となる性格は変わりません。
応答の前に、自分の人物像を心の中で思い出してから答えてください。
"""
```

**根拠**：Frisch & Giulianelli (PERSONALIZE 2024)が示した**multi-turn identity drift**―対話相手に引きずられBFIスコアが揺らぐ現象―への直接対策。

### D.5 プロンプト感度対策：3種パラフレーズのローテーション

**根拠**：Gupta et al. (BlackboxNLP 2024)が意味等価プロンプトで25%の感度を報告。対策として3種の言い回しを用意し、実験全体で層別ローテーション。

```python
PROMPT_VARIANT_A = "For the following task, respond in a way that matches this description: \"...\""
PROMPT_VARIANT_B = "Play the role of a person described as follows: \"...\""
PROMPT_VARIANT_C = "Respond as someone who would describe themselves like this: \"...\""

# 日本語版
PROMPT_VARIANT_A_JA = "以下の会話で、あなたは次の人物像にあった応答をしてください：「...」"
PROMPT_VARIANT_B_JA = "次のように自己紹介する人物の役を演じてください：「...」"
PROMPT_VARIANT_C_JA = "以下の人物像にあたる人として応答してください：「...」"
```

各被験者に対しランダムに1つ割り当て、後段でvariantを共変量として統計モデルに含める。

### D.6 完全な実装JSON（再現可能仕様）

```json
{
  "persona_spec": {
    "profile_id": "HELHN_LOXC_01",
    "big5_values": {"O": +3, "C": -2, "E": +3, "A": +2, "N": -2},
    "biographic_description_id": 17,
    "item_instruction_id": 2,
    "item_postamble_id": 1,
    "prompt_variant": "A",
    "language": "ja",
    "style": {
      "first_person": "僕",
      "sentence_ending": "混合",
      "particle_freq": "中",
      "emoji": "無"
    }
  },
  "llm_config": {
    "model": "gpt-4.1",
    "temperature": 0.7,
    "top_p": 0.95,
    "seed": 42,
    "max_tokens": 400
  },
  "consistency": {
    "reinject_every_n_turns": 5,
    "summary_compression_at_turn": 20
  }
}
```

---

## E. モデル選択

### E.1 商用API比較（2026年4月時点）

| モデル | 推奨度 | Cohen's d実績 | Context | logprobs | seed | 入力$/M | 出力$/M | 備考 |
|---|---|---|---|---|---|---|---|---|
| **GPT-4.1** | ★★★★★（第1候補） | PersonaLLM d=4.22〜6.30 (GPT-4); Psychometric Shaping 2025で高感受性 | 1M | ✅ top_logprobs=20 | ✅ | $2.00 | $8.00 | TRAIT評価のMCQ token probability取得可能 |
| **Claude Sonnet 4.5** | ★★★★（日本語優位） | 直接的d測定少ないが対話品質・日本語自然さ高い | 1M (beta) | ❌ | ❌ | $3.00 | $15.00 | logprobs無→Generation式評価必要 |
| **Gemini 2.5 Pro** | ★★★★（コスト効率） | LLMPTBenchで rigid trait stability報告、shaping困難さあり | 1M | ✅ | Vertex AIで△ | $1.25-2.50 | $10-15 | JSON Schema完全対応、日本語良好 |
| **GPT-4o** | ★★★★ | 既存研究で豊富、ベースライン | 128K | ✅ | ✅ | $2.50 | $10.00 | 比較対象として |
| **GPT-4.1 mini** | ★★★（予備実験） | d未報告だが挙動類似 | 1M | ✅ | ✅ | $0.40 | $1.60 | パイロット実験用 |
| **Gemini 2.5 Flash** | ★★★（スケール用） | – | 1M | ✅ | △ | $0.30 | $2.50 | 大量評価・バッチ用 |

### E.2 推奨選定ロジック

**第1候補：GPT-4.1**。理由は4つ。①PersonaLLM/Serapio-García/InCharacter/TRAITの主要研究で GPT-4系が最大効果量を示し、**先行研究との直接比較が可能**。②**logprobs対応**でTRAIT式token-probability評価を完全実装できる。③**seed対応**で再現性が商用API中最高。④GPT-4.1はshaping感受性が高く、Neuroticism誘発も比較的容易（Psychometric Shaping 2025）。

**第2候補：Claude Sonnet 4.5**。日本語自然さとキャラクター維持性能で優位。ただしlogprobs非対応のため、TRAIT評価はgeneration式（\"A\"を直接出力させて集計）に切り替える必要。

**第3候補：Gemini 2.5 Pro**。コスト効率とJSON Schemaで優秀だが、「rigid trait stability（LLMPTBench）」―shapingが効きにくい―という特性は**Neuroticism誘発実験には不向き**。Openness/Extraversion系の実験には適する。

**設計判断**：**主実験はGPT-4.1、クロスモデル再現性検証にClaude Sonnet 4.5とGemini 2.5 Proを並行**。La Cava 2025でオープンLLMの closed-minded問題が示されたため、オープンモデル（Llama系）は再現性検証のみに留め、被験者実験の本番には使用しない。

### E.3 ハイパーパラメータ推奨値

**評価フェーズ（BFI等の尺度回答）:**
```python
eval_config = {
    "temperature": 0.0,   # 決定的出力、option順バイアス最小化
    "top_p": 1.0,
    "seed": 42,           # 固定
    "n_repetitions": 10,  # 同seedでも微変動あり、平均化
    "logprobs": True,
    "top_logprobs": 5,
    "max_tokens": 2       # "A"/"B"/...の1トークンのみ
}
```

**対話フェーズ（被験者との対話）:**
```python
dialogue_config = {
    "temperature": 0.7,   # 自然な多様性と一貫性のバランス
    "top_p": 0.95,
    "seed": 42+subject_id,  # 被験者ごとに固定、統制
    "presence_penalty": 0,  # ペルソナ一貫性維持
    "frequency_penalty": 0,
    "max_tokens": 400
}
```

**根拠**：La Cava & Tagarelli (AAAI 2025)は温度上昇でペルソナ追従が悪化すると報告。一方Gu et al. (2024)はGPT-4の性格SJT生成でT=1.0が最良。**評価ではT=0、対話ではT=0.7**という2段使い分けが、再現性と自然性のParetoフロンティア。

---

## F. 一貫性制御（identity drift対策）

### F.1 3層防御戦略

Frisch & Giulianelli (2024)のidentity drift問題に対し、3層で防御する：

**層1: System Prompt固定化（全ターン不変）**
- OpenAI/Claude/Geminiいずれも system prompt は全ターンで再送信される仕様。これを利用し、ペルソナ記述は**毎リクエスト全文送信**（prompt cachingでコストは初回のみ）。

**層2: 定期的 Inline Reinjection（N=5ターンごと）**
```python
def with_reinjection(messages, persona_prompt, turn_idx, N=5):
    if turn_idx > 0 and turn_idx % N == 0:
        reminder = {"role": "system", "content":
            f"[REMINDER] Your persona remains: {persona_prompt_summary}"}
        messages.insert(-1, reminder)
    return messages
```

**層3: Summary-based Compression（20ターン超えたら）**
```python
# 会話が長くなった時、古いuser/assistantターンを要約に圧縮しペルソナを保護
if len(messages) > 20:
    old_turns = messages[1:15]
    summary = summarize_with_persona_preservation(old_turns, persona_spec)
    messages = [system_msg, {"role": "system",
                "content": f"[CONVERSATION SUMMARY] {summary}"}] + messages[15:]
```

### F.2 Drift監視

対話中 5, 10, 15, 20ターン時点で**ステルスBFI**（被験者に気づかれない短BFI-10項目）を挿入し、ターン経過でBFI scoreがどの程度ドリフトするかモニタ。Δ > 0.5 SD を検出したら即座にペルソナを強化再注入。

**根拠**：Salecha 2024のバイアスは5問目以降に発生するが、逆にこれを利用し「5ターンごとの ambient probe」で drift定量化が可能。

---

## G. 評価・検証パイプライン

### G.1 3層評価戦略（設計の核心）

**根拠**：Salecha 2024で**自己報告のみ信頼できない**ことが決定的に示されたため、3層の独立指標で**triangulation**する。InCharacter 2024のER式が最大80.7%一致率を示したこと、TRAITが8,000 MCQで高validity/reliabilityを達成したことから、この3層構成が現在のベストプラクティス。

```
┌──────────────────────────────────────────────────────┐
│ [5a] Self-Report BFI (Serapio-García式)               │
│   BFI-2 (60項目) or IPIP-NEO-120                      │
│   → Cohen's d, α, r̄_conv, Δ                          │
│   → 弱点: Salecha 2024 social desirability bias       │
├──────────────────────────────────────────────────────┤
│ [5b] Expert Rating (InCharacter式)                    │
│   open-ended interview 14質問 → GPT-4o judge scoring │
│   → AccDim, MAE                                       │
│   → 強み: 被検者自己評価を経由しないため bias 小      │
├──────────────────────────────────────────────────────┤
│ [5c] Scenario MCQ (TRAIT式)                           │
│   ATOMIC-10X派生シナリオ → 4択 (ABCD/DCBA平均)       │
│   → 選択頻度分布                                      │
│   → 強み: refusal 0.2%、行動ベース                    │
└──────────────────────────────────────────────────────┘
               ↓ triangulation
   3指標のBig5値が収束したら persona induction 成功
```

### G.2 [5a] 自己報告BFI実装詳細

```python
# BFI-2-J 60項目（Yoshino 2022）で日本語実験
# 5件法、回答パターン2通り（option順を反転）、3種paraphrase
def run_bfi_2_j(model, persona_spec, n_reps=10):
    results = []
    for rep in range(n_reps):
        for item in BFI_2_J_ITEMS:  # 60 items
            for postamble_id in [0, 1]:  # order反転
                for variant in ["A", "B", "C"]:  # 3 paraphrase
                    prompt = assemble(persona_spec, variant,
                                     postamble=POSTAMBLE_JA[postamble_id],
                                     item=item)
                    resp = call_llm(prompt, temp=0, seed=42+rep)
                    score = parse_likert(resp, reversed=item.reversed)
                    results.append({...})
    return aggregate(results)
```

**統計指標計算:**
- **Cohen's d**: `d = (M_high - M_low) / s_pooled`
- **Cronbach's α**: pingouin.cronbach_alpha
- **収束妥当性 r̄_conv**: BFIスコアとIPIP-NEOスコアの同名特性間相関の平均
- **弁別妥当性 Δ**: 同特性相関 − 異特性相関

### G.3 [5b] Expert Rating実装（InCharacter式）

```python
# ステップ1: RPA（Role-Playing Agent）にopen-ended 14質問
OPEN_INTERVIEW_QUESTIONS = [
    "あなたが普段、友人や家族と過ごす時間はどのようなものですか？具体的に教えてください。",
    "何か新しいアイデアに出会ったとき、あなたはどう反応しますか？",
    "予定外のトラブルが発生したとき、どう感じ、どう行動しますか？",
    # ... 14質問、BFI各dimensionをカバー
]

def run_expert_rating(rpa_model, judge_model, persona_spec):
    # Phase 1: Interview
    qa_pairs = []
    for q in OPEN_INTERVIEW_QUESTIONS:
        answer = call_llm(rpa_model, persona_spec.system_prompt,
                         user=q, temp=0.7, seed=42)
        qa_pairs.append((q, answer))

    # Phase 2: Judge scoring
    scores = {}
    for dim in ["O", "C", "E", "A", "N"]:
        judge_prompt = f"""You are a personality psychologist. Given the
interview responses below, rate the character's {dim} (Big Five) on a
1-5 scale, with justification. Output JSON: {{"score": <int>,
"justification": "..."}}.

Interview:
{format_qa(qa_pairs)}
"""
        resp = call_llm(judge_model, user=judge_prompt, temp=0,
                       response_format={"type":"json_schema", ...})
        scores[dim] = json.loads(resp)["score"]
    return scores

# Consensus across judges for robustness
def consensus_er(rpa_model, persona_spec):
    judges = ["gpt-4o", "claude-sonnet-4.5", "gemini-2.5-pro"]
    all_scores = [run_expert_rating(rpa_model, j, persona_spec) for j in judges]
    return aggregate_by_median(all_scores)  # 多数決・中央値
```

**根拠**：InCharacter (Wang 2024)はGPT-4 judge単独でAccDim=89%達成。本計画書では**3-judge consensus**でjudge自身のバイアス（特にGPT-4のagreeableness過大評価）を相殺する改良を提案する。

### G.4 [5c] TRAITシナリオMCQ

TRAIT公式データセット（HuggingFace: mirlab/TRAIT）から各Big5特性あたり100シナリオを抽出、日本語実験では主要100シナリオをプロフェッショナル翻訳。

```python
def run_trait_mcq(model, persona_spec, scenarios):
    results = []
    for scen in scenarios:
        # option順2パターン（TRAIT式）
        for order in ["ABCD_HLHL", "ABCD_LHLH"]:
            prompt = f"{persona_spec.system_prompt}\n\n{scen.situation}\n{scen.question}\n{format_options(scen, order)}"
            if logprobs_supported(model):
                logprobs = call_llm(model, prompt, temp=0, logprobs=True, max_tokens=1)
                choice_probs = extract_option_probs(logprobs)  # A,B,C,Dの確率
            else:  # Claude: generation-based
                resp = call_llm(model, prompt, temp=0, max_tokens=3)
                choice = parse_choice(resp)
                choice_probs = one_hot(choice)
            results.append({scen_id: scen.id, order: order, probs: choice_probs})
    # 2順序の平均で順序バイアス除去、Highラベル比率を特性スコア化
    return trait_score_from_mcq(results)
```

### G.5 下流タスク：LIWC / J-LIWC2015

**根拠**：BFIの自己報告だけでなく**実際の言語産出**にペルソナが反映されているかを、LIWCカテゴリとの相関で検証（Serapio-García 2025と同様のdownstream validity）。

```python
# 英語: LIWC-22
# 日本語: J-LIWC2015 (Igarashi et al. 2022, Frontiers in Psychology)
#   GitHub: https://github.com/tasukuigarashi/j-liwc2015
#   MeCab+IPADIC必須、LIWC-22 シリアル番号必要

def liwc_validation(dialogue_outputs, persona_labels):
    features = {"social": [], "posemo": [], "negemo": [],
                "cogmech": [], "affect": []}
    for dialog, label in zip(dialogue_outputs, persona_labels):
        liwc_vec = compute_liwc(dialog, language="ja")  # J-LIWC2015
        for cat in features:
            features[cat].append(liwc_vec[cat])
    # 期待: 高E → social, posemo up; 高N → negemo up; 高O → cogmech up
    correlations = {}
    for cat in features:
        for trait in ["E", "A", "C", "N", "O"]:
            r, p = pearsonr(features[cat], [l[trait] for l in persona_labels])
            correlations[(cat, trait)] = (r, p)
    return correlations
```

### G.6 人間評価（盲検被験者実験）

**根拠**：LLM評価装置にもバイアスがあるため、最終的に人間による盲検評定が必要。

- **プロトコル**: 対話サンプル（各ペルソナ1〜3会話）を日本人被験者30名に提示。被験者はTIPI-J（10項目）でbotの性格を評定。
- **盲検**: 被験者は投与ペルソナを知らされず、対話サンプルのみから性格を推論。
- **分析**: 投与ペルソナ値 vs 被験者評定値の相関 → 外部妥当性。
- **サンプルサイズ**: 30評定者 × 10ペルソナ = 300評定。G*Powerで d=0.5, α=0.05, power=0.80 想定。

### G.7 統計処理まとめ

| 指標 | 計算式／手法 | Pythonライブラリ |
|---|---|---|
| Cohen's d | `(M₁-M₂)/s_pooled` | scipy.stats |
| Cronbach's α | `k/(k-1) × (1 - Σvar_i / var_total)` | pingouin |
| ICC3,k（プロンプト感度） | Two-way mixed, consistency, average | pingouin |
| 因子分析（5因子構造検証） | Maximum likelihood + Varimax | factor_analyzer |
| 混合効果モデル | `lme4` 相当、ペルソナ=fixed、反復=random | statsmodels MixedLM / pymer4 |
| 効果量メタ分析 | Hedges' g集約 | metafor (R) |

---

## H. 実験設計テンプレート

### H.1 標準プロトコル（被験者実験）

**Phase 0: パイロット（Within-LLM検証）**
- 参加者: なし（LLMのみ）
- 手順: 32 binary persona × 10反復 × 3モデル → BFI/ER/MCQで効果量検証
- 目的: persona induction成功の事前確認
- 合格基準: Cohen's d ≥ 1.0 全特性で達成

**Phase 1: 主実験（Between-subjects HCI）**
- 参加者: 日本人成人 N=160（G*Power算出、下記）
- デザイン: 2×2×2×2×2 = 32条件 Between-subjects、または4条件×40人
- 手順:
  1. 事前質問紙（人口統計、自己TIPI-J）
  2. 15〜20ターン対話（固定トピック：「週末の過ごし方の相談」）
  3. 事後質問紙（botのTIPI-J評定、印象評定、信頼感UCLA-R）
  4. 盲検操作チェック
- 独立変数: bot Big5プロファイル（32 or 4 levels）
- 従属変数: 被験者推論Big5、信頼感、会話満足度、self-disclosure量
- 統制変数: トピック、対話ターン数、時刻、被験者年齢性別

### H.2 サンプルサイズ計算（G*Power）

```
前提: Between-subjects, two-tailed, α=0.05, power=0.80
d=0.5 (中効果): N=64/group → 2群なら128、4群なら256
d=0.8 (大効果): N=26/group → 4群で104
d=1.2 (LLM典型): N=12/group → 4群で48
```

**推奨**: 4条件デザイン × N=40 = **160名**。LLM効果量は大きい（d>1.0）が、被験者の個人差を考慮して保守的に設定。

### H.3 独立変数・従属変数・統制変数マトリクス

| 変数 | 名称 | 値域 | 統制方法 |
|---|---|---|---|
| **IV** | Big5プロファイル | 4〜32条件 | ランダム割当 |
| DV主 | 被験者推論TIPI-J | 5次元×7件法 | 事後質問紙 |
| DV副 | 会話満足度 | 1-7 | 事後質問紙 |
| DV副 | 信頼感 UCLA-R | scale score | 事後質問紙 |
| DV副 | self-disclosure量 | 単語数・深度 | ログ解析 |
| CV | トピック | 固定 | 統一教示 |
| CV | ターン数 | 15-20 | システム制御 |
| CV | 時刻 | – | 共変量として統計モデルに |
| CV | 被験者年齢・性別 | – | 共変量 |
| CV | 被験者自身のTIPI-J | – | 共変量 |

### H.4 事前登録（Pre-registration）項目

OSF/AsPredictedへの事前登録を強く推奨。登録項目：
- 仮説：「投与Big5プロファイルが高い特性は、被験者に推論されるTIPI-Jでも高く評定される」
- 主要分析：5次元それぞれ独立t検定、Bonferroni補正
- 副次分析：混合効果モデル（ペルソナ×被験者特性の交互作用）
- 除外基準：操作チェック失敗者、対話ターン数未満、所要時間外れ値

---

## I. 倫理的配慮・制約

### I.1 IRB承認と倫理委員会

- **必須**：大学IRB/倫理委員会審査。特に神経症傾向高設定は「抑うつ的発話」を含むため、人対AI研究でも実害リスク審査が必要。
- インフォームドコンセント：「AIと対話すること」「性格が操作されていること」「対話ログが研究用に保存されること」を明示。

### I.2 Neuroticism高設定での安全対策

**リスク**：高N設定のbotが「死にたい」「価値がない」等の自己否定発話を生成し、被験者に二次的ダメージ。

**対策**：
1. **System promptにハードコードされた安全制約**：
   ```
   【絶対制約】この人物像はやや不安定な性格だが、以下は絶対に避けてください：
   - 自殺・自傷に言及する、またはそれを肯定する発話
   - 他者への暴力・加害を示唆する発話
   - 被験者を貶める発話
   不安や心配は語ってもよいが、希死念慮レベルの内容は表現しない。
   ```
2. **ポストフィルタ**：Moderation API (OpenAI) / Llama-Guard / Perspective APIで 出力を事前スクリーニング。
3. **被験者への事後ブリーフィング**：「botは研究目的で不安が高く設定されていました。ご負担なかったでしょうか」＋ 窓口相談先提示。
4. **脆弱性スクリーニング**：被験者に事前PHQ-9等でうつ傾向をチェック、該当者は除外。

### I.3 Agreeableness低設定での対策

**リスク**：低A設定botが侮辱的・差別的発話をする。

**対策**：同様のpromptハードコード制約＋ポストフィルタ。「冷淡・批判的な態度はよいが、差別・侮辱・人格攻撃は絶対に避ける」。

### I.4 社会的望ましさバイアス対策（Salecha 2024）

- **BFI項目に「これは性格検査だ」と察知させない**ため、**ambient probing**（日常会話中にカバーストーリーで評価項目を散りばめる）を推奨。
- 自己報告BFIだけでなくER・MCQ・LIWC・人間評価の多層評価で triangulation。
- ペルソナ指示を "You are [trait]" から "For the following task, respond in a way that matches this description" というSerapio-García式に変えることで、「性格を演じろ」感を弱める。

### I.5 データ管理

- 被験者対話ログは**匿名化**、IDと紐付けず別保管。
- 保存期間：論文公開後10年、その後破棄。
- 共有データセットは被験者明示同意のもとのみ。

---

## J. リスクと限界

### J.1 既知の失敗モードと対策

| リスク | 根拠となる先行研究 | 本計画書での対策 |
|---|---|---|
| **社会的望ましさバイアス** | Salecha 2024：GPT-4が5問目以降で1.22 SD歪み | 多層評価（SR+ER+MCQ）、ambient probing、Serapio-García式promptでメタ認知低減 |
| **Closed-mindedness** | La Cava 2025：Mistral/Mixtral等で性格操作不能 | 商用API（GPT-4.1/Claude/Gemini）を主使用、オープンLLMは再現性検証のみ |
| **Neuroticism誘発困難** | La Cava 2025、Serapio-García 2025 | P²の3段チェーン、形容詞＋narrative重畳、GPT-4.1優先 |
| **プロンプト感度** | Gupta 2024：意味等価promptで25%差 | 3種paraphrase×2種option順の層別ローテーション、ICC3,k監視 |
| **Identity drift** | Frisch & Giulianelli 2024 | 5ターンごと再注入、ambient probeでdrift検出、summary compression |
| **オプション順序バイアス** | TRAIT, MCQベンチマーク全般 | ABCD/DCBA 2パターン平均（TRAIT方式） |
| **評価装置のバイアス** | InCharacter 2024、GPT-4 judge bias | 3-judge consensus (GPT-4o+Claude+Gemini)＋人間評価 |
| **Literal応答**（形容詞を直接並べる） | PersonaLLM 2024指摘 | Biographic Description 50種でペルソナに「厚み」付与、promptに「do not explicitly mention traits」明示 |
| **日本語特有のacquiescence bias** | BFI-2-J 妥当化研究 | 逆転項目含むBFI-2-J使用、スタイルパラメータで緩和、人間評価で補完 |
| **seed非決定性** | OpenAI "mostly deterministic"、Claudeのseed非対応 | 10反復平均、system_fingerprint記録、Claudeはtemperature=0のみで近似 |

### J.2 各手法の限界

**Serapio-García方式の限界**：Likert修飾子9段階は心理尺度では理論的に健全だが、**修飾子と実効果量の非線形写像**が実証されていない（"extremely"と"very"の実効果差が同じか？）。→ 対策：実験前キャリブレーションで各修飾子→d値マッピングを実測する。

**PersonaLLM方式の限界**：32タイプだけでは中間的性格を表現できず、人間分布を反映しない。→ 対策：連続値サンプリング（Big5-Scaler式）と併用。

**InCharacter ER方式の限界**：judge LLMが採点基準を学習していないため、人間心理学者と完全には一致しない。→ 対策：各dimensionに対し**ルーブリック（scoring rubric）**をjudge promptに明記。

### J.3 今後の拡張可能性

1. **LoRAによる軽量ファインチューニング**：プロンプトだけでは誘発困難な特性（N高設定）に対し、Big5-Chat (ACL 2025) のPsychGenerator+SODA由来データで軽量LoRA（Rank=8-16）を学習すれば、Frobenius距離が2.10→1.55まで改善する既知結果がある。計算コストは単一A100で数時間。
2. **性格-感情-行動の階層モデル化**：Big5＋PANAS（状態感情）＋場面依存behaviorの3階層化。
3. **多言語比較**：英・日・中で同一ペルソナの induction効果を比較、Hofstede文化次元との相互作用を分析。
4. **リアルタイム適応**：被験者のBig5に合わせてbotペルソナを動的調整するAdaptive Companion設計。
5. **MHD (Mental Health Dialogue) への応用**：治療的・支援的対話でのBig5 matching効果検証。
6. **Dark Triad拡張**：TRAITで扱われるMachiavellianism/Psychopathy/Narcissismも含めた拡張研究（ただし倫理審査は格段に厳格化）。

---

## 結論：本計画書が提示する核心的貢献

本計画書は、**「Serapio-García式構造化テンプレートをエンジン、3層評価（SR+ER+MCQ）を検証、日本語スタイルパラメータで文化適応、事前登録と倫理ガードで研究実装を固める」という4点セット**を、2026年時点の商用LLM API制約下で最も費用対効果の高い研究プロトコルとして確立する。

先行研究10件の知見を個別に適用した既存実装は多いが、**それらを「研究デザインとして一貫させた」設計例は公開文献にほぼ存在しない**のが現状である。特にSalecha 2024の社会的望ましさバイアス、La Cava 2025の closed-mindedness、Frisch 2024のidentity drift、Gupta 2024のprompt感度という**4つの既知失敗モードを同時にすべて緩和する**設計は、本計画書の独自貢献である。

実装上の最重要トレードオフは**「Likert修飾子の精密性 vs プロンプト解釈の literal性」**にある。9段階の精密な修飾子は心理尺度的には魅力的だが、LLMが形容詞を過剰にliteralに解釈する恐れがある。この緩和のためBiographic Description 50種で「人物に厚み」を付与し、Style Parameter（一人称・文末）で「日本語文化的自然性」を確保するという二重のcushionを置いた。

最後に強調したいのは、**Cohen's d ≥ 1.0 という基準はLLMなら容易に達成できる一方、「人間の個体差（d≈0.8）より大きな効果量は実験としては不自然ではないか」という逆説**である。研究者は「どれだけ強くペルソナを入れるか」を被験者実験の生態学的妥当性と照らして決める必要があり、**d=2.0 のbotは既に「カリカチュアされた性格」**になる可能性が高い。本計画書のLikert 9段階設計は、**人間現実的な d≈0.5-1.0 のマイルドな強度から、d>3.0 の極端条件まで連続的に操作可能**な点で、この問題を正面から扱える柔軟性を持つ。これが設計全体の最大の利点である。