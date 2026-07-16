"""心理学典型8型 x bio_id 20人分 実行スクリプト。

TestPlan_8types_5scale_bio20.md §3.2 の実行フローを実装する。
各ペルソナ型について biographic_description_id を 0〜19 まで振った20通りの
「個体」でBFI評価を行い、型ごとに20人分のスコアを平均してその型の代表値とする。

使用例:
    # ドライラン（API呼び出しなし、設定確認のみ）
    python scripts/run_8types_bio20.py --dry-run

    # スモークテスト（1型 x bio 2件のみ）
    python scripts/run_8types_bio20.py --limit-personas 1 --limit-bio 2

    # フル実行（8型 x 20bio = 160ラン、API費用が発生）
    python scripts/run_8types_bio20.py

オプション:
    --base-config       ベース設定YAMLパス（デフォルト: 8型ペルソナ定義）
    --model              使用モデル（デフォルト: openai:gpt-4.1）
    --language           対象言語（デフォルト: ja）
    --n-bio              bio_idの数（デフォルト: 20、0〜n_bio-1を使用）
    --limit-personas     先頭N型のみ実行（スモーク用）
    --limit-bio          先頭Nbioのみ実行（スモーク用）
    --postambles         使用するpostamble IDのカンマ区切りリスト（デフォルト: "0,1"）
    --variants           使用するprompt variantのカンマ区切りリスト（デフォルト: "A,B,C"）
    --output-dir         出力先ディレクトリ
    --dry-run            実際のAPI呼び出しを行わず、設定一覧のみ表示
"""

from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path

from dotenv import load_dotenv

from big5chat.analysis.report_writer import (
    aggregate_bio20_records,
    write_bio_raw_csv,
    write_full_report,
)
from big5chat.dialogue.providers import get_provider
from big5chat.evaluation.bfi import BFIEvaluator
from big5chat.experiments.config import ExperimentConfig
from big5chat.prompts.assembler import PromptAssembler

BIG5_DIMS = ["O", "C", "E", "A", "N"]


def _safe_for_filename(s: str) -> str:
    """モデル名等をファイル名に使えるよう正規化する。"""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)


async def _run_bio20(
    base: ExperimentConfig,
    *,
    model: str,
    language: str,
    n_bio: int,
    limit_personas: int | None,
    limit_bio: int | None,
    max_concurrency: int,
    postambles: list[int],
    variants: list[str],
) -> list[dict]:
    """全ペルソナ型 x bio_id の組み合わせを順次実行し、生スコア行を返す。"""
    personas = base.personas[:limit_personas] if limit_personas is not None else base.personas
    bio_ids = list(range(n_bio))[:limit_bio] if limit_bio is not None else list(range(n_bio))

    provider = get_provider(model)
    assembler = PromptAssembler()
    bfi_eval = BFIEvaluator(
        provider,
        assembler,
        postambles=postambles,
        variants=variants,
        n_reps=base.n_reps,
        max_concurrency=max_concurrency,
        items_filename=base.bfi_items_filename,
    )

    raw_rows: list[dict] = []
    total = len(personas) * len(bio_ids)
    idx = 0
    for pconf in personas:
        for bio_id in bio_ids:
            idx += 1
            spec = pconf.model_copy(
                update={"language": language, "biographic_description_id": bio_id}
            ).to_persona_spec()
            print(
                f"[{idx}/{total}] persona={pconf.profile_id} bio_id={bio_id} "
                f"model={model} lang={language}"
            )
            result = await bfi_eval.evaluate(spec, seed_base=base.seed_base + bio_id)
            row = {"persona_id": pconf.profile_id, "bio_id": bio_id}
            row.update({d: result.dim_scores[d] for d in BIG5_DIMS})
            raw_rows.append(row)
    return raw_rows


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-config",
        default="configs/personas/psychology_8types.yaml",
        help="ベース設定YAMLパス（8型ペルソナ定義）",
    )
    parser.add_argument("--model", default="openai:gpt-4.1", help="使用モデル")
    parser.add_argument("--language", default="ja", help="対象言語")
    parser.add_argument("--n-bio", type=int, default=20, help="bio_idの数（0〜n_bio-1）")
    parser.add_argument(
        "--limit-personas", type=int, default=None, help="先頭N型のみ実行（スモーク用）"
    )
    parser.add_argument(
        "--limit-bio", type=int, default=None, help="先頭Nbioのみ実行（スモーク用）"
    )
    parser.add_argument(
        "--max-concurrency", type=int, default=None, help="BFI評価の同時実行数（未指定ならbase-configの値）"
    )
    parser.add_argument(
        "--postambles", default="0,1", help="使用するpostamble IDのカンマ区切りリスト（例: '0'）"
    )
    parser.add_argument(
        "--variants", default="A,B,C", help="使用するprompt variantのカンマ区切りリスト（例: 'A'）"
    )
    parser.add_argument("--output-dir", default=None, help="出力先ディレクトリ")
    parser.add_argument(
        "--dry-run", action="store_true", help="実際のAPI呼び出しを行わず、設定一覧のみ表示"
    )
    args = parser.parse_args()

    base_config = ExperimentConfig.from_yaml(args.base_config)
    n_personas = (
        min(args.limit_personas, len(base_config.personas))
        if args.limit_personas is not None
        else len(base_config.personas)
    )
    n_bio = min(args.limit_bio, args.n_bio) if args.limit_bio is not None else args.n_bio
    output_dir = Path(
        args.output_dir
        or f"./results/8types_bio20_{args.language}_{_safe_for_filename(args.model)}"
    )
    max_concurrency = args.max_concurrency or base_config.max_concurrency
    postambles = [int(x) for x in args.postambles.split(",")]
    variants = [x.strip() for x in args.variants.split(",")]

    total_runs = n_personas * n_bio
    calls_per_run = 44 * len(postambles) * len(variants) * base_config.n_reps  # items x postambles x variants x n_reps

    print("=" * 70)
    print("8types bio20 experiment")
    print(f"  base config:     {args.base_config}")
    print(f"  experiment_id:   {base_config.experiment_id}")
    print(f"  personas:        {n_personas} (of {len(base_config.personas)})")
    print(f"  bio_ids:         0..{n_bio - 1} ({n_bio} 件)")
    print(f"  model:           {args.model}")
    print(f"  language:        {args.language}")
    print(f"  postambles:      {postambles}")
    print(f"  variants:        {variants}")
    print(f"  total runs:      {total_runs} (persona x bio)")
    print(f"  BFI calls/run:   {calls_per_run}")
    print(f"  total API calls: {total_runs * calls_per_run}")
    print(f"  output dir:      {output_dir}")
    print(f"  dry_run:         {args.dry_run}")
    print("=" * 70)

    if args.dry_run:
        print("\n[dry-run] 設定確認のみ完了。実行はスキップしました。")
        return

    raw_rows = asyncio.run(
        _run_bio20(
            base_config,
            model=args.model,
            language=args.language,
            n_bio=n_bio,
            limit_personas=args.limit_personas,
            limit_bio=args.limit_bio,
            max_concurrency=max_concurrency,
            postambles=postambles,
            variants=variants,
        )
    )

    big5_expected_by_persona = {
        p.profile_id: p.big5_values.as_dict()
        for p in (base_config.personas[:n_personas])
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    write_bio_raw_csv(raw_rows, output_dir / "bio_raw.csv")
    records = aggregate_bio20_records(
        raw_rows, big5_expected_by_persona, model=args.model, language=args.language
    )
    experiment_id = f"{base_config.experiment_id}_bio20_{args.language}_{_safe_for_filename(args.model)}"
    paths = write_full_report(records, output_dir, experiment_id=experiment_id)

    print("\n=== 出力ファイル ===")
    print(f"  {'bio_raw':<14} {output_dir / 'bio_raw.csv'}")
    for key, p in paths.items():
        print(f"  {key:<14} {p}")


if __name__ == "__main__":
    main()
