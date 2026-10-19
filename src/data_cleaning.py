import pandas as pd

from data_loader import RAW_COLUMNS

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


def standardize(raw):
    """Rename to English, parse types, and keep only the analysis columns."""
    data = pd.DataFrame({
        "station": raw["NombreEstacion"].str.strip(),
        "variable": raw["Variable"].map(VARIABLE_NAMES),
        "unit": raw["Unidad"].replace(UNIT_LABELS),
        "start_time": pd.to_datetime(raw["FechaInicio"], format=DATE_FORMAT),
        "value": pd.to_numeric(raw["Concentracion"], errors="coerce"),
    })
    unknown = raw.loc[data["variable"].isna(), "Variable"].unique()
    if len(unknown):
        raise ValueError(f"Unknown variables: {list(unknown)}")
    return data


def invalid_mask(data):
    """True where a value is outside its physically possible range."""
    below = (data["value"] < 0) & ~data["variable"].isin(NEGATIVE_ALLOWED)
    above = data["value"] > data["variable"].map(UPPER_BOUNDS)
    return below | above


def end_time_mismatches(raw):
    """Count rows whose end time is not exactly one hour after the start."""
    start = pd.to_datetime(raw["FechaInicio"], format=DATE_FORMAT)
    end = pd.to_datetime(raw["FechaFin"], format=DATE_FORMAT)
    return int((end - start != pd.Timedelta(hours=1)).sum())


def clean_data(raw):
    """Return the cleaned long table: one row per station, variable and hour.

    Missing values are left as NaN on purpose: imputing sensor gaps would
    invent measurements, and each analysis decides how to treat them.
    """
    data = standardize(raw.drop_duplicates(subset=RAW_COLUMNS))
    data = data.drop_duplicates(subset=KEY)
    data.loc[invalid_mask(data), "value"] = float("nan")
    return data.sort_values(KEY).reset_index(drop=True)


def station_table(clean, station):
    """Hourly table for one station with one column per variable."""
    rows = clean[clean["station"] == station]
    return rows.pivot(index="start_time", columns="variable", values="value").rename_axis(columns=None)


def cleaning_summary(raw, clean):
    """Before-and-after counts for the cleaning step."""
    standard = standardize(raw)
    rows = [
        ("records", len(raw), len(clean)),
        ("columns", len(RAW_COLUMNS), clean.shape[1]),
        ("missing_values_in_measurement", int(raw["Concentracion"].isna().sum()), int(clean["value"].isna().sum())),
        ("exact_duplicate_records", int(raw.duplicated(subset=RAW_COLUMNS).sum()), int(clean.duplicated().sum())),
        ("duplicated_station_variable_hour", int(standard.duplicated(subset=KEY).sum()), int(clean.duplicated(subset=KEY).sum())),
        ("physically_impossible_values", int(invalid_mask(standard).sum()), int(invalid_mask(clean).sum())),
        ("end_time_not_start_plus_one_hour", end_time_mismatches(raw), None),
    ]
    return pd.DataFrame(rows, columns=["check", "before", "after"]).astype({"after": "Int64"})
