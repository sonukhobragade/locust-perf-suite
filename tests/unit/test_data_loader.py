"""Unit tests for util/data_loader.py.

Both loaders swallow their exceptions and return an empty list, which is a
deliberate choice for a load test: a missing CSV should not take down a run
that has already spawned users. It does mean the empty list is doing double
duty, so these tests pin both halves of that behaviour rather than only the
happy path.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from util.data_loader import load_test_data_from_csv, load_user_ids_from_csv  # noqa: E402


def write_csv(tmp_path: Path, text: str) -> str:
    path = tmp_path / "data.csv"
    path.write_text(text)
    return str(path)


class TestLoadUserIds:
    def test_the_first_row_is_treated_as_a_header_and_skipped(self, tmp_path):
        p = write_csv(tmp_path, "user_id\n1001\n1002\n")

        assert load_user_ids_from_csv(p) == ["1001", "1002"]

    def test_a_named_column_index_is_honoured(self, tmp_path):
        p = write_csv(tmp_path, "name,user_id\nasha,1001\nben,1002\n")

        assert load_user_ids_from_csv(p, user_id_column=1) == ["1001", "1002"]

    def test_values_come_back_as_strings(self, tmp_path):
        # IDs are used to build URLs, so a caller should never have to guess
        # whether it got an int.
        p = write_csv(tmp_path, "user_id\n1001\n")

        assert load_user_ids_from_csv(p) == ["1001"]

    def test_a_row_too_short_for_the_column_is_skipped_not_fatal(self, tmp_path):
        p = write_csv(tmp_path, "name,user_id\nasha,1001\nlonely\nben,1002\n")

        assert load_user_ids_from_csv(p, user_id_column=1) == ["1001", "1002"]

    def test_a_missing_file_returns_empty_rather_than_raising(self, tmp_path):
        assert load_user_ids_from_csv(str(tmp_path / "nope.csv")) == []

    def test_a_header_only_file_returns_empty(self, tmp_path):
        assert load_user_ids_from_csv(write_csv(tmp_path, "user_id\n")) == []


class TestLoadTestData:
    def test_rows_come_back_keyed_by_column_name(self, tmp_path):
        p = write_csv(tmp_path, "user,plan\nasha,pro\nben,free\n")

        assert load_test_data_from_csv(p) == [
            {"user": "asha", "plan": "pro"},
            {"user": "ben", "plan": "free"},
        ]

    def test_the_header_is_consumed_as_keys_not_returned_as_a_row(self, tmp_path):
        p = write_csv(tmp_path, "user,plan\nasha,pro\n")

        rows = load_test_data_from_csv(p)

        assert len(rows) == 1
        assert rows[0]["user"] == "asha"

    def test_a_missing_file_returns_empty_rather_than_raising(self, tmp_path):
        assert load_test_data_from_csv(str(tmp_path / "nope.csv")) == []

    def test_a_header_only_file_returns_empty(self, tmp_path):
        assert load_test_data_from_csv(write_csv(tmp_path, "user,plan\n")) == []
