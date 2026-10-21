import pandas as pd

from data_loader import SiataLoader


class DataCleaner:
    """Standardizes and cleans the raw SIATA table.

    The rules (variable names, units, physical limits) are class attributes,
    so a subclass can reuse every method with different rules.
    """

    RAW_COLUMNS = SiataLoader.RAW_COLUMNS

    DATE_FORMAT = "%d/%m/%Y %I:%M:%S %p"

    KEY = ["station", "variable", "start_time"]

    VARIABLE_NAMES = {
        "Temperatura": "air_temperature",
        "Humedad Relativa": "relative_humidity",
        "Presion": "pressure",
        "Velocidad del Viento": "wind_speed",
        "Direccion del Viento": "wind_direction",
        "Precipitacion": "precipitation",
        "PM2.5": "pm25",
        "PM10": "pm10",
        "Ozono": "ozone",
        "NO": "no",
        "NO2": "no2",
        "NOx": "nox",
        "SO2": "so2",
        "CO": "co",
    }

    UNIT_LABELS = {"C": "°C", "Deg": "deg"}

    # Physical limits only: values beyond them cannot be real measurements.
    # Extreme but possible values (heavy rain, pollution peaks) are kept.
    UPPER_BOUNDS = {"relative_humidity": 100, "wind_direction": 360}
    NEGATIVE_ALLOWED = {"air_temperature"}

    def standardize(self, raw):
        """Rename to English, parse types, and keep only the analysis columns."""
        data = pd.DataFrame({
            "station": raw["NombreEstacion"].str.strip(),
            "variable": raw["Variable"].map(self.VARIABLE_NAMES),
            "unit": raw["Unidad"].replace(self.UNIT_LABELS),
            "start_time": pd.to_datetime(raw["FechaInicio"], format=self.DATE_FORMAT),
            "value": pd.to_numeric(raw["Concentracion"], errors="coerce"),
        })
        unknown = raw.loc[data["variable"].isna(), "Variable"].unique()
        if len(unknown):
            raise ValueError(f"Unknown variables: {list(unknown)}")
        return data

    def invalid_mask(self, data):
        """True where a value is outside its physically possible range."""
        below = (data["value"] < 0) & ~data["variable"].isin(self.NEGATIVE_ALLOWED)
        above = data["value"] > data["variable"].map(self.UPPER_BOUNDS)
        return below | above

    def end_time_mismatches(self, raw):
        """Count rows whose end time is not exactly one hour after the start."""
        start = pd.to_datetime(raw["FechaInicio"], format=self.DATE_FORMAT)
        end = pd.to_datetime(raw["FechaFin"], format=self.DATE_FORMAT)
        return int((end - start != pd.Timedelta(hours=1)).sum())

    def clean_data(self, raw):
        """Return the cleaned long table: one row per station, variable and hour.

        Missing values are left as NaN on purpose: imputing sensor gaps would
        invent measurements, and each analysis decides how to treat them.
        """
        data = self.standardize(raw.drop_duplicates(subset=self.RAW_COLUMNS))
        data = data.drop_duplicates(subset=self.KEY)
        data.loc[self.invalid_mask(data), "value"] = float("nan")
        return data.sort_values(self.KEY).reset_index(drop=True)

    def station_table(self, clean, station):
        """Hourly table for one station with one column per variable."""
        rows = clean[clean["station"] == station]
        return rows.pivot(index="start_time", columns="variable", values="value").rename_axis(columns=None)

    def cleaning_summary(self, raw, clean):
        """Before-and-after counts for the cleaning step."""
        standard = self.standardize(raw)
        rows = [
            ("records", len(raw), len(clean)),
            ("columns", len(self.RAW_COLUMNS), clean.shape[1]),
            ("missing_values_in_measurement", int(raw["Concentracion"].isna().sum()), int(clean["value"].isna().sum())),
            ("exact_duplicate_records", int(raw.duplicated(subset=self.RAW_COLUMNS).sum()), int(clean.duplicated().sum())),
            ("duplicated_station_variable_hour", int(standard.duplicated(subset=self.KEY).sum()), int(clean.duplicated(subset=self.KEY).sum())),
            ("physically_impossible_values", int(self.invalid_mask(standard).sum()), int(self.invalid_mask(clean).sum())),
            ("end_time_not_start_plus_one_hour", self.end_time_mismatches(raw), None),
        ]
        return pd.DataFrame(rows, columns=["check", "before", "after"]).astype({"after": "Int64"})
