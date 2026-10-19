import numpy as np
import pandas as pd

FEATURE = "air_temperature"
TARGET = "relative_humidity"


def model_data(wide):
    """Keep the predictor and target; drop hours where either is missing."""
    return wide[[FEATURE, TARGET]].dropna()


def chronological_split(data, split_time):
    """Past hours train the model, later hours test it. Nothing is shuffled."""
    return data[data.index < split_time], data[data.index >= split_time]


def fit_simple_linear_regression(x, y):
    """Least-squares intercept b0 and slope b1 from the closed-form sums.

    b1 = (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²)
    b0 = ȳ - b1*x̄
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    denominator = n * np.sum(x ** 2) - np.sum(x) ** 2
    if n < 2 or denominator == 0:
        raise ValueError("Need at least two different x values to fit a line.")
    slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / denominator
    intercept = np.mean(y) - slope * np.mean(x)
    return intercept, slope


def predict(intercept, slope, x):
    return intercept + slope * np.asarray(x, dtype=float)


def every_third_hour(data, day, decimals=2):
    """The 8 records of `day` at 00, 03, ..., 21 h, rounded so they can be used by hand."""
    rows = data[(data.index.normalize() == pd.Timestamp(day)) & (data.index.hour % 3 == 0)]
    return rows.round(decimals)


def regression_sums_table(x, y):
    """Table with x, y, x² and xy plus a final row of sums, as done on paper."""
    table = pd.DataFrame({"x": x, "y": y})
    table["x_squared"] = table["x"] ** 2
    table["xy"] = table["x"] * table["y"]
    table.loc["sum"] = table.sum()
    return table
