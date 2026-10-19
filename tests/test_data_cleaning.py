import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from data_cleaning import clean_data, cleaning_summary, end_time_mismatches, station_table  # noqa: E402


def raw_row(variable, unit, hour, value, station="TST-ONE"):
    """Build a row shaped like the SIATA .xls files (synthetic values)."""
    start = f"01/08/2026 {hour:02d}:00:00 am"
    end = f"01/08/2026 {hour + 1:02d}:00:00 am"
    return {
        "NombreEstacion": station, "Variable": variable, "Unidad": unit,
        "FechaInicio": start, "FechaFin": end, "FechaModificacion": None,
        "Concentracion": value, "MSFLCode": None,
    }


RAW = pd.DataFrame([
    raw_row("Temperatura", "C", 1, 20.0),
    raw_row("Temperatura", "C", 1, 20.0),  # exact duplicate
    raw_row("Temperatura", "C", 2, None),  # sensor gap
    raw_row("Humedad Relativa", "%", 1, 80.0),
    raw_row("Humedad Relativa", "%", 2, 130.0),  # impossible humidity
    raw_row("Precipitacion", "mm", 1, 45.0),  # extreme but possible
    raw_row("Precipitacion", "mm", 2, -1.0),  # impossible rain
])


class TestCleanData(unittest.TestCase):

    def setUp(self):
        self.clean = clean_data(RAW)

    def test_renames_and_parses_types(self):
        self.assertEqual(list(self.clean.columns), ["station", "variable", "unit", "start_time", "value"])
        self.assertEqual(self.clean["start_time"].min(), pd.Timestamp("2026-08-01 01:00"))
        self.assertIn("air_temperature", set(self.clean["variable"]))
        self.assertIn("°C", set(self.clean["unit"]))

    def test_removes_exact_duplicates(self):
        self.assertEqual(len(self.clean), len(RAW) - 1)

    def test_impossible_values_become_missing(self):
        values = self.clean.set_index(["variable", "start_time"])["value"]
        self.assertTrue(pd.isna(values[("relative_humidity", pd.Timestamp("2026-08-01 02:00"))]))
        self.assertTrue(pd.isna(values[("precipitation", pd.Timestamp("2026-08-01 02:00"))]))

    def test_keeps_extreme_valid_values_and_does_not_impute(self):
        values = self.clean.set_index(["variable", "start_time"])["value"]
        self.assertEqual(values[("precipitation", pd.Timestamp("2026-08-01 01:00"))], 45.0)
        self.assertTrue(pd.isna(values[("air_temperature", pd.Timestamp("2026-08-01 02:00"))]))

    def test_unknown_variable_is_rejected(self):
        with self.assertRaises(ValueError):
            clean_data(pd.DataFrame([raw_row("Unknown", "x", 1, 1.0)]))

    def test_station_table_has_one_column_per_variable(self):
        wide = station_table(self.clean, "TST-ONE")
        self.assertEqual(wide.shape, (2, 3))
        self.assertEqual(wide.loc[pd.Timestamp("2026-08-01 01:00"), "relative_humidity"], 80.0)

    def test_summary_counts(self):
        summary = cleaning_summary(RAW, self.clean).set_index("check")
        self.assertEqual(summary.loc["exact_duplicate_records", "before"], 1)
        self.assertEqual(summary.loc["physically_impossible_values", "before"], 2)
        self.assertEqual(summary.loc["physically_impossible_values", "after"], 0)
        self.assertEqual(end_time_mismatches(RAW), 0)


if __name__ == "__main__":
    unittest.main()
