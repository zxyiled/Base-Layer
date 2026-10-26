"""Consistency checks between the saved result tables that docs/informe.md quotes.

They only read files under results/tables/, so they do not need the raw SIATA ZIP.
Each test is skipped when the tables have not been generated yet.
"""
import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from evaluation import RegressionMetrics  # noqa: E402
from model import SimpleLinearRegression  # noqa: E402

TABLES_DIR = os.path.join(os.path.dirname(__file__), "..", "results", "tables")
SPLIT_TIME = pd.Timestamp("2026-08-25")


def read_table(name, **kwargs):
    path = os.path.join(TABLES_DIR, name)
    if not os.path.exists(path):
        raise unittest.SkipTest(f"{name} has not been generated")
    return pd.read_csv(path, **kwargs)


class TestSavedTables(unittest.TestCase):

    def test_test_metrics_match_the_saved_predictions(self):
        predictions = read_table("test_predictions.csv", index_col=0, parse_dates=True)
        metrics = read_table("metrics.csv").set_index("model").loc["linear_regression_test"]
        actual, predicted = predictions["relative_humidity"], predictions["predicted"]
        self.assertEqual(metrics["n"], len(predictions))
        self.assertAlmostEqual(metrics["mae"], RegressionMetrics.mae(actual, predicted), places=9)
        self.assertAlmostEqual(metrics["rmse"], RegressionMetrics.rmse(actual, predicted), places=9)
        self.assertAlmostEqual(metrics["r2"], RegressionMetrics.r2(actual, predicted), places=9)

    def test_predictions_are_only_from_the_test_period(self):
        predictions = read_table("test_predictions.csv", index_col=0, parse_dates=True)
        self.assertGreaterEqual(predictions.index.min(), SPLIT_TIME)
        self.assertTrue(predictions.index.is_monotonic_increasing)

    def test_manual_coefficients_match_the_sums_table(self):
        table = read_table("manual_regression_sample.csv", index_col=0)
        sums = table.loc["sum"]
        n = len(table) - 1
        slope = (n * sums["xy"] - sums["x"] * sums["y"]) / (n * sums["x_squared"] - sums["x"] ** 2)
        intercept = sums["y"] / n - slope * sums["x"] / n
        saved = read_table("model_coefficients.csv").set_index("fit").loc["manual_sample"]
        self.assertAlmostEqual(slope, saved["slope_b1"], places=9)
        self.assertAlmostEqual(intercept, saved["intercept_b0"], places=9)

    def test_manual_sample_refits_to_the_saved_coefficients(self):
        sample = read_table("manual_regression_sample.csv", index_col=0).drop("sum")
        model = SimpleLinearRegression().fit(sample["x"], sample["y"])
        saved = read_table("model_coefficients.csv").set_index("fit").loc["manual_sample"]
        self.assertAlmostEqual(model.slope, saved["slope_b1"], places=9)
        self.assertAlmostEqual(model.intercept, saved["intercept_b0"], places=9)

    def test_manual_metric_check_matches_the_error_table(self):
        errors = read_table("manual_metric_sample.csv")
        check = read_table("manual_metric_check.csv").iloc[0]
        self.assertEqual(check["n"], len(errors))
        self.assertAlmostEqual(check["mae"], errors["abs_error"].mean(), places=9)
        self.assertAlmostEqual(check["mse"], errors["squared_error"].mean(), places=9)

    def test_prediction_for_the_new_input_uses_each_saved_line(self):
        coefficients = read_table("model_coefficients.csv")
        expected = coefficients["intercept_b0"] + coefficients["slope_b1"] * coefficients["x_new"]
        pd.testing.assert_series_equal(coefficients["prediction_at_x_new"], expected, check_names=False)


if __name__ == "__main__":
    unittest.main()
