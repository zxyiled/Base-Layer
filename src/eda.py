import pandas as pd

from plotting import BasePlotter, plt


class ExploratoryAnalysis(BasePlotter):
    """Descriptive tables and exploratory figures for the SIATA data."""

    @staticmethod
    def raw_column_summary(raw):
        """Type, missing values and distinct values of every raw column."""
        return pd.DataFrame({
            "dtype": raw.dtypes.astype(str),
            "missing": raw.isna().sum(),
            "missing_pct": (raw.isna().mean() * 100).round(2),
            "unique_values": raw.nunique(),
        }).rename_axis("column")

    @staticmethod
    def variable_summary(clean):
        """One row per measured variable: coverage, missing values and range."""
        groups = clean.groupby("variable")
        return pd.DataFrame({
            "unit": groups["unit"].first(),
            "stations": groups["station"].nunique(),
            "records": groups.size(),
            "missing": groups["value"].apply(lambda v: v.isna().sum()),
            "missing_pct": (groups["value"].apply(lambda v: v.isna().mean()) * 100).round(2),
            "min": groups["value"].min(),
            "median": groups["value"].median(),
            "max": groups["value"].max(),
        }).sort_values("stations", ascending=False)

    def plot_missing_by_variable(self, summary, path):
        fig, ax = plt.subplots(figsize=(8, 5))
        ordered = summary["missing_pct"].sort_values()
        ax.barh(ordered.index, ordered.values, color="tab:blue")
        ax.set_xlabel("Missing values (%)")
        ax.set_title("Missing hourly values by variable (all stations, August 2026)")
        self.save_figure(fig, path)

    @staticmethod
    def station_correlations(clean, x, y, before_time):
        """Pearson correlation between x and y per station, using hours before `before_time` only."""
        rows = []
        for station, group in clean[clean["start_time"] < before_time].groupby("station"):
            wide = group.pivot(index="start_time", columns="variable", values="value")
            if x not in wide or y not in wide:
                continue
            pairs = wide[[x, y]].dropna()
            rows.append((station, len(pairs), round(pairs[x].corr(pairs[y]), 4)))
        table = pd.DataFrame(rows, columns=["station", "complete_pairs", "pearson_r"])
        return table.sort_values("pearson_r").reset_index(drop=True)

    def plot_station_correlations(self, table, x, y, path):
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh(table["station"], table["pearson_r"], color="tab:blue")
        ax.set_xlabel("Pearson correlation coefficient r")
        ax.set_title(f"Correlation between {x.replace('_', ' ')} and {y.replace('_', ' ')} by station")
        self.save_figure(fig, path)

    @staticmethod
    def outlier_summary(wide):
        """IQR fences per variable. Values outside them are flagged, not removed."""
        q1, q3 = wide.quantile(0.25), wide.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        return pd.DataFrame({
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "lower_fence": lower,
            "upper_fence": upper,
            "below_lower": (wide < lower).sum(),
            "above_upper": (wide > upper).sum(),
            "min": wide.min(),
            "max": wide.max(),
        }).rename_axis("variable")

    def plot_boxplots(self, wide, units, path):
        fig, axes = plt.subplots(1, len(wide.columns), figsize=(3 * len(wide.columns), 4))
        for ax, column in zip(axes, wide.columns):
            ax.boxplot(wide[column].dropna())
            ax.set_title(column.replace("_", " ").capitalize())
            ax.set_ylabel(units[column])
            ax.set_xticks([])
        fig.suptitle("Outlier analysis (1.5 IQR rule)")
        self.save_figure(fig, path)

    def plot_target_distribution(self, values, label, path):
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(values.dropna(), bins=30, color="tab:blue", edgecolor="white")
        ax.axvline(values.mean(), color="black", linestyle="--", label=f"Mean = {values.mean():.2f}")
        ax.set_xlabel(label)
        ax.set_ylabel("Number of hours")
        ax.set_title(f"Distribution of {label.split(' (')[0].lower()}")
        ax.legend()
        self.save_figure(fig, path)

    def plot_correlation_matrix(self, corr, path):
        fig, ax = plt.subplots(figsize=(7, 6))
        image = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
        labels = [name.replace("_", " ") for name in corr.columns]
        ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
        ax.set_yticks(range(len(labels)), labels)
        for i in range(len(labels)):
            for j in range(len(labels)):
                ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
        fig.colorbar(image, label="Pearson r")
        ax.set_title("Correlation matrix of meteorological variables")
        self.save_figure(fig, path)

    def plot_relationship(self, wide, x, y, units, path):
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.scatter(wide[x], wide[y], s=10, alpha=0.5)
        ax.set_xlabel(self.axis_label(x, units))
        ax.set_ylabel(self.axis_label(y, units))
        ax.set_title(f"{y.replace('_', ' ').capitalize()} versus {x.replace('_', ' ')}")
        self.save_figure(fig, path)

    def plot_time_series(self, wide, columns, units, split_time, path):
        fig, axes = plt.subplots(len(columns), 1, figsize=(11, 3 * len(columns)), sharex=True)
        for ax, column in zip(axes, columns):
            ax.plot(wide.index, wide[column], linewidth=0.8)
            ax.axvline(split_time, color="red", linestyle="--", label="Train/test split")
            ax.set_ylabel(self.axis_label(column, units))
            ax.legend(loc="upper right")
        axes[0].set_title("Hourly time series, August 2026")
        axes[-1].set_xlabel("Date")
        self.save_figure(fig, path)

    def plot_diurnal_cycle(self, wide, columns, units, path):
        hourly = wide[columns].groupby(wide.index.hour).mean()
        fig, ax_left = plt.subplots(figsize=(8, 4))
        ax_left.plot(hourly.index, hourly[columns[0]], marker="o", color="tab:red")
        ax_left.set_ylabel(self.axis_label(columns[0], units), color="tab:red")
        ax_right = ax_left.twinx()
        ax_right.plot(hourly.index, hourly[columns[1]], marker="s", color="tab:blue")
        ax_right.set_ylabel(self.axis_label(columns[1], units), color="tab:blue")
        ax_left.set_xlabel("Hour of day")
        ax_left.set_xticks(range(0, 24, 2))
        ax_left.set_title("Mean diurnal cycle")
        self.save_figure(fig, path)
