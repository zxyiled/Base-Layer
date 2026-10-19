# SIATA temperature and humidity analysis

Analyze SIATA's validated August 2026 weather data and estimate relative humidity from air temperature using simple linear regression at station `BAR-PDLA`. The pipeline loads and cleans the data, generates exploratory plots, fits the model, and evaluates it against a training-mean baseline.

## Requirements

- Python 3.10 or newer.
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for dependency and virtual-environment management.
- Internet access to install dependencies and download the dataset. Once both are available locally, the analysis runs offline.

Run the following commands from the project root (the directory containing `main.py` and `pyproject.toml`).

## 1. Install dependencies

```sh
uv sync --frozen
```

This creates `.venv/` and installs the versions recorded in `uv.lock`, including the development dependencies used for testing. No manual virtual-environment activation is needed when using `uv run`.

## 2. Download the dataset

The raw data is not included in the repository. On Linux or macOS, download it with:

```sh
mkdir -p data/raw
curl --fail --location https://siata.gov.co/IDEAM/DatosValidados_agosto2026.zip \
  --output data/raw/DatosValidados_agosto2026.zip
```

Alternatively, download the [SIATA ZIP file](https://siata.gov.co/IDEAM/DatosValidados_agosto2026.zip) in a browser and place it at:

```text
data/raw/DatosValidados_agosto2026.zip
```

Keep the filename unchanged and **do not extract the ZIP**: the loader reads its `.xls` files directly. The application does not download the dataset automatically.

## 3. Run the analysis

```sh
uv run python main.py
```

No command-line arguments are required. The pipeline prints its progress, fitted coefficients, and evaluation metrics to the terminal. It trains on August 1–24 and evaluates on August 25–31, 2026.

Generated files are written to these directories, which are created automatically:

| Directory | Contents |
| --- | --- |
| `data/processed/` | Cleaned observations and the selected station's hourly data |
| `results/tables/` | CSV summaries, model coefficients, predictions, evaluation metrics, and manual calculation examples |
| `results/figures/` | PNG exploratory, regression, and residual plots |

Plots are saved to disk rather than displayed in a window, so no graphical desktop is required. Running the pipeline again overwrites outputs with the same filenames; the raw ZIP is left unchanged.

If execution fails with `FileNotFoundError`, check that the ZIP is at the exact path shown above.

## Run the tests

```sh
uv run pytest
```

## Project layout

- `main.py`: runs the complete analysis pipeline.
- `src/`: data loading, cleaning, exploratory analysis, regression, and evaluation.
- `tests/`: automated tests.
- `docs/informe.md`: analysis report, if available in your checkout.
