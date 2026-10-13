"""Тесты для experiments/evaluate.py."""

import csv
import json
from pathlib import Path

import pytest

from experiments.evaluate import (
    evaluate,
    save_summary_csv,
    save_details_json,
    _run_method,
)
from automata.dfa import analyze as dfa_analyze
from automata.bounded_nesting import analyze as bounded_analyze
from grammar.parser import analyze as parse


# --- Вспомогательные анализаторы для тестов ---

def _always_accept(input_str, **options):
    return {"accepted": True, "error": None, "elapsed_ms": 0.0}


def _always_reject(input_str, **options):
    return {"accepted": False, "error": None, "elapsed_ms": 0.0}


def _raises(input_str, **options):
    raise RuntimeError("boom")


# --- Маленький тестовый датасет ---

SAMPLE_DATASET = [
    {"input": "the cat ran", "depth": 0, "label": "correct", "negative_type": None},
    {"input": "the cat that the dog chased ran", "depth": 1, "label": "correct", "negative_type": None},
    {"input": "the cat that the dog that the boy saw chased ran", "depth": 2, "label": "correct", "negative_type": None},
    {"input": "cat the ran", "depth": 0, "label": "incorrect", "negative_type": "word_order"},
    {"input": "the cat", "depth": 0, "label": "incorrect", "negative_type": "missing_iv"},
]


# --- _run_method ---

def test_run_method_wraps_success():
    out = _run_method(_always_accept, {}, "anything")
    assert out["accepted"] is True
    assert out["error"] is None


def test_run_method_wraps_exception():
    out = _run_method(_raises, {}, "anything")
    assert out["accepted"] is False
    assert "RuntimeError" in out["error"]
    assert "boom" in out["error"]


# --- evaluate: формат ответа ---

def test_evaluate_returns_summary_and_details():
    result = evaluate(SAMPLE_DATASET, [
        {"name": "always_accept", "fn": _always_accept, "options": {}},
    ])
    assert "summary" in result
    assert "details" in result
    assert len(result["summary"]) == 1
    assert len(result["details"]) == len(SAMPLE_DATASET)


def test_evaluate_summary_fields():
    result = evaluate(SAMPLE_DATASET, [
        {"name": "always_accept", "fn": _always_accept, "options": {}},
    ])
    row = result["summary"][0]
    expected_keys = {
        "method", "options",
        "correct_accepted", "correct_total",
        "incorrect_rejected", "incorrect_total",
        "accuracy_by_depth",
    }
    assert set(row.keys()) == expected_keys


# --- evaluate: счётчики ---

def test_evaluate_always_accept_counters():
    result = evaluate(SAMPLE_DATASET, [
        {"name": "always_accept", "fn": _always_accept, "options": {}},
    ])
    row = result["summary"][0]
    assert row["correct_total"] == 3
    assert row["correct_accepted"] == 3
    assert row["incorrect_total"] == 2
    assert row["incorrect_rejected"] == 0


def test_evaluate_always_reject_counters():
    result = evaluate(SAMPLE_DATASET, [
        {"name": "always_reject", "fn": _always_reject, "options": {}},
    ])
    row = result["summary"][0]
    assert row["correct_accepted"] == 0
    assert row["incorrect_rejected"] == 2


def test_evaluate_accuracy_by_depth():
    result = evaluate(SAMPLE_DATASET, [
        {"name": "always_accept", "fn": _always_accept, "options": {}},
    ])
    acc = result["summary"][0]["accuracy_by_depth"]
    # только глубины с корректными записями
    assert acc[0] == 1.0
    assert acc[1] == 1.0
    assert acc[2] == 1.0


# --- evaluate: детали ---

def test_evaluate_details_shape():
    result = evaluate(SAMPLE_DATASET, [
        {"name": "always_accept", "fn": _always_accept, "options": {}},
    ])
    detail = result["details"][0]
    expected_keys = {"input", "depth", "label", "negative_type", "results"}
    assert set(detail.keys()) == expected_keys
    assert "always_accept" in detail["results"]
    assert detail["results"]["always_accept"]["accepted"] is True


# --- evaluate: несколько методов ---

def test_evaluate_multiple_methods():
    result = evaluate(SAMPLE_DATASET, [
        {"name": "accept", "fn": _always_accept, "options": {}},
        {"name": "reject", "fn": _always_reject, "options": {}},
    ])
    names = [row["method"] for row in result["summary"]]
    assert names == ["accept", "reject"]

    d = result["details"][0]
    assert "accept" in d["results"]
    assert "reject" in d["results"]


# --- evaluate: настоящие модели ---

def test_evaluate_bounded_vs_cfg():
    """Проверка на реальных данных: bounded_d1 принимает до глубины 1,
    cfg — до любой доступной."""
    dataset = [
        {"input": "the cat ran", "depth": 0, "label": "correct", "negative_type": None},
        {"input": "the cat that the dog chased ran", "depth": 1, "label": "correct", "negative_type": None},
        {"input": "the cat that the dog that the boy saw chased ran", "depth": 2, "label": "correct", "negative_type": None},
    ]
    result = evaluate(dataset, [
        {"name": "bounded_d1", "fn": bounded_analyze, "options": {"max_depth": 1}},
        {"name": "cfg",        "fn": parse,           "options": {"grammar": "english"}},
    ])

    summary = {row["method"]: row for row in result["summary"]}
    assert summary["bounded_d1"]["accuracy_by_depth"][0] == 1.0
    assert summary["bounded_d1"]["accuracy_by_depth"][1] == 1.0
    assert summary["bounded_d1"]["accuracy_by_depth"][2] == 0.0
    assert summary["cfg"]["accuracy_by_depth"][0] == 1.0
    assert summary["cfg"]["accuracy_by_depth"][1] == 1.0
    assert summary["cfg"]["accuracy_by_depth"][2] == 1.0


def test_cfg_syntax_rejection_counts_but_unknown_word_is_input_error():
    dataset = [
        {"input": "the cat ran", "depth": 0, "label": "correct", "negative_type": None},
        {"input": "the cat the ran", "depth": 0, "label": "incorrect", "negative_type": "extra_det"},
        {"input": "the cat fly", "depth": 0, "label": "incorrect", "negative_type": "unknown_token"},
    ]
    result = evaluate(dataset, [
        {"name": "cfg", "fn": parse, "options": {"grammar": "english"}},
    ])
    row = result["summary"][0]
    assert row["incorrect_rejected"] == 1
    assert row["incorrect_total"] == 2


# --- evaluate: устойчивость к исключениям ---

def test_evaluate_handles_exception_gracefully():
    result = evaluate(SAMPLE_DATASET, [
        {"name": "boom", "fn": _raises, "options": {}},
    ])
    row = result["summary"][0]
    # все вызовы упали — ничего не принято
    assert row["correct_accepted"] == 0
    # и ни одно некорректное не отклонено
    assert row["incorrect_rejected"] == 0
    # детали содержат текст ошибки
    assert "RuntimeError" in result["details"][0]["results"]["boom"]["error"]


# --- Сохранение: summary ---

def test_save_summary_csv(tmp_path):
    summary = [
        {
            "method": "cfg", "options": {"grammar": "english"},
            "correct_accepted": 3, "correct_total": 3,
            "incorrect_rejected": 2, "incorrect_total": 2,
            "accuracy_by_depth": {0: 1.0, 1: 1.0, 2: 1.0},
        },
        {
            "method": "bounded", "options": {"max_depth": 1},
            "correct_accepted": 2, "correct_total": 3,
            "incorrect_rejected": 2, "incorrect_total": 2,
            "accuracy_by_depth": {0: 1.0, 1: 1.0, 2: 0.0},
        },
    ]
    path = tmp_path / "summary.csv"
    out = save_summary_csv(summary, path)
    assert out == path
    assert path.exists()

    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 2
    assert rows[0]["method"] == "cfg"
    assert rows[1]["method"] == "bounded"
    # колонки по глубинам присутствуют
    assert "accuracy_depth_0" in rows[0]
    assert "accuracy_depth_1" in rows[0]
    assert "accuracy_depth_2" in rows[0]


def test_save_summary_csv_handles_missing_depth(tmp_path):
    """Если метод не имеет данных по какой-то глубине — колонка пустая."""
    summary = [
        {
            "method": "bounded", "options": {"max_depth": 0},
            "correct_accepted": 1, "correct_total": 1,
            "incorrect_rejected": 1, "incorrect_total": 1,
            "accuracy_by_depth": {0: 1.0},   # нет ключа 1 и 2
        },
    ]
    path = tmp_path / "s.csv"
    save_summary_csv(summary, path, depths=[0, 1, 2])
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["accuracy_depth_0"] == "1.0"
    assert rows[0]["accuracy_depth_1"] == ""
    assert rows[0]["accuracy_depth_2"] == ""


# --- Сохранение: details ---

def test_save_details_json(tmp_path):
    details = [
        {
            "input": "the cat ran", "depth": 0, "label": "correct",
            "negative_type": None,
            "results": {"cfg": {"accepted": True, "error": None}},
        },
        {
            "input": "cat the ran", "depth": 0, "label": "incorrect",
            "negative_type": "word_order",
            "results": {"cfg": {"accepted": False, "error": "..."}},
        },
    ]
    path = tmp_path / "details.json"
    out = save_details_json(details, path)
    assert out == path
    assert path.exists()

    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == details


def test_save_details_json_preserves_unicode(tmp_path):
    details = [
        {
            "input": "the cat ran", "depth": 0, "label": "correct",
            "negative_type": None,
            "results": {"cfg": {"accepted": True, "error": "ошибка"}},
        },
    ]
    path = tmp_path / "d.json"
    save_details_json(details, path)
    text = path.read_text(encoding="utf-8")
    assert "ошибка" in text
