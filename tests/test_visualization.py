"""Проверки преобразования моделей и деревьев разбора в DOT."""

import pytest

from visualization.automaton import automaton_to_dot
from visualization.parse_tree import parse_tree_to_dot


def test_dfa_diagram_contains_states_and_transitions():
    dot = automaton_to_dot()
    assert 'q0 [shape=doublecircle' in dot
    assert 'q1 [shape=doublecircle' in dot
    assert 'q2 [shape=circle' in dot
    assert 'q0 -> q1 [label="b"]' in dot


def test_dfa_diagram_highlights_run():
    trace = [
        {"state": "q0", "symbol": "a", "next_state": "q0"},
        {"state": "q0", "symbol": "b", "next_state": "q1"},
    ]
    dot = automaton_to_dot(trace, accepted=True)
    assert dot.count("#15803D") == 4


def test_parse_tree_dot_contains_nonterminal_and_terminal_labels():
    dot = parse_tree_to_dot("(s (np (det the) (n cat)) (iv ran))")
    assert 'label="s"' in dot
    assert 'label="np"' in dot
    assert 'label="the"' in dot
    assert 'label="ran"' in dot


@pytest.mark.parametrize("expression", ["", "(s (np the)", "(s) trailing"])
def test_parse_tree_dot_rejects_malformed_expressions(expression):
    with pytest.raises(ValueError):
        parse_tree_to_dot(expression)
