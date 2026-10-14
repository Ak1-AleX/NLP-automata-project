"""Интерактивная демонстрация конечных автоматов и рекурсивной грамматики."""

from __future__ import annotations

import csv
import io
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

from automata.bounded_nesting import analyze as analyze_bounded, get_pattern
from automata.dfa import analyze as analyze_dfa
from automata.stack_checker import analyze as analyze_stack
from experiments.evaluate import evaluate
from experiments.generate import generate_dataset
from grammar.parser import analyze as analyze_cfg
from visualization.automaton import automaton_to_dot
from visualization.parse_tree import parse_tree_to_dot


st.set_page_config(page_title="Границы конечного автомата", page_icon="⌘", layout="wide")


def _show_decision(result: dict, subject: str) -> None:
    if result["error"]:
        st.error(f"Ошибка входа: {result['error']}")
    elif result["accepted"]:
        st.success(f"{subject}: строка принята")
    else:
        st.warning(f"{subject}: строка отклонена")


def _experiment_csv(summary: list[dict], depths: list[int]) -> str:
    output = io.StringIO(newline="")
    fields = [
        "method", "correct_accepted", "correct_total",
        "incorrect_rejected", "incorrect_total",
        *[f"accuracy_depth_{depth}" for depth in depths],
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in summary:
        record = {key: row[key] for key in fields[:5]}
        for depth in depths:
            record[f"accuracy_depth_{depth}"] = row["accuracy_by_depth"].get(depth, "")
        writer.writerow(record)
    return output.getvalue()


def _overall_accuracy(row: dict) -> float:
    total = row["correct_total"] + row["incorrect_total"]
    if total == 0:
        return 0.0
    correct = row["correct_accepted"] + row["incorrect_rejected"]
    return correct / total


st.title("Где заканчиваются возможности конечного автомата?")
st.markdown(
    "Учебная демонстрация на формальных языках и небольшом фрагменте английского. "
    "Она показывает, как стек и рекурсивная КС-грамматика описывают выбранные "
    "неограниченные зависимости. Это не универсальный анализатор естественного языка."
)

page = st.sidebar.radio("Раздел", ["Формальные языки", "Вложенность в NLP"])

if page == "Формальные языки":
    dfa_tab, stack_tab = st.tabs(["ДКА для L₁", "Стек для L₂"])

    with dfa_tab:
        st.subheader("Регулярный язык L₁ = { aᵐbⁿ | m, n ≥ 0 }")
        st.write("Автомат принимает любую последовательность `a`, за которой следуют `b`.")
        dfa_input = st.text_input("Строка над алфавитом {a, b}", "aabb", key="dfa_input")
        dfa_result = analyze_dfa(dfa_input)
        _show_decision(dfa_result, "ДКА")
        st.graphviz_chart(automaton_to_dot(dfa_result["trace"], dfa_result["accepted"]))
        with st.expander("Трассировка переходов"):
            st.dataframe(dfa_result["trace"], width="stretch", hide_index=True)

    with stack_tab:
        st.subheader("Нерегулярный язык L₂ = { aⁿbⁿ | n ≥ 0 }")
        st.write("Для каждой `a` алгоритм кладёт символ в стек; для каждой `b` снимает.")
        stack_input = st.text_input("Строка над алфавитом {a, b}", "aaabbb", key="stack_input")
        stack_result = analyze_stack(stack_input)
        _show_decision(stack_result, "Стековый анализатор")
        if stack_result["trace"]:
            st.dataframe(stack_result["trace"], width="stretch", hide_index=True)
        else:
            st.caption("Пустая строка принимается: n = 0.")
        st.info(
            "Стековый алгоритм принимает любое конечное n. Сам по себе конечный "
            "набор проверок не доказывает, что язык нерегулярен; доказательство "
            "приведено в docs/pumping_lemma.md."
        )

else:
    check_tab, experiment_tab = st.tabs(["Проверка моделей", "Эксперимент"])

    with check_tab:
        st.subheader("Рекурсивная вложенность в учебном английском фрагменте")
        st.caption(
            "Введите предложение строчными буквами без точки, например: "
            "the cat that the dog that the boy saw chased ran"
        )
        sentence = st.text_input(
            "Предложение", "the cat that the dog that the boy saw chased ran",
            key="sentence_input",
        )
        max_depth = st.slider("Лимит глубины регулярной модели", 0, 6, 1)
        bounded_result = analyze_bounded(sentence, max_depth=max_depth)
        cfg_result = analyze_cfg(sentence, grammar="english")

        bounded_col, cfg_col = st.columns(2)
        with bounded_col:
            st.markdown("#### Ограниченная регулярная модель")
            _show_decision(bounded_result, f"Лимит глубины {max_depth}")
        with cfg_col:
            st.markdown("#### Рекурсивная КС-грамматика")
            _show_decision(cfg_result, "CFG")

        if cfg_result["parse_tree"]:
            st.markdown("#### Дерево разбора")
            st.graphviz_chart(parse_tree_to_dot(cfg_result["parse_tree"]))
            with st.expander("Скобочная запись дерева"):
                st.code(cfg_result["parse_tree"], language="text")
        if cfg_result["error"]:
            st.caption(cfg_result["error"])

        with st.expander("Регулярное выражение при выбранном лимите"):
            st.code(get_pattern(max_depth), language="regex")

        st.info(
            "Регулярная модель заранее ограничена по глубине и потому соответствует "
            "некоторому конечному автомату. CFG использует рекурсивное правило. "
            "Непринятие этой учебной грамматикой не означает, что предложение "
            "неграмматично в реальном английском."
        )

    with experiment_tab:
        st.subheader("Сравнение на одном воспроизводимом наборе")
        st.write(
            "Для каждой глубины создаются корректные и контролируемо некорректные "
            "предложения. Обе модели получают одинаковые строки."
        )
        with st.form("experiment_form"):
            left, right = st.columns(2)
            with left:
                bounded_depth = st.slider("Лимит регулярной модели", 0, 5, 1, key="exp_bounded")
                deepest = st.slider("Наибольшая глубина примеров", 1, 8, 4)
            with right:
                per_label = st.slider("Примеров каждого класса на глубину", 2, 50, 20)
                seed = st.number_input("Seed генератора", min_value=0, max_value=2**31 - 1, value=42)
            submitted = st.form_submit_button("Запустить эксперимент")

        if submitted:
            depths = list(range(deepest + 1))
            dataset = generate_dataset(
                range(deepest + 1), n_per_depth=per_label,
                include_negative=True, seed=int(seed),
            )
            result = evaluate(dataset, [
                {
                    "name": f"bounded_d{bounded_depth}",
                    "fn": analyze_bounded,
                    "options": {"max_depth": bounded_depth},
                },
                {"name": "cfg", "fn": analyze_cfg, "options": {"grammar": "english"}},
            ])
            st.session_state["experiment_result"] = {
                "result": result,
                "depths": depths,
                "per_label": per_label,
                "seed": int(seed),
                "bounded_depth": bounded_depth,
            }

        saved = st.session_state.get("experiment_result")
        if saved:
            result = saved["result"]
            depths = saved["depths"]
            summary = result["summary"]
            rows = []
            for row in summary:
                rows.append({
                    "Модель": row["method"],
                    "Приняты корректные": f"{row['correct_accepted']}/{row['correct_total']}",
                    "Отклонены некорректные": f"{row['incorrect_rejected']}/{row['incorrect_total']}",
                    "Общая точность": f"{_overall_accuracy(row):.1%}",
                })
            st.dataframe(rows, width="stretch", hide_index=True)

            figure, axis = plt.subplots(figsize=(7.5, 4.2))
            for row in summary:
                values = [row["accuracy_by_depth"].get(depth, 0.0) for depth in depths]
                axis.plot(depths, values, marker="o", linewidth=2, label=row["method"])
            axis.set(title="Доля принятых корректных примеров по глубине", xlabel="Глубина вложенности", ylabel="Доля")
            axis.set_ylim(-0.05, 1.05)
            axis.set_xticks(depths)
            axis.grid(axis="y", alpha=0.25)
            axis.legend()
            figure.tight_layout()
            st.pyplot(figure)
            plt.close(figure)
            st.caption(
                f"Seed: {saved['seed']}; {saved['per_label']} примеров каждого класса "
                f"на глубину; лимит регулярной модели: {saved['bounded_depth']}. "
                "График показывает долю принятых положительных примеров."
            )

            st.download_button(
                "Скачать сводку CSV",
                data=_experiment_csv(summary, depths),
                file_name="summary.csv",
                mime="text/csv",
            )
            st.download_button(
                "Скачать результаты JSON",
                data=json.dumps(result["details"], ensure_ascii=False, indent=2),
                file_name="details.json",
                mime="application/json",
            )

            with st.expander("Первые десять примеров и результаты"):
                st.json(result["details"][:10])
        else:
            st.caption("Задайте параметры и запустите эксперимент.")
