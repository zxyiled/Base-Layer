import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from dataset import COLUMNS, column_values, format_table, head, round_values, tail  # noqa: E402


def make_record(year, source, total):
    """Build a record shaped like the API ones (every value is a string)."""
    record = {name: "0" for name in COLUMNS}
    record.update({":id": "row-x", "ano": str(year), "fuente": source, "generacion_total_gwh": str(total)})
    return record


RECORDS = [make_record(2000 + i, f"S{i}", i * 1.5) for i in range(5)]


class TestHeadTail(unittest.TestCase):

    def test_head_returns_first_rows(self):
        self.assertEqual(head(RECORDS, 2), RECORDS[:2])

    def test_tail_returns_last_rows(self):
        self.assertEqual(tail(RECORDS, 2), RECORDS[-2:])

    def test_more_rows_than_available_returns_everything(self):
        self.assertEqual(head(RECORDS, 10), RECORDS)
        self.assertEqual(tail(RECORDS, 10), RECORDS)

    def test_zero_or_negative_rows_returns_nothing(self):
        for n in (0, -2):
            with self.subTest(n=n):
                self.assertEqual(head(RECORDS, n), [])
                self.assertEqual(tail(RECORDS, n), [])


class TestColumns(unittest.TestCase):

    def test_column_values_are_parsed_with_the_column_type(self):
        self.assertEqual(column_values(RECORDS, "ano"), [2000, 2001, 2002, 2003, 2004])
        self.assertEqual(column_values(RECORDS, "fuente"), ["S0", "S1", "S2", "S3", "S4"])
        self.assertEqual(column_values(RECORDS, "generacion_total_gwh"), [0.0, 1.5, 3.0, 4.5, 6.0])

    def test_format_table_shows_only_the_selected_columns(self):
        lines = format_table(head(RECORDS, 2), ["ano", "fuente"]).splitlines()
        self.assertEqual(lines[0].split(), ["ano", "fuente"])
        self.assertEqual(len(lines), 4)  # header + separator + 2 rows
        self.assertEqual(lines[2].split(), ["2000", "S0"])
        self.assertNotIn(":id", lines[0])


class TestRoundValues(unittest.TestCase):

    def test_rounds_to_the_given_decimals(self):
        self.assertEqual(round_values([1.23456, 7.891], 2), [1.23, 7.89])

    def test_zero_decimals_returns_integers(self):
        result = round_values([1.4, 7.6], 0)
        self.assertEqual(result, [1, 8])
        self.assertTrue(all(isinstance(value, int) for value in result))


if __name__ == "__main__":
    unittest.main()
