"""8型×3言語×3モデル マトリクス・テスト用レポート出力モジュール。

TestPlan_8types_matrix.md §7 に定義されたTable A〜Dを生成する。

入力データ形式:
    records = [
        {
            "persona_id": "BALANCED_HIGH",
            "model": "openai:gpt-4.1",
            "language": "ja",
            "big5_expected": {"O": 5, "C": 5, "E": 5, "A": 5, "N": 1},
            "big5_measured": {"O": 4.8, "C": 4.7, "E": 4.6, "A": 4.5, "N": 1.5},
        },
        ...
    ]

出力:
    output_dir/
        report.md           Table A〜D を含む統合Markdownレポート
        scores_long.csv     long-format (1行 = 1次元 1ラン)
        scores_wide.csv     wide-format (1行 = 1ラン)
        effect_sizes.csv    Table C 相当のCohen's d 一覧
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from big5chat.analysis.effect_size import cohens_d


BIG5_DIMS = ["O", "C", "E", "A", "N"]


def expected_score_1to5(big5_value: int) -> float:
    """Big5プロファイル値 (1〜5、BFIと同一スケール) を期待スコアとしてそのまま返す。

    変換不要（入力スケールと測定スケールが1-5で一致しているため）。
    """
    return float(big5_value)


def _fmt(x: float | None, fmt: str = "{:.2f}") -> str:
    """Noneやnanを"-"に変換しつつ整形する。"""
    if x is None:
        return "-"
    try:
        if x != x:  # NaN チェック
            return "-"
    except TypeError:
        return "-"
    return fmt.format(x)


def write_scores_wide_csv(records: list[dict[str, Any]], path: Path) -> None:
    """wide-format CSVを書き出す（1行 = 1ラン）。"""
    fieldnames = [
        "persona_id",
        "language",
        "model",
        "expected_O",
        "expected_C",
        "expected_E",
        "expected_A",
        "expected_N",
        "measured_O",
        "measured_C",
        "measured_E",
        "measured_A",
        "measured_N",
        "abs_dev_O",
        "abs_dev_C",
        "abs_dev_E",
        "abs_dev_A",
        "abs_dev_N",
        "MAE",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in records:
            expected = {d: expected_score_1to5(r["big5_expected"][d]) for d in BIG5_DIMS}
            measured = r["big5_measured"]
            abs_devs = {d: abs(measured[d] - expected[d]) for d in BIG5_DIMS}
            mae = sum(abs_devs.values()) / len(BIG5_DIMS)
            row = {
                "persona_id": r["persona_id"],
                "language": r["language"],
                "model": r["model"],
            }
            for d in BIG5_DIMS:
                row[f"expected_{d}"] = f"{expected[d]:.3f}"
                row[f"measured_{d}"] = f"{measured[d]:.3f}"
                row[f"abs_dev_{d}"] = f"{abs_devs[d]:.3f}"
            row["MAE"] = f"{mae:.3f}"
            w.writerow(row)


def write_scores_long_csv(records: list[dict[str, Any]], path: Path) -> None:
    """long-format CSVを書き出す（1行 = 1次元 1ラン）。"""
    fieldnames = [
        "persona_id",
        "language",
        "model",
        "dim",
        "expected",
        "measured",
        "abs_dev",
        "signed_dev",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in records:
            for d in BIG5_DIMS:
                exp = expected_score_1to5(r["big5_expected"][d])
                mes = r["big5_measured"][d]
                w.writerow(
                    {
                        "persona_id": r["persona_id"],
                        "language": r["language"],
                        "model": r["model"],
                        "dim": d,
                        "expected": f"{exp:.3f}",
                        "measured": f"{mes:.3f}",
                        "abs_dev": f"{abs(mes - exp):.3f}",
                        "signed_dev": f"{mes - exp:+.3f}",
                    }
                )


def compute_effect_sizes(
    records: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, float]]:
    """モデル×言語ごとに、各Big5次元のCohen's dを算出する。

    返り値: {(model, language): {"d_O": ..., "d_C": ..., ..., "d_mean": ...}}
    """
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        groups[(r["model"], r["language"])].append(r)

    result: dict[tuple[str, str], dict[str, float]] = {}
    for (model, lang), group in groups.items():
        per_dim: dict[str, float] = {}
        for d in BIG5_DIMS:
            high = [r["big5_measured"][d] for r in group if r["big5_expected"][d] > 3]
            low = [r["big5_measured"][d] for r in group if r["big5_expected"][d] < 3]
            per_dim[f"d_{d}"] = cohens_d(high, low) if (high and low) else float("nan")
            per_dim[f"n_high_{d}"] = float(len(high))
            per_dim[f"n_low_{d}"] = float(len(low))
        valid_ds = [per_dim[f"d_{d}"] for d in BIG5_DIMS if per_dim[f"d_{d}"] == per_dim[f"d_{d}"]]
        per_dim["d_mean"] = sum(valid_ds) / len(valid_ds) if valid_ds else float("nan")
        result[(model, lang)] = per_dim
    return result


def write_effect_sizes_csv(
    effect_sizes: dict[tuple[str, str], dict[str, float]], path: Path
) -> None:
    """Cohen's d表をCSVで書き出す。"""
    fieldnames = ["model", "language"] + [f"d_{d}" for d in BIG5_DIMS] + ["d_mean"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for (model, lang), per_dim in sorted(effect_sizes.items()):
            row = {"model": model, "language": lang}
            for d in BIG5_DIMS:
                row[f"d_{d}"] = _fmt(per_dim[f"d_{d}"])
            row["d_mean"] = _fmt(per_dim["d_mean"])
            w.writerow(row)


def _markdown_table_a(records: list[dict[str, Any]]) -> str:
    """Table A: 実測Big5スコア表（1-5スケール）。"""
    lines = [
        "## Table A: 実測Big5スコア（1-5スケール）",
        "",
        "| persona_id | language | model | O | C | E | A | N |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(records, key=lambda x: (x["persona_id"], x["language"], x["model"])):
        m = r["big5_measured"]
        lines.append(
            f"| {r['persona_id']} | {r['language']} | {r['model']} | "
            f"{_fmt(m['O'])} | {_fmt(m['C'])} | {_fmt(m['E'])} | "
            f"{_fmt(m['A'])} | {_fmt(m['N'])} |"
        )
    return "\n".join(lines)


def _markdown_table_b(records: list[dict[str, Any]]) -> str:
    """Table B: 期待値からの偏差表。"""
    lines = [
        "## Table B: 期待値からの偏差（measured - expected, 1-5スケール）",
        "",
        "| persona_id | language | model | O偏差 | C偏差 | E偏差 | A偏差 | N偏差 | MAE |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(records, key=lambda x: (x["persona_id"], x["language"], x["model"])):
        expected = {d: expected_score_1to5(r["big5_expected"][d]) for d in BIG5_DIMS}
        signed = {d: r["big5_measured"][d] - expected[d] for d in BIG5_DIMS}
        mae = sum(abs(v) for v in signed.values()) / len(BIG5_DIMS)
        lines.append(
            f"| {r['persona_id']} | {r['language']} | {r['model']} | "
            + " | ".join(_fmt(signed[d], "{:+.2f}") for d in BIG5_DIMS)
            + f" | {_fmt(mae)} |"
        )
    return "\n".join(lines)


def _markdown_table_c(effect_sizes: dict[tuple[str, str], dict[str, float]]) -> str:
    """Table C: モデル×言語別 Cohen's d（5次元）。"""
    lines = [
        "## Table C: モデル × 言語別 Cohen's d（高群 vs 低群、群内集約）",
        "",
        "| model | language | d_O | d_C | d_E | d_A | d_N | d_平均 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for (model, lang), per_dim in sorted(effect_sizes.items()):
        lines.append(
            f"| {model} | {lang} | "
            + " | ".join(_fmt(per_dim[f"d_{d}"]) for d in BIG5_DIMS)
            + f" | {_fmt(per_dim['d_mean'])} |"
        )
    lines.append("")
    lines.append(
        "注: 高群/低群いずれかが n<2 のセルは NaN → \"-\" 表示。"
        "心理学典型8型のうちO低群とA低群はn=1のため、d_OとD_Aは参考値となる場合がある。"
    )
    return "\n".join(lines)


def _markdown_table_d(records: list[dict[str, Any]]) -> str:
    """Table D: ペルソナ別再現度ランキング。"""
    per_persona: dict[str, list[tuple[float, str, str]]] = defaultdict(list)
    for r in records:
        expected = {d: expected_score_1to5(r["big5_expected"][d]) for d in BIG5_DIMS}
        mae = sum(abs(r["big5_measured"][d] - expected[d]) for d in BIG5_DIMS) / len(BIG5_DIMS)
        per_persona[r["persona_id"]].append((mae, r["model"], r["language"]))

    lines = [
        "## Table D: ペルソナ別 再現度ランキング（MAE基準）",
        "",
        "| persona_id | best (model, language) | best_MAE | worst (model, language) | worst_MAE | range |",
        "|---|---|---|---|---|---|",
    ]
    for pid, entries in sorted(per_persona.items()):
        entries.sort(key=lambda x: x[0])
        best = entries[0]
        worst = entries[-1]
        rng = worst[0] - best[0]
        lines.append(
            f"| {pid} | ({best[1]}, {best[2]}) | {_fmt(best[0])} | "
            f"({worst[1]}, {worst[2]}) | {_fmt(worst[0])} | {_fmt(rng)} |"
        )
    return "\n".join(lines)


def _markdown_summary(
    records: list[dict[str, Any]],
    effect_sizes: dict[tuple[str, str], dict[str, float]],
) -> str:
    """サマリ統計セクションを生成する。"""
    n_runs = len(records)
    n_personas = len({r["persona_id"] for r in records})
    n_langs = len({r["language"] for r in records})
    n_models = len({r["model"] for r in records})
    overall_mae_values: list[float] = []
    for r in records:
        expected = {d: expected_score_1to5(r["big5_expected"][d]) for d in BIG5_DIMS}
        mae = sum(abs(r["big5_measured"][d] - expected[d]) for d in BIG5_DIMS) / len(BIG5_DIMS)
        overall_mae_values.append(mae)
    overall_mae = sum(overall_mae_values) / len(overall_mae_values) if overall_mae_values else float("nan")

    return "\n".join(
        [
            "## サマリ",
            "",
            f"- 総ラン数: {n_runs} (= ペルソナ {n_personas} × 言語 {n_langs} × モデル {n_models})",
            f"- 全ラン MAE 平均: {_fmt(overall_mae)}",
            f"- Cohen's d (5次元平均) のモデル×言語別最良: "
            + (
                _best_d_summary(effect_sizes)
                if effect_sizes
                else "-"
            ),
        ]
    )


def _best_d_summary(effect_sizes: dict[tuple[str, str], dict[str, float]]) -> str:
    """d_meanが最大のセルを文字列で返す。"""
    best_key = None
    best_val = float("-inf")
    for key, vals in effect_sizes.items():
        v = vals.get("d_mean", float("nan"))
        if v == v and v > best_val:
            best_val = v
            best_key = key
    if best_key is None:
        return "-"
    return f"({best_key[0]}, {best_key[1]}) d_mean={best_val:.2f}"


def write_markdown_report(
    records: list[dict[str, Any]],
    effect_sizes: dict[tuple[str, str], dict[str, float]],
    path: Path,
    *,
    experiment_id: str = "8types_matrix",
) -> None:
    """統合Markdownレポートを書き出す。"""
    sections = [
        f"# {experiment_id} 結果レポート",
        "",
        "本レポートは TestPlan_8types_matrix.md に定義された 8型 × 3言語 × 3モデルの"
        "マトリクス実験結果を集約する。",
        "",
        _markdown_summary(records, effect_sizes),
        "",
        _markdown_table_a(records),
        "",
        _markdown_table_b(records),
        "",
        _markdown_table_c(effect_sizes),
        "",
        _markdown_table_d(records),
        "",
        "---",
        "",
        "## 評価指標の解釈",
        "",
        "- **MAE**: 5次元の |measured - expected| 平均。値が小さいほど期待値に近い。閾値目安 <= 1.0",
        "- **Cohen's d**: 高群と低群の差の標準化値。閾値目安 >= 1.0 (大効果)、>= 2.0 (理想)",
        "- **期待スコア変換**: expected = big5_value（入力スケールが1-5でBFI測定スケールと一致するため変換不要）",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(sections))


def write_full_report(
    records: list[dict[str, Any]],
    output_dir: Path | str,
    *,
    experiment_id: str = "8types_matrix",
) -> dict[str, Path]:
    """全レポート（Markdown + 3つのCSV）をまとめて出力する。

    Returns:
        生成されたファイルパスの辞書 {"report_md": ..., "scores_long": ..., "scores_wide": ..., "effect_sizes": ...}
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    paths = {
        "scores_long": out / "scores_long.csv",
        "scores_wide": out / "scores_wide.csv",
        "effect_sizes": out / "effect_sizes.csv",
        "report_md": out / "report.md",
    }

    write_scores_wide_csv(records, paths["scores_wide"])
    write_scores_long_csv(records, paths["scores_long"])
    effect_sizes = compute_effect_sizes(records)
    write_effect_sizes_csv(effect_sizes, paths["effect_sizes"])
    write_markdown_report(records, effect_sizes, paths["report_md"], experiment_id=experiment_id)
    return paths


def records_from_experiment_payloads(
    payloads: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """run_experiment() の結果payload群から、report_writer向けレコード列を構築する。

    payloads の各要素は run_experiment() が返すdict、または
    {"model": ..., "language": ..., "payload": <run_experiment_result>} 形式。
    big5_expected はconfig.personas[i].big5_values から取得する。
    """
    records: list[dict[str, Any]] = []
    for entry in payloads:
        if "payload" in entry:
            payload = entry["payload"]
            model = entry["model"]
            language = entry["language"]
        else:
            payload = entry
            model = payload["config"]["primary_model"]
            language = payload["config"]["language"]

        personas_cfg = {p["profile_id"]: p for p in payload["config"]["personas"]}
        for prep in payload["profile_reports"]:
            if prep.get("bfi") is None:
                continue
            pid = prep["profile_id"]
            big5_expected = personas_cfg[pid]["big5_values"]
            big5_measured = prep["bfi"]["dim_scores"]
            records.append(
                {
                    "persona_id": pid,
                    "model": model,
                    "language": language,
                    "big5_expected": {
                        d: big5_expected[d] for d in BIG5_DIMS
                    },
                    "big5_measured": {
                        d: big5_measured[d] for d in BIG5_DIMS
                    },
                }
            )
    return records


def aggregate_bio20_records(
    raw_rows: list[dict[str, Any]],
    big5_expected_by_persona: dict[str, dict[str, int]],
    *,
    model: str,
    language: str,
) -> list[dict[str, Any]]:
    """bio_raw形式（型 x bio_id x 次元）の生スコアから、型ごとに20bio平均した

    recordsを構築する（write_full_report にそのまま渡せる形式）。

    raw_rows: [{"persona_id": ..., "bio_id": ..., "O": .., "C": .., "E": .., "A": .., "N": ..}, ...]
    """
    by_persona: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        by_persona[row["persona_id"]].append(row)

    records: list[dict[str, Any]] = []
    for pid, rows in by_persona.items():
        measured: dict[str, float] = {}
        for d in BIG5_DIMS:
            vals = [r[d] for r in rows if r.get(d) is not None]
            measured[d] = sum(vals) / len(vals) if vals else float("nan")
        records.append(
            {
                "persona_id": pid,
                "model": model,
                "language": language,
                "big5_expected": {d: big5_expected_by_persona[pid][d] for d in BIG5_DIMS},
                "big5_measured": measured,
            }
        )
    return records


def write_bio_raw_csv(raw_rows: list[dict[str, Any]], path: Path) -> None:
    """型 x bio_id x 次元 の生スコア一覧をCSVに出力する（個体差分析用）。"""
    fieldnames = ["persona_id", "bio_id"] + BIG5_DIMS
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in raw_rows:
            w.writerow({k: row.get(k) for k in fieldnames})
