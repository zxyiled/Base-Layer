# Dataset columns in display order, with the type used to parse their values
# (the API returns every value as a string)
COLUMNS = {
    "ano": int,
    "mes": int,
    "fuente": str,
    "promedio_mensual_gwh": float,
    "maximo_gwh": float,
    "minimo_gwh": float,
    "generacion_total_gwh": float,
    "porcentaje_participacion": float,
}


def head(records, n=5):
    return records[:max(n, 0)]


def tail(records, n=5):
    return records[max(len(records) - n, 0):]


def column_values(records, column):
    parse = COLUMNS[column]
    return [parse(record[column]) for record in records]


def round_values(values, decimals):
    # Round floats to `decimals` places; with 0 decimals they become ints.
    if decimals == 0:
        return [round(value) for value in values]
    return [round(value, decimals) for value in values]


def _format_value(value):
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def format_table(records, columns):
    rows = [
        [_format_value(value) for value in values]
        for values in zip(*(column_values(records, column) for column in columns))
    ]
    widths = [
        max([len(column)] + [len(row[i]) for row in rows])
        for i, column in enumerate(columns)
    ]

    lines = [
        "  ".join(column.ljust(width) for column, width in zip(columns, widths)),
        "  ".join("-" * width for width in widths),
    ]
    for row in rows:
        lines.append("  ".join(cell.ljust(width) for cell, width in zip(row, widths)))
    return "\n".join(lines)
