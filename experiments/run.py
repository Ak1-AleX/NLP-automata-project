"""Командный запуск воспроизводимого сравнения bounded-модели и CFG."""

from __future__ import annotations

import argparse
import json
import platform
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from automata.bounded_nesting import analyze as bounded_analyze
from experiments.evaluate import (
    RESULTS_DIR,
    evaluate,
    save_details_json,
    save_summary_csv,
)
from experiments.generate import generate_dataset
from grammar.parser import analyze as cfg_analyze


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def run_experiment(
    min_depth: int = 0,
    max_depth: int = 4,
    n_per_depth: int = 20,
    seed: int = 42,
    bounded_depth: int = 1,
    results_dir: Path | None = None,
) -> dict:
    """Генерирует данные, сравнивает модели и сохраняет полный прогон."""
    if min_depth < 0 or max_depth < min_depth:
        raise ValueError("требуется 0 <= min_depth <= max_depth")
    if n_per_depth <= 0:
        raise ValueError("n_per_depth должен быть больше нуля")
    if bounded_depth < 0:
        raise ValueError("bounded_depth не может быть отрицательной")

    dataset = generate_dataset(
        range(min_depth, max_depth + 1),
        n_per_depth=n_per_depth,
        include_negative=True,
        seed=seed,
    )
    result = evaluate(dataset, [
        {
            "name": f"bounded_d{bounded_depth}",
            "fn": bounded_analyze,
            "options": {"max_depth": bounded_depth},
        },
        {
            "name": "cfg",
            "fn": cfg_analyze,
            "options": {"grammar": "english"},
        },
    ])

    output_dir = Path(results_dir) if results_dir is not None else RESULTS_DIR
    depths = list(range(min_depth, max_depth + 1))
    save_summary_csv(result["summary"], output_dir / "summary.csv", depths=depths)
    save_details_json(result["details"], output_dir / "details.json")
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python_version": platform.python_version(),
        "lark_version": _package_version("lark"),
        "depths": depths,
        "examples_per_label_per_depth": n_per_depth,
        "seed": seed,
        "bounded_max_depth": bounded_depth,
        "dataset_size": len(dataset),
        "label_counts": {
            label: sum(record["label"] == label for record in dataset)
            for label in ("correct", "incorrect")
        },
        "methods": [row["method"] for row in result["summary"]],
        "metrics_note": (
            "accuracy_by_depth is the fraction of positive (correct) examples accepted; "
            "the CSV also reports rejection counts for negative examples."
        ),
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result["metadata"] = metadata
    result["output_dir"] = output_dir
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-depth", type=int, default=0)
    parser.add_argument("--max-depth", type=int, default=4,
                        help="максимальная глубина примеров в наборе")
    parser.add_argument("--n-per-depth", type=int, default=20,
                        help="количество положительных и отрицательных примеров на глубину")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bounded-depth", type=int, default=1,
                        help="максимальная вложенность регулярной модели")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()

    result = run_experiment(
        min_depth=args.min_depth,
        max_depth=args.max_depth,
        n_per_depth=args.n_per_depth,
        seed=args.seed,
        bounded_depth=args.bounded_depth,
        results_dir=args.results_dir,
    )
    print(f"Сгенерировано примеров: {result['metadata']['dataset_size']}")
    for row in result["summary"]:
        accepted = f"{row['correct_accepted']}/{row['correct_total']}"
        rejected = f"{row['incorrect_rejected']}/{row['incorrect_total']}"
        print(f"{row['method']}: корректные приняты {accepted}; некорректные отклонены {rejected}")
    print(f"Результаты сохранены в: {result['output_dir']}")


if __name__ == "__main__":
    main()
