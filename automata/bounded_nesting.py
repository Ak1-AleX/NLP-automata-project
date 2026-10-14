"""Регулярная модель английского с явным лимитом глубины.

Для каждого max_depth генерируется регулярное выражение, описывающее
ровно те предложения, у которых глубина вложенности np не превышает
max_depth. Предложения глубже лимита регулярным выражением не
покрываются — это и есть демонстрация ограничения конечного автомата.
"""

import re
from time import perf_counter
from grammar.vocabulary import grammar_rule_vocabulary, unknown_symbol_error


def _rule_pattern(rule: str) -> str:
    """Build a regex alternation directly from the Lark rule's terminals."""
    alternatives = grammar_rule_vocabulary("english", rule)
    if not alternatives:
        raise ValueError(f"в грамматике english нет терминалов для правила {rule!r}")
    return "(?:" + "|".join(re.escape(word) for word in alternatives) + ")"


# Лексика регулярной модели извлекается из тех же Lark-правил, что и CFG.
DET = _rule_pattern("det")
N = _rule_pattern("n")
IV = _rule_pattern("iv")
V = _rule_pattern("v")
THAT = _rule_pattern("that")

# Кэш скомпилированных выражений по max_depth
_patterns: dict[int, re.Pattern] = {}
MAX_SUPPORTED_DEPTH = 64


def validate_max_depth(max_depth: int) -> None:
    """Reject invalid or impractically large regular-model depths."""
    if isinstance(max_depth, bool) or not isinstance(max_depth, int):
        raise TypeError("max_depth должен быть целым числом")
    if max_depth < 0:
        raise ValueError("max_depth не может быть отрицательным")
    if max_depth > MAX_SUPPORTED_DEPTH:
        raise ValueError(f"max_depth не может быть больше {MAX_SUPPORTED_DEPTH}")


def _build_pattern(max_depth: int) -> str:
    """Строит регулярное выражение для глубины вложенности <= max_depth.

    Глубина 0: Det N IV
    Глубина 1: Det N (that Det N V)? IV, где Det N — базовая np
    Глубина k: np строится рекурсивно до уровня k, затем финальный IV.
    """
    validate_max_depth(max_depth)

    # Базовая np (глубина 0): Det N
    np_regex = rf"{DET}\s+{N}"

    # На каждом уровне добавляем необязательное вложение. Предыдущий
    # шаблон встречается один раз, поэтому размер выражения растёт линейно.
    for _ in range(max_depth):
        np_regex = rf"{DET}\s+{N}(?:\s+{THAT}\s+{np_regex}\s+{V})?"

    # Внешний S: np + iv
    return rf"^\s*{np_regex}\s+{IV}\s*$"


def _get_pattern(max_depth: int) -> re.Pattern:
    if max_depth not in _patterns:
        regex = _build_pattern(max_depth)
        _patterns[max_depth] = re.compile(regex)
    return _patterns[max_depth]


def get_pattern(max_depth: int) -> str:
    """Возвращает строку регулярного выражения (для отчёта и визуализации)."""
    return _build_pattern(max_depth)


def count_depth(input_str: str) -> int:
    """Грубая оценка глубины вложенности по числу 'that' во входе.

    Не является разбором; используется для диагностики и экспериментов.
    """
    tokens = input_str.split()
    return tokens.count("that")


def analyze(input_str: str, max_depth: int = 2) -> dict:
    """Проверяет строку регулярной моделью с лимитом глубины max_depth.

    Возвращает dict по контракту из docs/api.md.
    """
    validate_max_depth(max_depth)

    started = perf_counter()
    pattern = _get_pattern(max_depth)
    tokens = input_str.split()
    match = pattern.match(input_str)
    accepted = match is not None

    # Вход за пределами словаря — ошибка входа, даже если regex также
    # отклонил бы его. Используется та же проверка словаря, что и у CFG.
    error = unknown_symbol_error(input_str, "english")

    return {
        "accepted": accepted,
        "method": "bounded",
        "input": input_str,
        "tokens": tokens,
        "trace": [],
        "parse_tree": None,
        "error": error,
        "elapsed_ms": (perf_counter() - started) * 1000,
    }
