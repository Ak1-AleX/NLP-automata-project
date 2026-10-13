"""Построение Graphviz-диаграммы ДКА языка L1."""

from __future__ import annotations

import json

from automata.dfa import ACCEPT_STATES, START_STATE, TRANSITIONS


# Пояснительные подписи для узлов диаграммы. Это интерфейсный текст,
# а не часть формальной модели, поэтому хранится здесь, а не в dfa.py.
_STATE_LABELS = {
    "q0": "q0\\nначальное, принимающее",
    "q1": "q1\\nпринимающее",
    "q2": "q2\\nловушка",
}

_TRAP_STATES = {"q2"}


def _all_states() -> set[str]:
    """Все состояния, встречающиеся в таблице переходов и как стартовые/принимающие."""
    states = {START_STATE} | set(ACCEPT_STATES)
    for source, _ in TRANSITIONS:
        states.add(source)
    for _, target in TRANSITIONS:
        states.add(target)
    return states


def automaton_to_dot(trace: list[dict] | None = None, accepted: bool | None = None) -> str:
    """Возвращает DOT-код ДКА L1, подсвечивая пройденный путь при наличии.

    Диаграмма описывает весь автомат, а не только переходы конкретного запуска.
    Визуальный рендер выполняет Streamlit; локальный исполняемый файл Graphviz
    для этой функции не требуется.
    """
    trace = trace or []
    used_edges = {
        (step.get("state"), step.get("symbol"), step.get("next_state"))
        for step in trace
        if step.get("symbol") is not None
    }
    visited_states = {START_STATE}
    visited_states.update(
        step.get("next_state") for step in trace if step.get("next_state")
    )
    path_color = "#15803D" if accepted else "#B91C1C"

    lines = [
        "digraph DFA {",
        '  graph [rankdir=LR, bgcolor="transparent", pad="0.25", nodesep="0.65", ranksep="0.8"];',
        '  node [fontname="Arial", fontsize=12, style="filled", fillcolor="#F8FAFC", color="#475569", fontcolor="#0F172A", penwidth=1.4];',
        '  edge [fontname="Arial", fontsize=11, color="#64748B", fontcolor="#334155", arrowsize=0.8];',
        '  start [shape=point, width=0.12, label="", color="#475569"];',
        f'  start -> {START_STATE} [color="#475569"];',
    ]

    for state in sorted(_all_states()):
        shape = "doublecircle" if state in ACCEPT_STATES else "circle"
        label = _STATE_LABELS.get(state, state)
        attrs = [f"shape={shape}", f"label={json.dumps(label)}"]
        if state in _TRAP_STATES:
            attrs.append('fillcolor="#FFF7ED"')
        lines.append(f'  {state} [{", ".join(attrs)}];')

    for state in sorted(visited_states):
        if state in _all_states():
            lines.append(
                f'  {state} [fillcolor="#DBEAFE", color="#2563EB", penwidth=2.2];'
            )

    for (source, symbol), target in sorted(TRANSITIONS.items()):
        attrs = [f'label={json.dumps(symbol)}']
        if (source, symbol, target) in used_edges:
            attrs.extend([
                f'color={json.dumps(path_color)}',
                f'fontcolor={json.dumps(path_color)}',
                'penwidth=2.8',
            ])
        lines.append(f"  {source} -> {target} [{', '.join(attrs)}];")

    lines.append("}")
    return "\n".join(lines)