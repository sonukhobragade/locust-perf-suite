"""Unit tests for tools/ab_compare.py.

These run without a load test, a service or a network. `tests/` previously held
only Locust scenario modules named `*_load.py`, which pytest does not collect,
so the gate's test step matched nothing and passed. These are the first tests
in the repository that the gate can actually run.

The comparison logic is worth testing because it is what decides whether a
branch is called a regression, and the thresholds are exclusive in a way that
is easy to get wrong by one.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.ab_compare import flag, fmt_delta, load  # noqa: E402


HEADER = [
    "Type",
    "Name",
    "Request Count",
    "Failure Count",
    "Average Response Time",
    "50%",
    "95%",
    "99%",
]


def write_stats(tmp_path: Path, rows: list[list[str]]) -> str:
    path = tmp_path / "stats.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)
    return str(path)


class TestLoad:
    def test_reads_a_row_into_typed_values(self, tmp_path):
        p = write_stats(tmp_path, [["GET", "/orders", "120", "3", "88.5", "70", "150", "220"]])

        stats = load(p)

        assert stats == {
            "GET /orders": {
                "reqs": 120,
                "fails": 3,
                "p50": 70.0,
                "p95": 150.0,
                "p99": 220.0,
                "avg": 88.5,
            }
        }

    def test_the_aggregated_row_is_dropped(self, tmp_path):
        p = write_stats(
            tmp_path,
            [
                ["GET", "/orders", "120", "0", "88", "70", "150", "220"],
                ["", "Aggregated", "120", "0", "88", "70", "150", "220"],
            ],
        )

        stats = load(p)

        assert list(stats) == ["GET /orders"]

    def test_the_key_is_method_then_name(self, tmp_path):
        p = write_stats(tmp_path, [["POST", "/orders", "1", "0", "1", "1", "1", "1"]])

        assert list(load(p)) == ["POST /orders"]

    def test_two_methods_on_one_path_stay_separate(self, tmp_path):
        p = write_stats(
            tmp_path,
            [
                ["GET", "/orders", "10", "0", "50", "40", "80", "90"],
                ["POST", "/orders", "20", "0", "60", "50", "90", "99"],
            ],
        )

        stats = load(p)

        assert sorted(stats) == ["GET /orders", "POST /orders"]
        assert stats["POST /orders"]["reqs"] == 20

    def test_an_empty_run_loads_as_no_endpoints(self, tmp_path):
        assert load(write_stats(tmp_path, [])) == {}


class TestFmtDelta:
    def test_a_slower_run_is_positive_and_signed(self):
        d, pct, text = fmt_delta(100.0, 150.0)

        assert d == 50.0
        assert pct == 50.0
        assert text == "+50 (+50%)"

    def test_a_faster_run_is_negative_and_carries_its_own_minus(self):
        d, pct, text = fmt_delta(100.0, 60.0)

        assert d == -40.0
        assert pct == -40.0
        assert text == "-40 (-40%)"

    def test_no_change_reads_as_zero_without_a_sign(self):
        _, _, text = fmt_delta(100.0, 100.0)

        assert text == "0 (0%)"

    def test_a_baseline_of_zero_does_not_divide_by_zero(self):
        # An endpoint that recorded 0ms on the baseline run. Reporting must not
        # blow up on it, and a percentage against zero is meaningless.
        d, pct, _ = fmt_delta(0.0, 25.0)

        assert d == 25.0
        assert pct == 0


class TestFlag:
    @pytest.mark.parametrize("pct", [25.1, 40, 300])
    def test_more_than_25_percent_slower_is_a_regression(self, pct):
        assert "regression" in flag(pct)

    @pytest.mark.parametrize("pct", [10.1, 20, 25])
    def test_between_10_and_25_is_minor(self, pct):
        assert "minor" in flag(pct)

    @pytest.mark.parametrize("pct", [-10.1, -30, -90])
    def test_more_than_10_percent_faster_is_an_improvement(self, pct):
        assert "improved" in flag(pct)

    @pytest.mark.parametrize("pct", [-10, -5, 0, 5, 10])
    def test_the_band_between_minus_10_and_10_is_flat(self, pct):
        assert "flat" in flag(pct)

    def test_the_boundaries_are_exclusive(self):
        # Exactly 25 is not yet a regression and exactly 10 is not yet minor.
        # Both thresholds are `>`, and a run that lands precisely on one should
        # not change category.
        assert "minor" in flag(25)
        assert "regression" not in flag(25)
        assert "flat" in flag(10)
        assert "minor" not in flag(10)
