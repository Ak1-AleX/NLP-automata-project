"""Сравнение анализаторов на одном наборе данных.

evaluate() возвращает результаты, не пишет на диск.
Сохранение — отдельные функции save_summary_csv и save_details_json.
"""

import csv
import json
from pathlib import Path
from collections import defaultdict


RESULTS_DIR = Path(__file__).parent / "results"


# --- Прогон одного метода по одному входу ---

def _run_method(analyzer_fn, options: dict, input_str: str) -> dict:
    """Вызывает анализатор, устойчиво к исключениям.

    Возвращает dict с полями accepted, error, elapsed_ms.
    """
    try:
        result = analyzer_fn(input_str, **options)
        return {
            "accepted": bool(result.get("accepted", False)),
            "error": result.get("error"),
            "elapsed_ms": float(result.get("elapsed_ms", 0.0)),
        }
    except Exception as e:
        return {
            "accepted": False,
            "error": f"{e.__class__.__name__}: {e}",
            "elapsed_ms": 0.0,
        }


# --- Основная функция ---

def evaluate(dataset: list[dict], methods: list[dict]) -> dict:
    """Прогоняет все методы на одном наборе.

    methods — список словарей:
    [
        {"name": "dfa",     "fn": dfa_analyze,     "options": {}},
        {"name": "bounded", "fn": bounded_analyze, "options": {"max_depth": 2}},
        {"name": "cfg",     "fn": parse,           "options": {"grammar": "english"}},
    ]

    Возвращает:
    {
        "summary": [
            {
                "method": str,
                "options": dict,
                "correct_accepted": int, "correct_total": int,
                "incorrect_rejected": int, "incorrect_total": int,
                "accuracy_by_depth": {depth: float, ...},
            },
            ...
        ],
        "details": [
            {
                "input": str, "depth": int, "label": str,
                "negative_type": str | None,
                "results": {method_name: {"accepted": bool, "error": str | None}},
            },
            ...
        ],
    }
    """
    details = []
    # по методу: счётчики и разбивка по глубинам
    stats = {
        m["name"]: {
            "correct_accepted": 0,
            "correct_total": 0,
            "incorrect_rejected": 0,
            "incorrect_total": 0,
            "by_depth_correct": defaultdict(int),
            "by_depth_correct_total": defaultdict(int),
        }
        for m in methods
    }

    for record in dataset:
        input_str = record["input"]
        label = record["label"]
        depth = record["depth"]

        record_results = {}
        for m in methods:
            run = _run_method(m["fn"], m.get("options", {}), input_str)
            record_results[m["name"]] = {
                "accepted": run["accepted"],
                "error": run["error"],
            }

            s = stats[m["name"]]
            if label == "correct":
                s["correct_total"] += 1
                s["by_depth_correct_total"][depth] += 1
                if run["accepted"]:
                    s["correct_accepted"] += 1
                    s["by_depth_correct"][depth] += 1
            else:  # incorrect
                s["incorrect_total"] += 1
                if not run["accepted"] and run["error"] is None:
                    s["incorrect_rejected"] += 1

        details.append({
            "input": input_str,
            "depth": depth,
            "label": label,
            "negative_type": record.get("negative_type"),
            "results": record_results,
        })

    summary = []
    for m in methods:
        s = stats[m["name"]]
        accuracy_by_depth = {}
        for depth, total in s["by_depth_correct_total"].items():
            accuracy_by_depth[depth] = (
                s["by_depth_correct"][depth] / total if total else 0.0
            )
        summary.append({
            "method": m["name"],
            "options": m.get("options", {}),
            "correct_accepted": s["correct_accepted"],
            "correct_total": s["correct_total"],
            "incorrect_rejected": s["incorrect_rejected"],
            "incorrect_total": s["incorrect_total"],
            "accuracy_by_depth": dict(sorted(accuracy_by_depth.items())),
        })

    return {"summary": summary, "details": details}


# --- Сохранение результатов ---

def save_summary_csv(
    summary: list[dict],
    path: Path | None = None,
    depths: list[int] | None = None,
) -> Path:
    """Сохраняет сводку в CSV. Возвращает путь к файлу.

    depths — явный список глубин для колонок. Если None — берётся
    из данных (только те, что реально встретились).
    """
    if path is None:
        path = RESULTS_DIR / "summary.csv"
    path.parent.mkdir(parents=True, exist_ok=True)

    if depths is None:
        dset = set()
        for row in summary:
            dset.update(row["accuracy_by_depth"].keys())
        depths = sorted(dset)

    fieldnames = [
        "method", "options",
        "correct_accepted", "correct_total",
        "incorrect_rejected", "incorrect_total",
    ] + [f"accuracy_depth_{d}" for d in depths]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary:
            out = {
                "method": row["method"],
                "options": json.dumps(row["options"], ensure_ascii=False),
                "correct_accepted": row["correct_accepted"],
                "correct_total": row["correct_total"],
                "incorrect_rejected": row["incorrect_rejected"],
                "incorrect_total": row["incorrect_total"],
            }
            for d in depths:
                out[f"accuracy_depth_{d}"] = row["accuracy_by_depth"].get(d, "")
            writer.writerow(out)

    return path

def save_details_json(details: list[dict], path: Path | None = None) -> Path:
    """Сохраняет построчные результаты в JSON. Возвращает путь к файлу."""
    if path is None:
        path = RESULTS_DIR / "details.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(details, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path