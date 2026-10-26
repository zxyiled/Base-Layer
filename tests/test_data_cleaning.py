import os
import sys
import tempfile
import unittest
import zipfile

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from data_cleaning import DataCleaner  # noqa: E402
from data_loader import SiataLoader  # noqa: E402


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
        self.cleaner = DataCleaner()
        self.clean = self.cleaner.clean_data(RAW)

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
            self.cleaner.clean_data(pd.DataFrame([raw_row("Unknown", "x", 1, 1.0)]))

    def test_station_table_has_one_column_per_variable(self):
        wide = self.cleaner.station_table(self.clean, "TST-ONE")
        self.assertEqual(wide.shape, (2, 3))
        self.assertEqual(wide.loc[pd.Timestamp("2026-08-01 01:00"), "relative_humidity"], 80.0)

    def test_raw_table_is_not_modified(self):
        before = RAW.copy(deep=True)
        self.cleaner.clean_data(RAW)
        pd.testing.assert_frame_equal(RAW, before)

    def test_physical_limits_are_inclusive_and_negative_temperature_is_valid(self):
        raw = pd.DataFrame([
            raw_row("Humedad Relativa", "%", 1, 100.0),  # saturation is possible
            raw_row("Humedad Relativa", "%", 2, 0.0),
            raw_row("Direccion del Viento", "Deg", 1, 360.0),
            raw_row("Temperatura", "C", 1, -2.5),
            raw_row("Ozono", "ug/m3", 1, 0.0),  # zero is a valid measurement
        ])
        clean = self.cleaner.clean_data(raw)
        self.assertEqual(int(clean["value"].isna().sum()), 0)
        self.assertEqual(len(clean), len(raw))

    def test_duplicate_station_variable_hour_keeps_first_and_is_counted(self):
        raw = pd.DataFrame([
            raw_row("Temperatura", "C", 1, 20.0),
            raw_row("Temperatura", "C", 1, 21.0),  # same key, different value
        ])
        clean = self.cleaner.clean_data(raw)
        self.assertEqual(len(clean), 1)
        self.assertEqual(clean["value"].iloc[0], 20.0)
        summary = self.cleaner.cleaning_summary(raw, clean).set_index("check")
        self.assertEqual(summary.loc["duplicated_station_variable_hour", "before"], 1)
        self.assertEqual(summary.loc["duplicated_station_variable_hour", "after"], 0)

    def test_end_time_mismatch_is_detected(self):
        raw = pd.DataFrame([raw_row("Temperatura", "C", 1, 20.0), raw_row("Temperatura", "C", 2, 21.0)])
        raw.loc[1, "FechaFin"] = "01/08/2026 05:00:00 am"
        self.assertEqual(self.cleaner.end_time_mismatches(raw), 1)

    def test_midnight_is_parsed_as_hour_zero(self):
        raw = pd.DataFrame([raw_row("Temperatura", "C", 1, 20.0)])
        raw.loc[0, "FechaInicio"] = "01/08/2026 12:00:00 am"
        clean = self.cleaner.clean_data(raw)
        self.assertEqual(clean["start_time"].iloc[0], pd.Timestamp("2026-08-01 00:00"))

    def test_summary_counts(self):
        summary = self.cleaner.cleaning_summary(RAW, self.clean).set_index("check")
        self.assertEqual(summary.loc["exact_duplicate_records", "before"], 1)
        self.assertEqual(summary.loc["physically_impossible_values", "before"], 2)
        self.assertEqual(summary.loc["physically_impossible_values", "after"], 0)
        self.assertEqual(self.cleaner.end_time_mismatches(RAW), 0)


class TestLoader(unittest.TestCase):

    def test_missing_zip_gives_a_clear_error(self):
        with tempfile.TemporaryDirectory() as folder:
            loader = SiataLoader(os.path.join(folder, "missing.zip"))
            with self.assertRaises(FileNotFoundError):
                loader.load_raw()

    def test_zip_without_xls_files_is_rejected_and_left_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "empty.zip")
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("Datos/readme.txt", "not an xls file")
            with open(path, "rb") as handle:
                original = handle.read()
            with self.assertRaises(ValueError):
                SiataLoader(path).load_raw()
            with open(path, "rb") as handle:
                self.assertEqual(handle.read(), original)


if __name__ == "__main__":
    unittest.main()
