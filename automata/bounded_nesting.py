"""Регулярная модель английского с явным лимитом глубины.

Для каждого max_depth генерируется регулярное выражение, описывающее
ровно те предложения, у которых глубина вложенности np не превышает
max_depth. Предложения глубже лимита регулярным выражением не
покрываются — это и есть демонстрация ограничения конечного автомата.
"""

import re
from time import perf_counter

# Терминалы — те же, что в docs/language_spec.md и grammar/english.lark
DET = r"(?:the|a)"
N = r"(?:cat|dog|boy|girl|man|woman|bird|child)"
IV = r"(?:ran|slept|smiled|waited|laughed)"
V = r"(?:saw|chased|heard|found|liked)"
THAT = r"that"

# Кэш скомпилированных выражений по max_depth
_patterns: dict[int, re.Pattern] = {}


def _build_pattern(max_depth: int) -> str:
    """Строит регулярное выражение для глубины вложенности <= max_depth.

    Глубина 0: Det N IV
    Глубина 1: Det N (that Det N V)? IV, где Det N — базовая np
    Глубина k: np строится рекурсивно до уровня k, затем финальный IV.
    """
    # Базовая np (глубина 0): Det N
    np_regex = rf"{DET}\s+{N}"

    # Наращиваем вложенность до нужного уровня
    for _ in range(max_depth):
        np_regex = rf"(?:{np_regex}|{DET}\s+{N}\s+{THAT}\s+{np_regex}\s+{V})"

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
    if isinstance(max_depth, bool) or not isinstance(max_depth, int):
        raise TypeError("max_depth должен быть целым числом")
    if max_depth < 0:
        raise ValueError("max_depth не может быть отрицательным")

    started = perf_counter()
    pattern = _get_pattern(max_depth)
    tokens = input_str.split()
    match = pattern.match(input_str)
    accepted = match is not None

    # Отличить «не принадлежит языку вообще» от «глубже лимита» можно
    # только по внешнему признаку — числу that. Это эвристика для отчёта,
    # а не часть формальной модели.
    depth_estimate = count_depth(input_str)
    error = None
    if not accepted and depth_estimate > max_depth:
        error = None  # это ожидаемое поведение модели, а не сбой

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
