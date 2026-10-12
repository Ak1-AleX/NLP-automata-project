"""Тесты для automata/bounded_nesting.py (регулярная модель с лимитом глубины)."""

import pytest

from automata.bounded_nesting import (
    analyze,
    get_pattern,
    count_depth,
    _patterns,
)


# --- Предложения разной глубины (раздел 3.4 спецификации) ---

DEPTH_0 = [
    "the cat ran",
    "a dog slept",
    "the boy smiled",
    "the girl waited",
    "a bird laughed",
]

DEPTH_1 = [
    "the cat that the dog chased ran",
    "a boy that the girl saw waited",
    "the bird that the man heard laughed",
]

DEPTH_2 = [
    "the cat that the dog that the boy saw chased ran",
    "a girl that the man that the woman found liked slept",
]


# --- max_depth = 0: принимает только глубину 0 ---

@pytest.mark.parametrize("sentence", DEPTH_0)
def test_depth0_accepts_depth0(sentence):
    result = analyze(sentence, max_depth=0)
    assert result["accepted"] is True


@pytest.mark.parametrize("sentence", DEPTH_1 + DEPTH_2)
def test_depth0_rejects_deeper(sentence):
    result = analyze(sentence, max_depth=0)
    assert result["accepted"] is False
    assert result["error"] is None


# --- max_depth = 1: принимает глубину 0 и 1 ---

@pytest.mark.parametrize("sentence", DEPTH_0 + DEPTH_1)
def test_depth1_accepts_up_to_1(sentence):
    result = analyze(sentence, max_depth=1)
    assert result["accepted"] is True


@pytest.mark.parametrize("sentence", DEPTH_2)
def test_depth1_rejects_depth2(sentence):
    result = analyze(sentence, max_depth=1)
    assert result["accepted"] is False


# --- max_depth = 2: принимает глубину 0, 1, 2 ---

@pytest.mark.parametrize("sentence", DEPTH_0 + DEPTH_1 + DEPTH_2)
def test_depth2_accepts_up_to_2(sentence):
    result = analyze(sentence, max_depth=2)
    assert result["accepted"] is True


# --- Некорректные строки отклоняются при любом лимите ---

@pytest.mark.parametrize("sentence", [
    "cat the ran",
    "the cat",
    "the cat the ran",
    "the cat that the dog chased",
    "the cat fly",
    "the cat that dog chased ran",
    "the ran cat",
])
@pytest.mark.parametrize("max_depth", [0, 1, 2, 3])
def test_rejects_invalid_regardless_of_depth(sentence, max_depth):
    result = analyze(sentence, max_depth=max_depth)
    assert result["accepted"] is False


# --- Рост покрытия с ростом max_depth ---

def test_coverage_grows_with_max_depth():
    depth2_sentence = DEPTH_2[0]

    assert analyze(depth2_sentence, max_depth=0)["accepted"] is False
    assert analyze(depth2_sentence, max_depth=1)["accepted"] is False
    assert analyze(depth2_sentence, max_depth=2)["accepted"] is True
    assert analyze(depth2_sentence, max_depth=3)["accepted"] is True


# --- Формат ответа (контракт из docs/api.md) ---

def test_response_format():
    result = analyze("the cat ran", max_depth=0)
    expected_keys = {
        "accepted", "method", "input", "tokens",
        "trace", "parse_tree", "error", "elapsed_ms",
    }
    assert set(result.keys()) == expected_keys
    assert result["method"] == "bounded"
    assert result["input"] == "the cat ran"
    assert result["tokens"] == ["the", "cat", "ran"]
    assert result["trace"] == []
    assert result["parse_tree"] is None


# --- count_depth ---

@pytest.mark.parametrize("sentence,expected", [
    ("the cat ran", 0),
    ("the cat that the dog chased ran", 1),
    ("the cat that the dog that the boy saw chased ran", 2),
])
def test_count_depth(sentence, expected):
    assert count_depth(sentence) == expected


# --- get_pattern ---

def test_get_pattern_depth0():
    pattern = get_pattern(0)
    # для глубины 0 не должно быть "that" в шаблоне
    assert "that" not in pattern


def test_get_pattern_depth1_contains_that():
    pattern = get_pattern(1)
    assert "that" in pattern


def test_get_pattern_grows_with_depth():
    p0 = get_pattern(0)
    p1 = get_pattern(1)
    p2 = get_pattern(2)
    assert len(p0) < len(p1) < len(p2)


# --- Кэш регулярок ---

def test_pattern_is_cached():
    _patterns.clear()
    analyze("the cat ran", max_depth=1)
    assert 1 in _patterns
    first = _patterns[1]
    analyze("a dog slept", max_depth=1)
    second = _patterns[1]
    assert first is second