"""Построение Graphviz-диаграммы ДКА языка L1."""

from __future__ import annotations

import json


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
    visited_states = {"q0"}
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
        '  q0 [shape=doublecircle, label="q0\\nначальное, принимающее"];',
        '  q1 [shape=doublecircle, label="q1\\nпринимающее"];',
        '  q2 [shape=circle, label="q2\\nловушка", fillcolor="#FFF7ED"];',
        '  start -> q0 [color="#475569"];',
    ]
    for state in sorted(visited_states):
        if state in {"q0", "q1", "q2"}:
            lines.append(f'  {state} [fillcolor="#DBEAFE", color="#2563EB", penwidth=2.2];')

    transitions = [
        ("q0", "a", "q0"), ("q0", "b", "q1"),
        ("q1", "a", "q2"), ("q1", "b", "q1"),
        ("q2", "a", "q2"), ("q2", "b", "q2"),
    ]
    for source, symbol, target in transitions:
        attrs = [f'label={json.dumps(symbol)}']
        if (source, symbol, target) in used_edges:
            attrs.extend([f'color={json.dumps(path_color)}', 'fontcolor="' + path_color + '"', 'penwidth=2.8'])
        lines.append(f"  {source} -> {target} [{', '.join(attrs)}];")
    lines.append("}")
    return "\n".join(lines)
