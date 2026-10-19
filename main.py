import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

import pandas as pd

import eda
import evaluation
from data_cleaning import clean_data, cleaning_summary, station_table
from data_loader import load_raw
from model import (FEATURE, TARGET, chronological_split, every_third_hour, fit_simple_linear_regression,
                   model_data, predict, regression_sums_table)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_ZIP = os.path.join(PROJECT_DIR, "data", "raw", "DatosValidados_agosto2026.zip")
PROCESSED_DIR = os.path.join(PROJECT_DIR, "data", "processed")
FIGURES_DIR = os.path.join(PROJECT_DIR, "results", "figures")
TABLES_DIR = os.path.join(PROJECT_DIR, "results", "tables")

# Highest |r| between temperature and humidity in the training period with
# complete data; see results/tables/station_correlation.csv
MODEL_STATION = "BAR-PDLA"
# Train: 1-24 August (576 h). Test: 25-31 August (168 h)
SPLIT_TIME = pd.Timestamp("2026-08-25")
MANUAL_TRAIN_DAY = "2026-08-01"
MANUAL_TEST_DAY = "2026-08-25"
METEOROLOGICAL = ["air_temperature", "relative_humidity", "pressure", "wind_speed", "wind_direction", "precipitation"]


def figure_path(name):
    return os.path.join(FIGURES_DIR, name)


def save_table(table, name, index=True):
    table.to_csv(os.path.join(TABLES_DIR, name), index=index)


def run_siata_pipeline():
    for folder in (PROCESSED_DIR, FIGURES_DIR, TABLES_DIR):
        os.makedirs(folder, exist_ok=True)

    print("1. Loading the raw SIATA files...")
    raw = load_raw(RAW_ZIP)
    print(f"   {raw['source_file'].nunique()} files, {raw.shape[0]} records, {raw.shape[1] - 1} columns")
    save_table(raw.head(10), "raw_sample.csv", index=False)
    save_table(eda.raw_column_summary(raw), "raw_column_summary.csv")

    print("2. Cleaning...")
    clean = clean_data(raw)
    clean.to_csv(os.path.join(PROCESSED_DIR, "siata_clean_long.csv"), index=False)
    summary = cleaning_summary(raw, clean)
    save_table(summary, "cleaning_summary.csv", index=False)
    print(summary.to_string(index=False))

    print("3. Exploratory analysis...")
    units = dict(zip(clean["variable"], clean["unit"]))
    variables = eda.variable_summary(clean)
    save_table(variables, "variable_summary.csv")
    eda.plot_missing_by_variable(variables, figure_path("missing_values_by_variable.png"))

    correlations = eda.station_correlations(clean, FEATURE, TARGET, SPLIT_TIME)
    save_table(correlations, "station_correlation.csv", index=False)
    eda.plot_station_correlations(correlations, FEATURE, TARGET, figure_path("station_correlation.png"))

    wide = station_table(clean, MODEL_STATION)[METEOROLOGICAL]
    wide.to_csv(os.path.join(PROCESSED_DIR, f"station_{MODEL_STATION}_hourly.csv"))
    save_table(wide.describe().T, "station_descriptive_stats.csv")
    save_table(eda.outlier_summary(wide), "outlier_summary.csv")
    eda.plot_boxplots(wide, units, figure_path("outliers_boxplot.png"))
    train_corr = wide[wide.index < SPLIT_TIME].corr()
    save_table(train_corr, "correlation_matrix.csv")
    eda.plot_correlation_matrix(train_corr, figure_path("correlation_matrix.png"))
    eda.plot_target_distribution(wide[TARGET], eda.axis_label(TARGET, units), figure_path("target_distribution.png"))
    eda.plot_relationship(wide, FEATURE, TARGET, units, figure_path("temperature_vs_humidity.png"))
    eda.plot_time_series(wide, [FEATURE, TARGET], units, SPLIT_TIME, figure_path("time_series.png"))
    eda.plot_diurnal_cycle(wide, [FEATURE, TARGET], units, figure_path("diurnal_cycle.png"))

    print(f"4. Simple linear regression at {MODEL_STATION}...")
    data = model_data(wide)
    train, test = chronological_split(data, SPLIT_TIME)
    intercept, slope = fit_simple_linear_regression(train[FEATURE], train[TARGET])
    test_predicted = predict(intercept, slope, test[FEATURE])
    predictions = test.assign(predicted=test_predicted, residual=test[TARGET] - test_predicted)
    save_table(predictions, "test_predictions.csv")

    print("5. Manual example (8 real training records)...")
    sample = every_third_hour(train, MANUAL_TRAIN_DAY)
    save_table(regression_sums_table(sample[FEATURE], sample[TARGET]), "manual_regression_sample.csv")
    manual_intercept, manual_slope = fit_simple_linear_regression(sample[FEATURE], sample[TARGET])
    sample_errors = evaluation.error_table(sample[TARGET], predict(manual_intercept, manual_slope, sample[FEATURE]))
    save_table(sample_errors, "manual_sample_errors.csv")

    new_time = test.index[0]
    x_new = round(test[FEATURE].iloc[0], 2)
    coefficients = pd.DataFrame([
        ("manual_sample", len(sample), manual_intercept, manual_slope),
        ("full_training", len(train), intercept, slope),
    ], columns=["fit", "n", "intercept_b0", "slope_b1"])
    coefficients["x_new"] = x_new
    coefficients["prediction_at_x_new"] = predict(coefficients["intercept_b0"], coefficients["slope_b1"], x_new)
    coefficients["actual_at_x_new"] = round(test[TARGET].iloc[0], 2)
    coefficients["time_of_x_new"] = new_time
    save_table(coefficients, "model_coefficients.csv", index=False)
    print(coefficients.to_string(index=False))

    print("6. Evaluation...")
    metric_sample = every_third_hour(test, MANUAL_TEST_DAY)
    metric_errors = evaluation.error_table(
        metric_sample[TARGET], predict(intercept, slope, metric_sample[FEATURE]).round(2)
    )
    metric_errors.insert(0, "x", metric_sample[FEATURE])
    save_table(metric_errors, "manual_metric_sample.csv")
    save_table(pd.DataFrame([evaluation.metrics_row("manual_metric_sample", metric_errors["y"], metric_errors["y_hat"])]),
               "manual_metric_check.csv", index=False)

    baseline = [train[TARGET].mean()] * len(test)
    metrics = pd.DataFrame([
        evaluation.metrics_row("linear_regression_train", train[TARGET], predict(intercept, slope, train[FEATURE])),
        evaluation.metrics_row("linear_regression_test", test[TARGET], test_predicted),
        evaluation.metrics_row("baseline_train_mean_test", test[TARGET], baseline),
    ])
    metrics["residual_lag1_autocorrelation"] = [
        (train[TARGET] - predict(intercept, slope, train[FEATURE])).autocorr(),
        predictions["residual"].autocorr(),
        (test[TARGET] - baseline).autocorr(),
    ]
    save_table(metrics, "metrics.csv", index=False)
    print(metrics.to_string(index=False))

    label = eda.axis_label(TARGET, units).lower()
    evaluation.plot_regression_line(train, test, FEATURE, TARGET, intercept, slope, units,
                                    figure_path("regression_line.png"))
    evaluation.plot_actual_vs_predicted(test[TARGET], predictions["predicted"], label,
                                        figure_path("actual_vs_predicted.png"))
    evaluation.plot_residuals(test.index, predictions["predicted"], predictions["residual"], label,
                              figure_path("residuals.png"))
    print(f"Done. Figures in {FIGURES_DIR}, tables in {TABLES_DIR}, cleaned data in {PROCESSED_DIR}.")


if __name__ == "__main__":
    try:
        run_siata_pipeline()
    except KeyboardInterrupt:
        print("\nInterrupted.")
