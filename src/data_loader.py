import os
import zipfile
from io import BytesIO

import pandas as pd


class SiataLoader:
    """Reads the SIATA validated-data ZIP into one long table."""

    DATASET_URL = "https://siata.gov.co/IDEAM/DatosValidados_agosto2026.zip"

    RAW_COLUMNS = [
        "NombreEstacion",
        "Variable",
        "Unidad",
        "FechaInicio",
        "FechaFin",
        "FechaModificacion",
        "Concentracion",
        "MSFLCode",
    ]

    def __init__(self, zip_path):
        self.zip_path = zip_path

    def load_raw(self):
        """Read every .xls file inside the SIATA ZIP into one long table.

        The ZIP is read in place, so the original download is never modified.
        """
        if not os.path.exists(self.zip_path):
            raise FileNotFoundError(
                f"{self.zip_path} not found. Download {self.DATASET_URL} and place it in data/raw/."
            )

        frames = []
        with zipfile.ZipFile(self.zip_path) as archive:
            for name in sorted(archive.namelist()):
                if not name.endswith(".xls"):
                    continue
                frame = pd.read_excel(BytesIO(archive.read(name)), engine="xlrd")
                if list(frame.columns) != self.RAW_COLUMNS:
                    raise ValueError(f"{name} has unexpected columns: {list(frame.columns)}")
                frame["source_file"] = os.path.basename(name)
                frames.append(frame)

        if not frames:
            raise ValueError(f"No .xls files found in {self.zip_path}")
        return pd.concat(frames, ignore_index=True)
