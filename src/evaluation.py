import numpy as np
import pandas as pd

from eda import axis_label, plt, save_figure


def mae(actual, predicted):
    return float(np.mean(np.abs(np.asarray(actual) - np.asarray(predicted))))


def mse(actual, predicted):
    return float(np.mean((np.asarray(actual) - np.asarray(predicted)) ** 2))


def rmse(actual, predicted):
    return float(np.sqrt(mse(actual, predicted)))


def r2(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    residual = np.sum((actual - np.asarray(predicted)) ** 2)
    total = np.sum((actual - actual.mean()) ** 2)
    return float(1 - residual / total)


def metrics_row(name, actual, predicted):
    return {
        "model": name,
        "n": len(actual),
        "mae": mae(actual, predicted),
        "mse": mse(actual, predicted),
        "rmse": rmse(actual, predicted),
        "r2": r2(actual, predicted),
    }


def error_table(actual, predicted):
    """Per-record errors used for the manual metric calculation."""
    table = pd.DataFrame({"y": actual, "y_hat": predicted})
    table["error"] = table["y"] - table["y_hat"]
    table["abs_error"] = table["error"].abs()
    table["squared_error"] = table["error"] ** 2
    return table


def plot_regression_line(train, test, x, y, intercept, slope, units, path):
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(train[x], train[y], s=10, alpha=0.4, label="Training hours")
    ax.scatter(test[x], test[y], s=10, alpha=0.6, color="tab:orange", label="Test hours")
    line_x = np.linspace(min(train[x].min(), test[x].min()), max(train[x].max(), test[x].max()), 100)
    ax.plot(line_x, intercept + slope * line_x, color="black", label=f"ŷ = {intercept:.2f} + ({slope:.2f})x")
    ax.set_xlabel(axis_label(x, units))
    ax.set_ylabel(axis_label(y, units))
    ax.set_title("Fitted simple linear regression")
    ax.legend()
    save_figure(fig, path)


def plot_actual_vs_predicted(actual, predicted, label, path):
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(actual, predicted, s=12, alpha=0.6)
    low, high = min(actual.min(), predicted.min()), max(actual.max(), predicted.max())
    ax.plot([low, high], [low, high], color="black", linestyle="--", label="Perfect prediction")
    ax.set_xlabel(f"Actual {label}")
    ax.set_ylabel(f"Predicted {label}")
    ax.set_title("Actual versus predicted values (test set)")
    ax.legend()
    save_figure(fig, path)


def plot_residuals(times, predicted, residuals, label, path):
    fig, (ax_time, ax_fit) = plt.subplots(1, 2, figsize=(12, 4))
    ax_time.plot(times, residuals, linewidth=0.8)
    ax_time.axhline(0, color="black", linestyle="--")
    ax_time.set_xlabel("Date")
    ax_time.set_ylabel(f"Residual {label}")
    ax_time.set_title("Residuals over time (test set)")
    ax_time.tick_params(axis="x", rotation=30)
    ax_fit.scatter(predicted, residuals, s=12, alpha=0.6)
    ax_fit.axhline(0, color="black", linestyle="--")
    ax_fit.set_xlabel(f"Predicted {label}")
    ax_fit.set_ylabel(f"Residual {label}")
    ax_fit.set_title("Residuals versus predicted values (test set)")
    save_figure(fig, path)
