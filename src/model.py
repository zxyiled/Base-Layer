import numpy as np
import pandas as pd

FEATURE = "air_temperature"
TARGET = "relative_humidity"


class ModelDataPreparer:
    """Prepares the hourly table for modelling: selection, split and manual samples."""

    def __init__(self, feature=FEATURE, target=TARGET):
        self.feature = feature
        self.target = target

    def model_data(self, wide):
        """Keep the predictor and target; drop hours where either is missing."""
        return wide[[self.feature, self.target]].dropna()

    @staticmethod
    def chronological_split(data, split_time):
        """Past hours train the model, later hours test it. Nothing is shuffled."""
        return data[data.index < split_time], data[data.index >= split_time]

    @staticmethod
    def every_third_hour(data, day, decimals=2):
        """The 8 records of `day` at 00, 03, ..., 21 h, rounded so they can be used by hand."""
        rows = data[(data.index.normalize() == pd.Timestamp(day)) & (data.index.hour % 3 == 0)]
        return rows.round(decimals)

    @staticmethod
    def regression_sums_table(x, y):
        """Table with x, y, x² and xy plus a final row of sums, as done on paper."""
        table = pd.DataFrame({"x": x, "y": y})
        table["x_squared"] = table["x"] ** 2
        table["xy"] = table["x"] * table["y"]
        table.loc["sum"] = table.sum()
        return table


class SimpleLinearRegression:
    """Simple linear regression y = b0 + b1*x fitted by least squares."""

    def __init__(self):
        self.intercept = None
        self.slope = None

    def fit(self, x, y):
        """Least-squares intercept b0 and slope b1 from the closed-form sums.

        b1 = (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²)
        b0 = ȳ - b1*x̄
        """
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        n = len(x)
        # A constant x gives 0/0, but with decimals the formula's denominator is
        # only approximately 0 because of rounding, so test for it directly.
        if n < 2 or np.ptp(x) == 0:
            raise ValueError("Need at least two different x values to fit a line.")
        denominator = n * np.sum(x ** 2) - np.sum(x) ** 2
        self.slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / denominator
        self.intercept = np.mean(y) - self.slope * np.mean(x)
        return self

    @staticmethod
    def predict_line(intercept, slope, x):
        return intercept + slope * np.asarray(x, dtype=float)

    def predict(self, x):
        if self.intercept is None or self.slope is None:
            raise ValueError("The model must be fitted before predicting.")
        return self.predict_line(self.intercept, self.slope, x)
