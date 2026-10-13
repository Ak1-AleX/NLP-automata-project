"""Стековый алгоритм для языка L2 = a^n b^n (n >= 0)."""

from time import perf_counter

ALPHABET = {"a", "b"}


def analyze(input_str: str) -> dict:
    """Проверяет строку на принадлежность L2 с помощью стека.

    Возвращает dict по контракту из docs/api.md.
    """
    started = perf_counter()
    stack = []
    trace = []
    error = None
    saw_b = False       # встретили ли уже первый b
    rejected = False

    for i, symbol in enumerate(input_str, start=1):
        if symbol not in ALPHABET:
            error = f"символ '{symbol}' не входит в алфавит {{a, b}}"
            break

        if symbol == "a":
            if saw_b:
                # a после b — порядок нарушен
                trace.append({"step": i, "symbol": symbol,
                              "action": "reject", "stack": list(stack)})
                rejected = True
                break
            stack.append("a")
            trace.append({"step": i, "symbol": symbol,
                          "action": "push", "stack": list(stack)})
        else:  # symbol == "b"
            saw_b = True
            if not stack:
                # b без соответствующей a
                trace.append({"step": i, "symbol": symbol,
                              "action": "reject", "stack": list(stack)})
                rejected = True
                break
            stack.pop()
            trace.append({"step": i, "symbol": symbol,
                          "action": "pop", "stack": list(stack)})

    accepted = (
        error is None
        and not rejected
        and len(stack) == 0
    )

    return {
        "accepted": accepted,
        "method": "stack",
        "input": input_str,
        "tokens": [],
        "trace": trace,
        "parse_tree": None,
        "error": error,
        "elapsed_ms": (perf_counter() - started) * 1000,
    }
