"""Обёртка над Lark: проверка принадлежности и дерево разбора."""

from time import perf_counter
from lark import Lark, Tree, Token
from lark.exceptions import UnexpectedInput
from grammar.vocabulary import GRAMMAR_FILES, unknown_symbol_error

_parsers = {}


def _get_parser(grammar: str) -> Lark:
    if grammar not in GRAMMAR_FILES:
        raise ValueError(f"неизвестная грамматика: {grammar!r}")
    if grammar not in _parsers:
        text = GRAMMAR_FILES[grammar].read_text(encoding="utf-8")
        _parsers[grammar] = Lark(text, start="start", parser="earley", keep_all_tokens=True)
    return _parsers[grammar]


def _to_sexpr(node) -> str:
    """Преобразует дерево Lark в скобочную нотацию.

    Терминалы вида Tree('det', [Token('the')]) сворачиваются в (det the).
    """
    if isinstance(node, Tree):
        children = node.children
        # терминал: один ребёнок-Token — сворачиваем в (имя значение)
        if len(children) == 1 and isinstance(children[0], Token):
            return f"({node.data} {children[0]})"
        parts = " ".join(_to_sexpr(child) for child in children)
        return f"({node.data} {parts})" if parts else f"({node.data})"
    if isinstance(node, Token):
        return str(node)
    return str(node)


def _tokenize(input_str: str) -> list[str]:
    return input_str.split()


def analyze(input_str: str, grammar: str = "english") -> dict:
    """Проверяет строку на принадлежность языку грамматики.

    Возвращает dict по контракту из docs/api.md.
    """
    started = perf_counter()
    tokens = _tokenize(input_str)
    error = None
    parse_tree = None
    accepted = False

    try:
        parser = _get_parser(grammar)
        tree = parser.parse(input_str)
        if isinstance(tree, Tree) and tree.data == "start" and len(tree.children) == 1:
            tree = tree.children[0]
        parse_tree = _to_sexpr(tree)
        accepted = True
    except UnexpectedInput:
        # A syntax mismatch over known terminals is an ordinary language
        # rejection. Reserve ``error`` for symbols outside the grammar's
        # alphabet so evaluation can distinguish rejection from bad input.
        error = unknown_symbol_error(input_str, grammar)
    except ValueError as e:
        error = str(e)

    return {
        "accepted": accepted,
        "method": "cfg",
        "input": input_str,
        "tokens": tokens,
        "trace": [],
        "parse_tree": parse_tree,
        "error": error,
        "elapsed_ms": (perf_counter() - started) * 1000,
    }
