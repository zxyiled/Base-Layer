import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main  

# Records shaped like the API ones: every value is a string
TOTALS = ["10.256", "8.751", "7.249", "5.754", "4.333"]
RECORDS = [
    dict({name: "0" for name in main.COLUMN_NAMES}, ano=str(2000 + i), fuente=f"S{i}", generacion_total_gwh=total)
    for i, total in enumerate(TOTALS)
]


def sorted_section(output):
    """Return the values printed after 'Sorted:'."""
    return output.split("Sorted:")[1].split()


def run_with_input(func, answers, *args):
    """Run `func` feeding `answers` to input(); return (result, printed output)."""
    output = io.StringIO()
    with patch("builtins.input", side_effect=answers), redirect_stdout(output):
        result = func(*args)
    return result, output.getvalue()


class TestInputHelpers(unittest.TestCase):

    def test_ask_int_retries_until_valid(self):
        result, output = run_with_input(main.ask_int, ["abc", "-1", "0", "9", "3"], "Columns?", 1, 8)
        self.assertEqual(result, 3)
        self.assertIn("'abc' is not a whole number.", output)
        self.assertEqual(output.count("between 1 and 8"), 3)

    def test_ask_option_accepts_name_or_number(self):
        options = ["head", "tail"]
        self.assertEqual(run_with_input(main.ask_option, ["TAIL"], "Mode?", options)[0], "tail")
        self.assertEqual(run_with_input(main.ask_option, ["1"], "Mode?", options)[0], "head")

    def test_ask_option_rejects_unknown_values(self):
        result, output = run_with_input(main.ask_option, ["nope", "0", "3", "tail"], "Mode?", ["head", "tail"])
        self.assertEqual(result, "tail")
        self.assertEqual(output.count("Invalid option"), 3)


class TestPreview(unittest.TestCase):

    def test_preview_shows_selected_number_of_columns(self):
        # 99 columns is rejected, then 2 columns, tail, 1 row
        _, output = run_with_input(main.preview, ["99", "2", "tail", "1"], RECORDS)
        self.assertIn("between 1 and 8", output)
        table = output.strip().splitlines()[-3:]
        self.assertEqual(table[0].split(), ["ano", "mes"])
        self.assertEqual(table[2].split(), ["2004", "0"])


class TestSortColumn(unittest.TestCase):

    def test_incompatible_combination_shows_message_without_sorting(self):
        with patch.object(main, "print_sorted") as print_sorted:
            _, output = run_with_input(main.sort_column, ["fuente", "head", "5", "counting"], RECORDS)
        print_sorted.assert_not_called()
        self.assertIn("Counting Sort cannot be applied to column 'fuente'.", output)
        self.assertIn("requires non-negative integer values", output)

    def test_compatible_combination_sorts(self):
        _, output = run_with_input(main.sort_column, ["ano", "head", "5", "radix"], RECORDS)
        self.assertIn("Method: Radix Sort", output)
        self.assertNotIn("cannot be applied", output)

    def test_main_keeps_running_after_incompatible_selection(self):
        answers = ["sort", "fuente", "head", "5", "bucket", "sort", "fuente", "head", "5", "merge", "exit"]
        with patch.object(main, "get_data", return_value=RECORDS):
            _, output = run_with_input(main.main, answers)
        self.assertIn("Bucket Sort cannot be applied to column 'fuente'.", output)
        self.assertIn("Method: Merge Sort", output)
        self.assertIn("Goodbye.", output)

    def test_sorts_only_the_selected_rows(self):
        _, output = run_with_input(main.sort_column, ["ano", "tail", "2", "bubble"], RECORDS)
        self.assertEqual(sorted_section(output), ["2003", "2004"])

    def test_rounding_is_only_asked_for_decimal_columns(self):
        # No answer is given for the rounding question: asking it would exhaust the input
        _, output = run_with_input(main.sort_column, ["ano", "head", "5", "merge"], RECORDS)
        self.assertNotIn("Round the values", output)

    def test_rounds_values_before_sorting(self):
        answers = ["generacion_total_gwh", "head", "5", "yes", "2", "merge"]
        _, output = run_with_input(main.sort_column, answers, RECORDS)
        self.assertEqual(sorted_section(output), ["4.33", "5.75", "7.25", "8.75", "10.26"])

    def test_decimal_column_needs_zero_decimals_for_counting_sort(self):
        answers = ["generacion_total_gwh", "head", "5", "no", "counting"]
        _, output = run_with_input(main.sort_column, answers, RECORDS)
        self.assertIn("Counting Sort cannot be applied to column 'generacion_total_gwh'.", output)

        answers = ["generacion_total_gwh", "head", "5", "yes", "0", "counting"]
        _, output = run_with_input(main.sort_column, answers, RECORDS)
        self.assertIn("Method: Counting Sort", output)
        self.assertEqual(sorted_section(output), ["4", "6", "7", "9", "10"])


if __name__ == "__main__":
    unittest.main()
