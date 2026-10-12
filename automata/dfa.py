"""ДКА для языка L1 = a^m b^n (m, n >= 0)."""

ALPHABET = {"a", "b"}

# Состояния:
#   q0 — читаем a (начальное, принимающее)
#   q1 — читаем b (принимающее)
#   q2 — ошибка (порядок нарушен)
TRANSITIONS = {
    ("q0", "a"): "q0",
    ("q0", "b"): "q1",
    ("q1", "a"): "q2",
    ("q1", "b"): "q1",
    ("q2", "a"): "q2",
    ("q2", "b"): "q2",
}

START_STATE = "q0"
ACCEPT_STATES = {"q0", "q1"}


def analyze(input_str: str) -> dict:
    """Прогоняет строку по ДКА для L1.

    Возвращает dict по контракту из docs/api.md.
    """
    trace = [{"step": 0, "state": START_STATE, "symbol": None, "next_state": START_STATE}]
    state = START_STATE
    error = None

    for i, symbol in enumerate(input_str):
        if symbol not in ALPHABET:
            error = f"символ '{symbol}' не входит в алфавит {{a, b}}"
            break
        next_state = TRANSITIONS[(state, symbol)]
        trace.append({
            "step": i + 1,
            "state": state,
            "symbol": symbol,
            "next_state": next_state,
        })
        state = next_state

    accepted = (error is None) and (state in ACCEPT_STATES)

    return {
        "accepted": accepted,
        "method": "dfa",
        "input": input_str,
        "tokens": [],
        "trace": trace,
        "parse_tree": None,
        "error": error,
        "elapsed_ms": 0.0,
    }
