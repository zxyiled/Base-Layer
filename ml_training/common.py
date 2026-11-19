"""Shared helpers for training and evaluation: paths, seeds and datasets."""

import csv
import os
import random
import sys
from pathlib import Path
from typing import Callable

import torch
from PIL import Image
from torch.utils.data import Dataset

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:  # allow "uv run python ml_training/<script>.py"
    sys.path.insert(0, str(ROOT_DIR))

DEFAULT_DATASET_DIR = Path(os.environ.get("DATASET_DIR", ROOT_DIR / "data" / "raw" / "fruits-360"))
MANIFEST_PATH = ROOT_DIR / "data" / "processed" / "manifest.csv"
REAL_TEST_DIR = ROOT_DIR / "data" / "real_test"
ARTIFACTS_DIR = ROOT_DIR / "app" / "ml" / "artifacts"
REPORTS_DIR = ROOT_DIR / "ml_training" / "reports"
HISTORY_PATH = REPORTS_DIR / "history.json"
SEED = 42
REAL_TEST_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def set_seed(seed: int = SEED) -> None:
    """Fix the seeds of random and torch."""
    random.seed(seed)
    torch.manual_seed(seed)


def load_manifest(split: str, manifest_path: Path = MANIFEST_PATH) -> list[dict]:
    """Return the manifest rows of one split (train, val or test)."""
    if not manifest_path.is_file():
        raise FileNotFoundError(f"{manifest_path} not found: run ml_training/prepare_subset.py first")
    with manifest_path.open(encoding="utf-8") as file:
        return [row for row in csv.DictReader(file) if row["split"] == split]


class ImageListDataset(Dataset):
    """Dataset over (image path, label index) pairs."""

    def __init__(self, samples: list[tuple[Path, int]], transform: Callable) -> None:
        self.samples = samples
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, position: int) -> tuple[torch.Tensor, int]:
        path, target = self.samples[position]
        with Image.open(path) as image:
            return self.transform(image), target


def manifest_dataset(rows: list[dict], labels: list[str], dataset_dir: Path, transform: Callable) -> ImageListDataset:
    """Build a dataset from manifest rows (paths are relative to ``dataset_dir``)."""
    label_to_index = {label: index for index, label in enumerate(labels)}
    samples = [(dataset_dir / row["path"], label_to_index[row["fruit"]]) for row in rows]
    return ImageListDataset(samples, transform)


def collect_real_test(labels: list[str], real_test_dir: Path = REAL_TEST_DIR) -> tuple[list[tuple[Path, int]], list[str]]:
    """Return (samples, ignored folders) from ``data/real_test/<label>/``.

    A missing folder yields no samples; folders that are not a known label are ignored.
    """
    if not real_test_dir.is_dir():
        return [], []
    label_to_index = {label: index for index, label in enumerate(labels)}
    samples, ignored = [], []
    for folder in sorted(path for path in real_test_dir.iterdir() if path.is_dir()):
        if folder.name not in label_to_index:
            ignored.append(folder.name)
            continue
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() in REAL_TEST_EXTENSIONS:
                samples.append((path, label_to_index[folder.name]))
    return samples, ignored
