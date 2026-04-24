# big5chat — Big5 ペルソナチャットボット研究フレームワーク

ConstructionPlan.md の研究設計を実装したPythonパッケージ。

- Serapio-García 2025 式 9段階Likert修飾子によるペルソナ誘発
- 3層評価 (Self-Report BFI + Expert Rating + TRAIT MCQ)
- N=5ターン再注入によるidentity drift対策
- **日英中 (ja / en / zh) 3言語対応**
- GPT-4.1 / Claude Sonnet 4.5 / Gemini 2.5 Pro プロバイダ

詳細は `CLAUDE.md` と `ConstructionPlan.md` を参照してください。

## クイックスタート

```bash
# 1. 仮想環境の作成と依存インストール
python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell/cmd)
# source .venv/bin/activate      # macOS/Linux
pip install -e ".[analysis,dev]"

# 2. APIキーの設定
copy .env.example .env           # Windows
# cp .env.example .env           # macOS/Linux
# → .env を編集して OPENAI_API_KEY を記入

# 3. 疎通テスト (1ペルソナで20項目BFI実行、数百円規模)
python scripts/smoke_test.py

# 4. 対話テスト (インタラクティブ)
python scripts/chat_interactive.py --big5 "O=3,C=-1,E=3,A=2,N=-2" --show-system

# 5. 4ペルソナ・ミニパイロット
python -m big5chat.cli pilot --config configs/personas/phase0_pilot_4corners.yaml

# 6. 32ペルソナ・フルパイロット (要API予算)
python scripts/run_pilot_32.py --limit 8   # 最初は少数で

# 7. MPI / PersonaLLM との3方式比較 (要英語ペルソナ + API予算)
python scripts/run_comparison.py --n-personas 4 --language en

# 8. 中国語ペルソナで対話
python scripts/chat_interactive.py --big5 "O=3,C=2,E=3,A=2,N=-2" --language zh --show-system

# 9. 中国語smoke test
python scripts/smoke_test.py --language zh
```

## 対応言語

| 言語 | persona prompt | BFI items | Interview | TRAIT | Safety |
|---|---|---|---|---|---|
| **ja** | ✅ Serapio-García 日本語 | ✅ 20項目 | ✅ 14質問 | ✅ 20シナリオ | ✅ |
| **en** | ✅ Serapio-García 英語 | ✅ 20項目 | — | — | ✅ |
| **zh** | ✅ Serapio-García 簡体中文 | ✅ 20項目 | ✅ 14質問 | ✅ 20シナリオ | ✅ |

中国語は簡体字 (Mainland) を標準とし、人称は `我/咱`、語体は `书面/口语/混合/随意` の体系を採用。
BFI-2の公式中文版 (Zhang et al. 2022) または CBF-PI (王孟成 et al. 2011) に差し替えて使用してください。

## 詳しい使い方

目的別の詳細ガイドは [`docs/USAGE_GUIDE.md`](docs/USAGE_GUIDE.md) を参照してください。
「とにかく chatbot と会話してみたい」「3手法の応答を並べて比較したい」「Cohen's d で
定量比較したい」「32ペルソナのフルパイロットを回したい」などのユースケース別に
コマンド例・オプション・コスト目安・トラブルシューティングを記載しています。

## テスト

```bash
pytest tests/ -v
```

外部APIを使わないユニット+モックテストのみ含まれており、APIキーがなくても
ほぼすべてのテストが動作します (network smoke_test.py を除く)。

## 外部リポジトリ (比較ベースライン)

`external/` に先行研究の公式実装を配置しています:

- `external/MPI/` — Jiang et al. NeurIPS 2023. 120項目IPIP-NEO検査 + P² prompting.
- `external/PersonaLLM/` — Jiang et al. NAACL 2024. 44項目BFI + 32型バイナリペルソナ.

両リポジトリは旧OpenAI SDK・非推奨API (`text-davinci-003`) を使用しており、
そのままでは動作しません。本プロジェクトは `src/big5chat/baselines/` に
**同等方法論を現行APIで再実装したアダプタ**を用意しています。データファイル
(`mpi_120.csv`, `bfi_prompt.txt`, `bfi_scores.txt`) は外部リポジトリから
直接読み取るため方法論的忠実性は保たれます。
