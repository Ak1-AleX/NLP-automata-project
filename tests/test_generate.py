"""Тесты для experiments/generate.py."""

import random
import pytest

from experiments.generate import (
    generate_sentence,
    generate_negative,
    generate_dataset,
    NEGATIVE_TYPES,
)
from grammar.parser import analyze as parse
from automata.bounded_nesting import count_depth


# --- generate_sentence: структура ---

@pytest.mark.parametrize("depth", [0, 1, 2, 3, 4])
def test_generated_sentence_has_correct_depth(depth):
    rng = random.Random(0)
    sentence = generate_sentence(depth, rng)
    assert count_depth(sentence) == depth


@pytest.mark.parametrize("depth", [0, 1, 2, 3])
def test_generated_sentence_ends_with_iv(depth):
    rng = random.Random(0)
    sentence = generate_sentence(depth, rng)
    last_token = sentence.split()[-1]
    from experiments.generate import IV
    assert last_token in IV


def test_negative_depth_raises():
    with pytest.raises(ValueError):
        generate_sentence(-1, random.Random(0))


# --- generate_sentence: согласованность с CFG ---

@pytest.mark.parametrize("depth", [0, 1, 2, 3])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_generated_sentence_is_accepted_by_cfg(depth, seed):
    """Ключевой тест: генератор не должен выдавать мусор."""
    rng = random.Random(seed)
    sentence = generate_sentence(depth, rng)
    result = parse(sentence, grammar="english")
    assert result["accepted"] is True, f"CFG отклонил: {sentence!r}"


# --- generate_negative: все типы ---

@pytest.mark.parametrize("neg_type", NEGATIVE_TYPES)
def test_negative_rejected_by_cfg(neg_type):
    """Все сгенерированные некорректные строки должны отклоняться CFG."""
    rng = random.Random(0)
    sentence, returned_type = generate_negative(1, rng, neg_type)
    assert returned_type == neg_type
    result = parse(sentence, grammar="english")
    assert result["accepted"] is False, f"CFG принял некорректное: {sentence!r}"


def test_unknown_negative_type_raises():
    with pytest.raises(ValueError):
        generate_negative(1, random.Random(0), "nonexistent_type")


def test_negative_type_is_returned():
    rng = random.Random(0)
    sentence, neg_type = generate_negative(2, rng)
    assert neg_type in NEGATIVE_TYPES
    assert isinstance(sentence, str)


# --- generate_dataset: структура ---

def test_dataset_length():
    dataset = generate_dataset(range(0, 3), n_per_depth=2)
    # 3 глубины * (2 корректных + 2 некорректных) = 12
    assert len(dataset) == 12


def test_dataset_length_without_negatives():
    dataset = generate_dataset(range(0, 3), n_per_depth=2, include_negative=False)
    assert len(dataset) == 6


def test_dataset_record_format():
    dataset = generate_dataset(range(0, 2), n_per_depth=1)
    expected_keys = {"input", "depth", "label", "negative_type"}
    for record in dataset:
        assert set(record.keys()) == expected_keys
        assert isinstance(record["input"], str)
        assert isinstance(record["depth"], int)
        assert record["label"] in {"correct", "incorrect"}
        if record["label"] == "correct":
            assert record["negative_type"] is None
        else:
            assert record["negative_type"] in NEGATIVE_TYPES


def test_dataset_labels_match_parser():
    """Каждая запись должна пройти проверку CFG согласно своей метке."""
    dataset = generate_dataset(range(0, 3), n_per_depth=2, seed=1)
    for record in dataset:
        result = parse(record["input"], grammar="english")
        if record["label"] == "correct":
            assert result["accepted"] is True, record
        else:
            assert result["accepted"] is False, record


def test_dataset_depth_distribution():
    dataset = generate_dataset(range(0, 4), n_per_depth=3)
    depths = [r["depth"] for r in dataset]
    for d in range(4):
        count = sum(1 for x in depths if x == d)
        # 3 корректных + 3 некорректных на каждую глубину
        assert count == 6


# --- Воспроизводимость ---

def test_dataset_reproducible_with_same_seed():
    d1 = generate_dataset(range(0, 3), n_per_depth=2, seed=42)
    d2 = generate_dataset(range(0, 3), n_per_depth=2, seed=42)
    assert d1 == d2


def test_dataset_differs_with_different_seed():
    d1 = generate_dataset(range(0, 3), n_per_depth=2, seed=42)
    d2 = generate_dataset(range(0, 3), n_per_depth=2, seed=43)
    assert d1 != d2


# --- Разнообразие ---

def test_dataset_has_variety():
    """Генератор не должен выдавать одну и ту же строку подряд."""
    dataset = generate_dataset(range(0, 3), n_per_depth=5, seed=0)
    inputs = [r["input"] for r in dataset if r["label"] == "correct"]
    # минимум половина должна быть уникальной
    assert len(set(inputs)) >= len(inputs) // 2