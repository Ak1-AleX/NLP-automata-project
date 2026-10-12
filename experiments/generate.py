"""Генератор корректных и некорректных английских предложений.

Используется для сравнительного эксперимента: одна и та же выборка
подаётся всем анализаторам (dfa, stack, bounded, cfg).
"""

import random


DET = ["the", "a"]
N = ["cat", "dog", "boy", "girl", "man", "woman", "bird", "child"]
IV = ["ran", "slept", "smiled", "waited", "laughed"]
V = ["saw", "chased", "heard", "found", "liked"]


# --- Генерация корректных предложений ---

def generate_sentence(depth: int, rng: random.Random | None = None) -> str:
    """Генерирует корректное английское предложение заданной глубины.

    Глубина 0 — базовая именная группа без придаточных.
    Глубина k — k вложенных придаточных.
    """
    if rng is None:
        rng = random.Random()
    if depth < 0:
        raise ValueError("глубина не может быть отрицательной")

    np = _generate_np(depth, rng)
    iv = rng.choice(IV)
    return f"{np} {iv}"


def _generate_np(depth: int, rng: random.Random) -> str:
    """Рекурсивно строит именную группу заданной глубины.

    Глубина 0: Det N
    Глубина k: Det N that <np глубины k-1> V
    """
    det = rng.choice(DET)
    n = rng.choice(N)
    if depth == 0:
        return f"{det} {n}"
    inner_np = _generate_np(depth - 1, rng)
    v = rng.choice(V)
    return f"{det} {n} that {inner_np} {v}"


# --- Генерация некорректных предложений ---

NEGATIVE_TYPES = [
    "word_order",
    "missing_iv",
    "extra_det",
    "unclosed_embedding",
    "unknown_token",
    "missing_det",
]


def generate_negative(depth: int, rng: random.Random | None = None,
                      negative_type: str | None = None) -> tuple[str, str]:
    """Генерирует некорректное предложение.

    Возвращает (строка, тип_некорректности).
    Если negative_type не задан — выбирается случайно.
    """
    if rng is None:
        rng = random.Random()
    if negative_type is None:
        negative_type = rng.choice(NEGATIVE_TYPES)
    if negative_type not in NEGATIVE_TYPES:
        raise ValueError(f"неизвестный тип: {negative_type!r}")

    base = generate_sentence(depth, rng)
    tokens = base.split()

    if negative_type == "word_order":
        # меняем местами первые два токена
        tokens[0], tokens[1] = tokens[1], tokens[0]
    elif negative_type == "missing_iv":
        # убираем последний токен (непереходный глагол)
        tokens = tokens[:-1]
    elif negative_type == "extra_det":
        # вставляем лишний "the" в начало
        tokens = ["the"] + tokens
    elif negative_type == "unclosed_embedding":
        # вставляем "that the cat chased" в конец, но без внешнего IV
        tokens = tokens + ["that", "the", "cat", "chased"]
    elif negative_type == "unknown_token":
        # заменяем последний токен на неизвестный
        tokens[-1] = "fly"
    elif negative_type == "missing_det":
        # убираем определитель в начале
        tokens = tokens[1:]

    return " ".join(tokens), negative_type


# --- Генерация набора данных ---

def generate_dataset(
    depths: range,
    n_per_depth: int,
    include_negative: bool = True,
    seed: int = 42,
) -> list[dict]:
    """Генерирует размеченный набор данных.

    Каждая запись:
    {
        "input": str,
        "depth": int,
        "label": "correct" | "incorrect",
        "negative_type": str | None,
    }
    """
    rng = random.Random(seed)
    dataset = []

    for depth in depths:
        for _ in range(n_per_depth):
            sentence = generate_sentence(depth, rng)
            dataset.append({
                "input": sentence,
                "depth": depth,
                "label": "correct",
                "negative_type": None,
            })

        if include_negative:
            for _ in range(n_per_depth):
                sentence, neg_type = generate_negative(depth, rng)
                dataset.append({
                    "input": sentence,
                    "depth": depth,
                    "label": "incorrect",
                    "negative_type": neg_type,
                })

    return dataset