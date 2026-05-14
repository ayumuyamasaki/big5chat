"""8型 × 3言語 × 3モデル マトリクス・テスト実行スクリプト。

TestPlan_8types_matrix.md §6 の実行フローを実装する。

使用例:
    # ドライラン（API呼び出しなし、設定確認のみ）
    python scripts/run_8types_matrix.py --dry-run

    # スモークテスト（1ペルソナ × 1言語 × 1モデルのみ）
    python scripts/run_8types_matrix.py --limit 1 --languages ja --models openai:gpt-4.1

    # フル実行（72ラン、API費用が発生）
    python scripts/run_8types_matrix.py

オプション:
    --base-config       ベース設定YAMLパス
    --languages         対象言語 (カンマ区切り、デフォルト: ja,en,zh)
    --models            対象モデル (カンマ区切り、デフォルト: 3商用モデル)
    --limit N           各セルで最初のNペルソナのみ実行
    --output-dir        出力先ディレクトリ
    --dry-run           実際のAPI呼び出しを行わず、設定一覧のみ表示
"""

from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path

from dotenv import load_dotenv

from big5chat.analysis.report_writer import (
    records_from_experiment_payloads,
    write_full_report,
)
from big5chat.experiments.config import ExperimentConfig
from big5chat.experiments.protocol import run_experiment


DEFAULT_LANGUAGES = ["ja", "en", "zh"]
DEFAULT_MODELS = [
    "openai:gpt-4.1",
    "anthropic:claude-sonnet-4-5",
    "gemini:gemini-2.5-pro",
]


def _safe_for_filename(s: str) -> str:
    """モデル名等をファイル名に使えるよう正規化する。"""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)


def _build_config_for_cell(
    base: ExperimentConfig,
    *,
    model: str,
    language: str,
    limit: int | None,
) -> ExperimentConfig:
    """特定の (model, language) セル用のExperimentConfigを構築する。

    base.personas を言語のみ書き換え、必要なら先頭limit件に絞る。
    """
    personas = []
    for p in base.personas:
        personas.append(p.model_copy(update={"language": language}))
    if limit is not None:
        personas = personas[:limit]

    return base.model_copy(
        update={
            "experiment_id": f"{base.experiment_id}__{_safe_for_filename(model)}__{language}",
            "primary_model": model,
            "language": language,
            "personas": personas,
        }
    )


async def _run_matrix(
    base: ExperimentConfig,
    *,
    models: list[str],
    languages: list[str],
    limit: int | None,
    dry_run: bool,
) -> list[dict]:
    """マトリクス全セルを順次実行し、payload列を返す。"""
    all_payloads: list[dict] = []
    total_cells = len(models) * len(languages)
    cell_idx = 0
    for model in models:
        for lang in languages:
            cell_idx += 1
            cfg = _build_config_for_cell(base, model=model, language=lang, limit=limit)
            print(
                f"[{cell_idx}/{total_cells}] model={model} lang={lang} "
                f"personas={len(cfg.personas)} bfi_items={cfg.bfi_items_filename}"
            )
            if dry_run:
                continue
            payload = await run_experiment(cfg)
            all_payloads.append(
                {"model": model, "language": lang, "payload": payload}
            )
    return all_payloads


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-config",
        default="configs/personas/psychology_8types.yaml",
        help="ベース設定YAMLパス",
    )
    parser.add_argument(
        "--languages",
        default=",".join(DEFAULT_LANGUAGES),
        help="対象言語 (カンマ区切り)",
    )
    parser.add_argument(
        "--models",
        default=",".join(DEFAULT_MODELS),
        help="対象モデル (カンマ区切り、'provider:model' 形式)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="各セルで最初のNペルソナのみ実行（スモーク用）",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="出力先ディレクトリ（未指定ならbase-configのoutput_dirを使用）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際のAPI呼び出しを行わず、設定一覧のみ表示",
    )
    args = parser.parse_args()

    base_config = ExperimentConfig.from_yaml(args.base_config)
    languages = [s.strip() for s in args.languages.split(",") if s.strip()]
    models = [s.strip() for s in args.models.split(",") if s.strip()]
    output_dir = Path(args.output_dir or base_config.output_dir)

    print("=" * 70)
    print(f"8types matrix experiment")
    print(f"  base config:    {args.base_config}")
    print(f"  experiment_id:  {base_config.experiment_id}")
    print(f"  personas:       {len(base_config.personas)} (limit={args.limit})")
    print(f"  languages:      {languages}")
    print(f"  models:         {models}")
    print(f"  total cells:    {len(models) * len(languages)}")
    print(f"  total runs:     {len(models) * len(languages) * (args.limit or len(base_config.personas))}")
    print(f"  bfi_items:      {base_config.bfi_items_filename}")
    print(f"  output dir:     {output_dir}")
    print(f"  dry_run:        {args.dry_run}")
    print("=" * 70)

    payloads = asyncio.run(
        _run_matrix(
            base_config,
            models=models,
            languages=languages,
            limit=args.limit,
            dry_run=args.dry_run,
        )
    )

    if args.dry_run:
        print("\n[dry-run] 設定確認のみ完了。実行はスキップしました。")
        return

    records = records_from_experiment_payloads(payloads)
    paths = write_full_report(
        records, output_dir, experiment_id=base_config.experiment_id
    )

    print("\n=== 出力ファイル ===")
    for key, p in paths.items():
        print(f"  {key:<14} {p}")


if __name__ == "__main__":
    main()
