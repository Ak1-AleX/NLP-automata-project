"""Shared literal-terminal helpers for the project's grammars."""

import re
from functools import lru_cache
from pathlib import Path


GRAMMAR_DIR = Path(__file__).parent
GRAMMAR_FILES = {
    "english": GRAMMAR_DIR / "english.lark",
    "anbn": GRAMMAR_DIR / "anbn.lark",
}


@lru_cache(maxsize=None)
def grammar_vocabulary(grammar: str) -> frozenset[str]:
    """Return literal terminals from a project's grammar file."""
    path = GRAMMAR_FILES.get(grammar)
    if path is None:
        return frozenset()
    text = _grammar_source(path)
    return frozenset(re.findall(r'"([^"\\]+)"', text))


@lru_cache(maxsize=None)
def grammar_rule_vocabulary(grammar: str, rule: str) -> tuple[str, ...]:
    """Return the literal alternatives declared directly by one grammar rule."""
    path = GRAMMAR_FILES.get(grammar)
    if path is None:
        return ()
    for line in _grammar_source(path).splitlines():
        match = re.match(rf"\s*{re.escape(rule)}\s*:\s*(.*)$", line)
        if match:
            return tuple(re.findall(r'"([^"\\]+)"', match.group(1)))
    return ()


def _grammar_source(path: Path) -> str:
    """Read grammar source without full-line comments."""
    text = path.read_text(encoding="utf-8")
    return "\n".join(
        line for line in text.splitlines()
        if not line.lstrip().startswith("//")
    )


def unknown_symbol_error(input_str: str, grammar: str) -> str | None:
    """Return a consistent input-vocabulary error for a grammar's alphabet."""
    if grammar not in GRAMMAR_FILES:
        return None

    vocabulary = grammar_vocabulary(grammar)
    if grammar == "anbn":
        unknown = next((symbol for symbol in input_str if symbol not in vocabulary), None)
        if unknown is not None:
            return f"символ {unknown!r} не входит в алфавит {{a, b}}"
    else:
        unknown = next((token for token in input_str.split() if token not in vocabulary), None)
        if unknown is not None:
            return f"неизвестное слово: {unknown!r}"
    return None
