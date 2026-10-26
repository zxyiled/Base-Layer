import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from eda import ExploratoryAnalysis  # noqa: E402


def long_table(station, hours, temperature, humidity):
    """Synthetic long table shaped like the cleaned SIATA data."""
    times = pd.date_range("2026-08-01", periods=hours, freq="h")
    frames = [
        pd.DataFrame({"station": station, "variable": "air_temperature", "unit": "°C",
                      "start_time": times, "value": temperature}),
        pd.DataFrame({"station": station, "variable": "relative_humidity", "unit": "%",
                      "start_time": times, "value": humidity}),
    ]
    return pd.concat(frames, ignore_index=True)


class TestStationCorrelations(unittest.TestCase):

    def test_only_hours_before_the_split_are_used(self):
        # Before the split the relation is perfectly negative; after it, perfectly positive.
        temperature = np.arange(48.0)
        humidity = np.where(np.arange(48) < 24, 100 - temperature, temperature)
        clean = long_table("TST-ONE", 48, temperature, humidity)
        table = ExploratoryAnalysis.station_correlations(
            clean, "air_temperature", "relative_humidity", pd.Timestamp("2026-08-02"))
        self.assertEqual(table["complete_pairs"].tolist(), [24])
        self.assertAlmostEqual(table["pearson_r"].iloc[0], -1.0)

    def test_stations_without_both_variables_are_skipped(self):
        only_temperature = long_table("TST-TWO", 6, np.arange(6.0), np.arange(6.0))
        only_temperature = only_temperature[only_temperature["variable"] == "air_temperature"]
        table = ExploratoryAnalysis.station_correlations(
            only_temperature, "air_temperature", "relative_humidity", pd.Timestamp("2026-08-02"))
        self.assertTrue(table.empty)


class TestOutlierSummary(unittest.TestCase):

    def test_rain_is_flagged_but_nothing_is_removed(self):
        wide = pd.DataFrame({"precipitation": [0.0] * 8 + [4.0, 10.0]})
        before = wide.copy()
        summary = ExploratoryAnalysis.outlier_summary(wide)
        # Q1 = Q3 = 0, so every rainy hour is flagged by the 1.5 IQR rule.
        self.assertEqual(summary.loc["precipitation", "above_upper"], 2)
        self.assertEqual(summary.loc["precipitation", "max"], 10.0)
        pd.testing.assert_frame_equal(wide, before)


class TestVariableSummary(unittest.TestCase):

    def test_counts_missing_values(self):
        clean = long_table("TST-ONE", 4, [10.0, np.nan, 12.0, 13.0], [50.0, 60.0, 70.0, 80.0])
        summary = ExploratoryAnalysis.variable_summary(clean)
        self.assertEqual(summary.loc["air_temperature", "missing"], 1)
        self.assertAlmostEqual(summary.loc["air_temperature", "missing_pct"], 25.0)
        self.assertEqual(summary.loc["relative_humidity", "missing"], 0)


if __name__ == "__main__":
    unittest.main()
