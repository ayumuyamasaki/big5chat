## 進行中 (In Progress)

## 未着手 (Todo)
- [ ] .env ファイル設定（APIキー） | 期限: 2026-06-07 | 優先度: 高 | 備考: OpenAI必須、Anthropic/Geminiは任意
- [ ] Phase-0 パイロット実験実行（8ペルソナ試験） | 期限: 2026-06-14 | 優先度: 中 | 備考: APIキー設定後。run_pilot_32.py --limit 8
- [ ] Cohen's d 閾値達成の確認と調整 | 期限: 2026-06-21 | 優先度: 中 | 備考: 全5次元でd≥1.0を目標
- [ ] P² 3段チェーン実装（Neuroticism誘発強化） | 期限: 2026-07-05 | 優先度: 低 | 備考: ConstructionPlan.md §D.3

## 完了 (Done)
- [x] テスト全件実行（pytest tests/） | 完了: 2026-06-04 | 備考: 59テスト全パス。big5 conda環境で実行
