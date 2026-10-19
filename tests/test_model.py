import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from evaluation import error_table, mae, mse, r2, rmse  # noqa: E402
from model import (FEATURE, TARGET, chronological_split, every_third_hour,  # noqa: E402
                   fit_simple_linear_regression, predict, regression_sums_table)


class TestLinearRegression(unittest.TestCase):

    def test_recovers_an_exact_line(self):
        x = [1.0, 2.0, 3.0, 4.0]
        intercept, slope = fit_simple_linear_regression(x, [5.0, 8.0, 11.0, 14.0])
        self.assertAlmostEqual(intercept, 2.0)
        self.assertAlmostEqual(slope, 3.0)

    def test_matches_numpy_least_squares(self):
        rng = np.random.default_rng(0)
        x = rng.uniform(15, 30, 50)
        y = 170 - 4.5 * x + rng.normal(0, 5, 50)
        expected_slope, expected_intercept = np.polyfit(x, y, 1)
        intercept, slope = fit_simple_linear_regression(x, y)
        self.assertAlmostEqual(intercept, expected_intercept)
        self.assertAlmostEqual(slope, expected_slope)

    def test_hand_calculated_example(self):
        # x̄ = 2, ȳ = 3, Σ(x-x̄)(y-ȳ) = 4, Σ(x-x̄)² = 2 -> b1 = 2, b0 = -1
        intercept, slope = fit_simple_linear_regression([1, 2, 3], [1, 3, 5])
        self.assertAlmostEqual(slope, 2.0)
        self.assertAlmostEqual(intercept, -1.0)
        np.testing.assert_allclose(predict(intercept, slope, [4]), [7.0])

    def test_constant_x_is_rejected(self):
        with self.assertRaises(ValueError):
            fit_simple_linear_regression([2, 2, 2], [1, 2, 3])

    def test_sums_table(self):
        table = regression_sums_table([1.0, 2.0], [3.0, 4.0])
        self.assertEqual(table.loc["sum"].tolist(), [3.0, 7.0, 5.0, 11.0])


class TestSplitAndSampling(unittest.TestCase):

    def setUp(self):
        times = pd.date_range("2026-08-01", periods=72, freq="h")
        self.data = pd.DataFrame({FEATURE: np.arange(72.0), TARGET: np.arange(72.0) * 2}, index=times)

    def test_chronological_split_keeps_past_before_future(self):
        train, test = chronological_split(self.data, pd.Timestamp("2026-08-03"))
        self.assertEqual((len(train), len(test)), (48, 24))
        self.assertLess(train.index.max(), test.index.min())

    def test_every_third_hour_takes_eight_records_of_the_day(self):
        sample = every_third_hour(self.data, "2026-08-02")
        self.assertEqual(list(sample.index.hour), [0, 3, 6, 9, 12, 15, 18, 21])
        self.assertTrue((sample.index.day == 2).all())


class TestMetrics(unittest.TestCase):

    def test_known_values(self):
        actual, predicted = [3.0, 5.0, 7.0], [2.0, 5.0, 9.0]
        self.assertAlmostEqual(mae(actual, predicted), 1.0)
        self.assertAlmostEqual(mse(actual, predicted), 5.0 / 3)
        self.assertAlmostEqual(rmse(actual, predicted), np.sqrt(5.0 / 3))
        # SSres = 5, SStot = 8
        self.assertAlmostEqual(r2(actual, predicted), 1 - 5.0 / 8)

    def test_perfect_prediction(self):
        self.assertEqual(r2([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]), 1.0)
        self.assertEqual(mae([1.0, 2.0], [1.0, 2.0]), 0.0)

    def test_error_table(self):
        table = error_table([10.0, 20.0], [12.0, 17.0])
        self.assertEqual(table["error"].tolist(), [-2.0, 3.0])
        self.assertEqual(table["squared_error"].tolist(), [4.0, 9.0])


if __name__ == "__main__":
    unittest.main()
