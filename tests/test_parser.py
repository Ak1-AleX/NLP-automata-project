"""Тесты для grammar/parser.py (CFG-парсер на Lark)."""

import pytest

from grammar.parser import analyze


# --- Английская грамматика: принимаемые предложения ---

@pytest.mark.parametrize("sentence", [
    # глубина 0
    "the cat ran",
    "a dog slept",
    "the boy smiled",
    "the girl waited",
    "a bird laughed",
    # глубина 1
    "the cat that the dog chased ran",
    "a boy that the girl saw waited",
    "the bird that the man heard laughed",
    # глубина 2
    "the cat that the dog that the boy saw chased ran",
    "a girl that the man that the woman found liked slept",
])
def test_english_accepts_valid(sentence):
    result = analyze(sentence, grammar="english")
    assert result["accepted"] is True
    assert result["error"] is None
    assert result["parse_tree"] is not None


# --- Английская грамматика: отклоняемые предложения ---

@pytest.mark.parametrize("sentence", [
    "cat the ran",                     # порядок слов
    "the cat",                         # нет iv
    "the cat the ran",                 # лишний детерминатив
    "the cat that the dog chased",     # незакрытая вложенность
    "the cat fly",                     # неизвестный токен
    "the cat that dog chased ran",     # пропущен det перед dog
    "the ran cat",                     # перестановка
    "The cat ran",                     # регистр не совпадает
])
def test_english_rejects_invalid(sentence):
    result = analyze(sentence, grammar="english")
    assert result["accepted"] is False


# --- anbn: принимаемые строки ---

@pytest.mark.parametrize("input_str", [
    "",
    "ab",
    "aabb",
    "aaabbb",
    "aaaabbbb",
])
def test_anbn_accepts_valid(input_str):
    result = analyze(input_str, grammar="anbn")
    assert result["accepted"] is True
    assert result["error"] is None


# --- anbn: отклоняемые строки ---

@pytest.mark.parametrize("input_str", [
    "aaabb",
    "aabbb",
    "abab",
    "ba",
    "a",
    "b",
    "a a b b",  # пробелы не входят в алфавит L2
])
def test_anbn_rejects_invalid(input_str):
    result = analyze(input_str, grammar="anbn")
    assert result["accepted"] is False


# --- Формат ответа ---

def test_response_format_english():
    result = analyze("the cat ran", grammar="english")
    expected_keys = {
        "accepted", "method", "input", "tokens",
        "trace", "parse_tree", "error", "elapsed_ms",
    }
    assert set(result.keys()) == expected_keys
    assert result["method"] == "cfg"
    assert result["input"] == "the cat ran"
    assert result["tokens"] == ["the", "cat", "ran"]
    assert result["trace"] == []


def test_response_format_anbn():
    result = analyze("aabb", grammar="anbn")
    assert result["method"] == "cfg"
    assert result["input"] == "aabb"
    assert result["tokens"] == ["aabb"]   # split() не делит внутри слова
    assert result["trace"] == []


# --- Дерево разбора ---

def test_parse_tree_is_sexpr():
    result = analyze("the cat ran", grammar="english")
    tree = result["parse_tree"]
    assert tree.startswith("(s ")
    assert tree.endswith(")")
    assert "np" in tree
    assert "iv" in tree


def test_parse_tree_contains_that():
    result = analyze("the cat that the dog chased ran", grammar="english")
    tree = result["parse_tree"]
    assert "(that that)" in tree


def test_parse_tree_nested_np():
    result = analyze(
        "the cat that the dog that the boy saw chased ran",
        grammar="english",
    )
    tree = result["parse_tree"]
    # три вложенных np на глубине 2
    assert tree.count("(np ") == 3


def test_parse_tree_none_on_reject():
    result = analyze("the cat the ran", grammar="english")
    assert result["parse_tree"] is None


# --- Ошибки ---

def test_known_word_syntax_rejection_has_no_error():
    result = analyze("the cat the ran", grammar="english")
    assert result["accepted"] is False
    assert result["error"] is None


def test_unknown_word_returns_error():
    result = analyze("the cat fly", grammar="english")
    assert result["accepted"] is False
    assert result["error"] == "неизвестное слово: 'fly'"


def test_unknown_grammar_returns_error():
    result = analyze("the cat ran", grammar="french")
    assert result["accepted"] is False
    assert result["error"] is not None


# --- Кэш парсеров ---

def test_parser_is_cached():
    """Повторные вызовы не должны пересобирать парсер."""
    from grammar import parser as parser_module
    # прогреваем кэш
    analyze("the cat ran", grammar="english")
    assert "english" in parser_module._parsers
    first = parser_module._parsers["english"]
    analyze("a dog slept", grammar="english")
    second = parser_module._parsers["english"]
    assert first is second
