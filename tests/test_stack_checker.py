"""Тесты для automata/stack_checker.py (стековый алгоритм для L2 = a^n b^n)."""

import pytest

from automata.stack_checker import analyze, ALPHABET


# --- Принимаемые строки (раздел 2.2 спецификации) ---

@pytest.mark.parametrize("input_str", [
    "",         # eps, n = 0
    "ab",       # n = 1
    "aabb",     # n = 2
    "aaabbb",   # n = 3
    "aaaabbbb", # n = 4
])
def test_accepts_valid_strings(input_str):
    result = analyze(input_str)
    assert result["accepted"] is True
    assert result["error"] is None


# --- Отклоняемые строки ---

@pytest.mark.parametrize("input_str", [
    "aaabb",    # 3 и 2
    "aabbb",    # 2 и 3
    "abab",     # нарушен порядок
    "ba",       # b раньше a
    "b",        # только b
    "a",        # только a
    "aab",      # стек не пуст
    "abb",      # b при пустом стеке
])
def test_rejects_invalid_strings(input_str):
    result = analyze(input_str)
    assert result["accepted"] is False
    assert result["error"] is None


# --- Некорректный алфавит ---

@pytest.mark.parametrize("input_str", [
    "abc",
    "c",
    "a1b",
    "a b",
])
def test_unknown_symbol_returns_error(input_str):
    result = analyze(input_str)
    assert result["accepted"] is False
    assert result["error"] is not None


# --- Формат ответа (контракт из docs/api.md) ---

def test_response_format():
    result = analyze("aabb")
    expected_keys = {
        "accepted", "method", "input", "tokens",
        "trace", "parse_tree", "error", "elapsed_ms",
    }
    assert set(result.keys()) == expected_keys
    assert result["method"] == "stack"
    assert result["input"] == "aabb"
    assert result["tokens"] == []
    assert result["parse_tree"] is None


# --- Трассировка ---

def test_trace_length_on_accept():
    for input_str in ["", "ab", "aabb", "aaabbb"]:
        result = analyze(input_str)
        assert len(result["trace"]) == len(input_str)


def test_trace_length_on_reject():
    # трассировка обрывается на моменте отклонения
    result = analyze("abab")
    assert len(result["trace"]) == 3   # a, b, a (reject)


def test_trace_push_and_pop():
    result = analyze("aabb")
    actions = [step["action"] for step in result["trace"]]
    assert actions == ["push", "push", "pop", "pop"]


def test_trace_stack_states():
    result = analyze("aabb")
    stacks = [step["stack"] for step in result["trace"]]
    assert stacks == [
        ["a"],
        ["a", "a"],
        ["a"],
        [],
    ]


def test_trace_reject_on_a_after_b():
    result = analyze("abab")
    last = result["trace"][-1]
    assert last["action"] == "reject"
    assert last["symbol"] == "a"


def test_trace_reject_on_b_with_empty_stack():
    result = analyze("abb")
    last = result["trace"][-1]
    assert last["action"] == "reject"
    assert last["symbol"] == "b"


def test_trace_stops_at_unknown_symbol():
    result = analyze("ab c")
    symbols = [step["symbol"] for step in result["trace"]]
    assert "c" not in symbols
    assert result["error"] is not None


# --- Согласованность ---

def test_trace_stacks_are_independent_copies():
    # изменения стека в трассировке не должны влиять друг на друга
    result = analyze("aaabbb")
    stacks = [step["stack"] for step in result["trace"]]
    # каждый следующий снапшот независим от предыдущего
    assert stacks[0] != stacks[-1]
    assert len(stacks[0]) == 1
    assert len(stacks[-1]) == 0