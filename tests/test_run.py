"""Tests for the reproducible experiment entry point."""

import csv
import json

import pytest

from experiments.run import MAX_EXPERIMENT_DEPTH, run_experiment


def test_run_experiment_writes_reproducible_artifacts(tmp_path):
    result = run_experiment(
        min_depth=0,
        max_depth=1,
        n_per_depth=2,
        seed=17,
        bounded_depth=0,
        results_dir=tmp_path,
    )

    assert result["metadata"]["dataset_size"] == 8
    assert result["metadata"]["depths"] == [0, 1]
    assert result["metadata"]["seed"] == 17
    assert (tmp_path / "details.json").exists()
    assert (tmp_path / "metadata.json").exists()
    with (tmp_path / "summary.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert [row["method"] for row in rows] == ["bounded_d0", "cfg"]
    assert len(json.loads((tmp_path / "details.json").read_text(encoding="utf-8"))) == 8


@pytest.mark.parametrize(
    "kwargs, error",
    [
        ({"max_depth": MAX_EXPERIMENT_DEPTH + 1}, ValueError),
        ({"max_depth": -1}, ValueError),
        ({"n_per_depth": 0}, ValueError),
        ({"n_per_depth": True}, TypeError),
        ({"max_depth": 1.5}, TypeError),
    ],
)
def test_run_experiment_rejects_invalid_limits_before_writing(tmp_path, kwargs, error):
    with pytest.raises(error):
        run_experiment(results_dir=tmp_path, **kwargs)

    assert not list(tmp_path.iterdir())
