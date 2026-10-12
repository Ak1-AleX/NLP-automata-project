"""Тесты для automata/dfa.py (ДКА языка L1 = a^m b^n)."""

import pytest

from automata.dfa import analyze, ALPHABET, TRANSITIONS, START_STATE, ACCEPT_STATES


# --- Принимаемые строки (раздел 1.2 спецификации) ---

@pytest.mark.parametrize("input_str", [
    "",        # eps
    "a",
    "b",
    "ab",
    "aabb",
    "aaab",
    "abb",
    "aaabbb",
    "bbbbb",
    "aaaa",
])
def test_accepts_valid_strings(input_str):
    result = analyze(input_str)
    assert result["accepted"] is True
    assert result["error"] is None


# --- Отклоняемые строки ---

@pytest.mark.parametrize("input_str", [
    "ba",
    "abab",
    "aabba",
    "baa",
    "bbaa",
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
    assert result["method"] == "dfa"
    assert result["input"] == "aabb"
    assert result["tokens"] == []
    assert result["parse_tree"] is None


# --- Трассировка ---

def test_trace_starts_at_start_state():
    result = analyze("ab")
    first_step = result["trace"][0]
    assert first_step["step"] == 0
    assert first_step["state"] == START_STATE
    assert first_step["symbol"] is None


def test_trace_length():
    # шаг 0 + по одному шагу на символ
    for input_str in ["", "a", "ab", "aabb"]:
        result = analyze(input_str)
        assert len(result["trace"]) == len(input_str) + 1


def test_trace_for_simple_accept():
    result = analyze("ab")
    states = [step["next_state"] for step in result["trace"]]
    assert states == ["q0", "q0", "q1"]


def test_trace_enters_trap_on_bad_order():
    result = analyze("ba")
    states = [step["next_state"] for step in result["trace"]]
    assert states == ["q0", "q1", "q2"]


def test_trace_stops_at_unknown_symbol():
    result = analyze("ab c")
    # трассировка содержит только шаги до ошибки
    symbols = [step["symbol"] for step in result["trace"] if step["symbol"] is not None]
    assert "c" not in symbols
    assert result["error"] is not None


# --- Согласованность с таблицей переходов ---

def test_all_transitions_lead_to_known_states():
    known_states = {START_STATE} | ACCEPT_STATES | {"q2"}
    for (state, symbol), next_state in TRANSITIONS.items():
        assert state in known_states
        assert next_state in known_states
        assert symbol in ALPHABET


def test_start_state_is_accepting():
    assert START_STATE in ACCEPT_STATES