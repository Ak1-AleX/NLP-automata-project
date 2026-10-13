"""Преобразование скобочного дерева разбора в Graphviz DOT."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


@dataclass
class _Node:
    label: str
    children: list[_Node | str] = field(default_factory=list)


def _parse_sexpr(expression: str) -> _Node:
    tokens = re.findall(r"\(|\)|[^()\s]+", expression)
    position = 0

    def parse_node() -> _Node:
        nonlocal position
        if position >= len(tokens) or tokens[position] != "(":
            raise ValueError("ожидалось начало узла '('")
        position += 1
        if position >= len(tokens) or tokens[position] in {"(", ")"}:
            raise ValueError("у узла должно быть имя")
        node = _Node(tokens[position])
        position += 1

        while position < len(tokens) and tokens[position] != ")":
            if tokens[position] == "(":
                node.children.append(parse_node())
            else:
                node.children.append(tokens[position])
                position += 1
        if position >= len(tokens):
            raise ValueError("не закрыта скобка дерева разбора")
        position += 1
        return node

    root = parse_node()
    if position != len(tokens):
        raise ValueError("после дерева разбора остались лишние данные")
    return root


def parse_tree_to_dot(expression: str) -> str:
    """Преобразует S-выражение из ``grammar.parser.analyze`` в дерево DOT."""
    if not expression or not expression.strip():
        raise ValueError("дерево разбора не должно быть пустым")

    root = _parse_sexpr(expression)
    lines = [
        "digraph ParseTree {",
        '  graph [rankdir=TB, bgcolor="transparent", pad="0.2", nodesep="0.25", ranksep="0.45"];',
        '  node [shape=box, style="rounded,filled", fillcolor="#EFF6FF", color="#93C5FD", fontname="Arial", fontsize=11, fontcolor="#0F172A", margin="0.10,0.06"];',
        '  edge [color="#64748B", arrowsize=0.65];',
    ]
    next_id = 0

    def add(node: _Node | str, parent_id: str | None = None) -> None:
        nonlocal next_id
        node_id = f"n{next_id}"
        next_id += 1
        label = node.label if isinstance(node, _Node) else node
        attrs = [f"label={json.dumps(label, ensure_ascii=False)}"]
        if isinstance(node, str):
            attrs.extend(['shape=ellipse', 'fillcolor="#F8FAFC"', 'color="#CBD5E1"'])
        lines.append(f"  {node_id} [{', '.join(attrs)}];")
        if parent_id is not None:
            lines.append(f"  {parent_id} -> {node_id};")
        if isinstance(node, _Node):
            for child in node.children:
                add(child, node_id)

    add(root)
    lines.append("}")
    return "\n".join(lines)
