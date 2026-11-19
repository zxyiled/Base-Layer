"""Build the 8-fruit subset of Fruits-360 and write a small manifest.

Only the folders of the chosen varieties are read (never all of data/raw/).

Leak-free split rule (per variety folder of Training/):
  * Images are frames of short videos, named N_100.jpg, r_N_100.jpg,
    r2_N_100.jpg... All files sharing the same index N stay together.
  * The unique indices are sorted; the last VAL_FRACTION of them form the
    validation block. Training keeps only indices N < min(val) - GAP, so a
    safety gap of GAP index values separates both blocks (dropped files).
  * Test/ is the official test split and is never used for training or tuning.
Balance: training and validation are subsampled per fruit with a fixed seed.

Usage: uv run python ml_training/prepare_subset.py
"""

import argparse
import csv
import json
import logging
import math
import os
import random
import re
from collections import Counter
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_DIR = ROOT_DIR / "data" / "raw" / "fruits-360"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
MANIFEST_PATH = PROCESSED_DIR / "manifest.csv"
MANIFEST_INFO_PATH = PROCESSED_DIR / "manifest_info.json"

# Label -> Fruits-360 folder prefix. Folders are matched as "<prefix> <rest>",
# case-insensitive, so "Grape" does not match "Grapefruit".
FRUIT_PREFIXES = {
    "banano": "Banana",
    "fresa": "Strawberry",
    "limon": "Lemon",
    "manzana": "Apple",
    "naranja": "Orange",
    "pera": "Pear",
    "tomate": "Tomato",
    "uva": "Grape",
}
# Not a whole fruit with its skin (decided with the project owner).
EXCLUDED_VARIETIES = {"Orange peeled 1", "Strawberry Wedge 1"}

VAL_FRACTION = 0.15
GAP = 10
MAX_TRAIN_PER_FRUIT = 1200
MAX_VAL_PER_FRUIT = 300
SEED = 42

FILENAME_PATTERN = re.compile(r"^(?:r\d*_)?(\d+)_100\.jpg$")
MANIFEST_FIELDS = ["path", "fruit", "variety", "split", "index"]

logger = logging.getLogger("prepare_subset")


def parse_index(filename: str) -> int | None:
    """Return the frame index N of a Fruits-360 file name, or None if it does not match."""
    match = FILENAME_PATTERN.match(filename)
    return int(match.group(1)) if match else None


def find_varieties(split_dir: Path) -> dict[str, list[str]]:
    """Map each fruit label to its variety folder names inside ``split_dir``."""
    folder_names = sorted(entry.name for entry in os.scandir(split_dir) if entry.is_dir())
    varieties: dict[str, list[str]] = {}
    for label, prefix in FRUIT_PREFIXES.items():
        varieties[label] = [
            name
            for name in folder_names
            if name.lower().startswith(prefix.lower() + " ") and name not in EXCLUDED_VARIETIES
        ]
    return varieties


def split_indices(indices: Iterable[int], val_fraction: float = VAL_FRACTION, gap: int = GAP) -> tuple[set[int], set[int]]:
    """Split frame indices into (train, val) contiguous blocks separated by ``gap``."""
    unique = sorted(set(indices))
    if not unique:
        return set(), set()
    n_val = max(1, math.ceil(len(unique) * val_fraction))
    val = set(unique[-n_val:])
    val_start = min(val)
    train = {index for index in unique[:-n_val] if index < val_start - gap}
    return train, val


def list_images(folder: Path) -> list[tuple[str, int]]:
    """Return (filename, index) for the valid image files of one variety folder."""
    images = []
    for entry in os.scandir(folder):
        if not entry.is_file():
            continue
        index = parse_index(entry.name)
        if index is None:
            logger.warning("Skipping unexpected file name: %s/%s", folder.name, entry.name)
            continue
        images.append((entry.name, index))
    return sorted(images, key=lambda item: (item[1], item[0]))


def make_row(split_name: str, variety: str, filename: str, fruit: str, split: str, index: int) -> dict:
    return {
        "path": f"{split_name}/{variety}/{filename}",
        "fruit": fruit,
        "variety": variety,
        "split": split,
        "index": index,
    }


def rows_for_training_variety(dataset_dir: Path, fruit: str, variety: str) -> list[dict]:
    """Assign train/val to the files of one Training/ variety folder (gap files dropped)."""
    images = list_images(dataset_dir / "Training" / variety)
    train, val = split_indices(index for _, index in images)
    rows = []
    for filename, index in images:
        split = "train" if index in train else "val" if index in val else None
        if split:
            rows.append(make_row("Training", variety, filename, fruit, split, index))
    return rows


def rows_for_test_variety(dataset_dir: Path, fruit: str, variety: str) -> list[dict]:
    images = list_images(dataset_dir / "Test" / variety)
    return [make_row("Test", variety, filename, fruit, "test", index) for filename, index in images]


def subsample(rows: list[dict], split: str, max_per_fruit: int, rng: random.Random) -> list[dict]:
    """Keep at most ``max_per_fruit`` rows of ``split`` per fruit (other rows untouched)."""
    kept = [row for row in rows if row["split"] != split]
    for fruit in FRUIT_PREFIXES:
        candidates = [row for row in rows if row["split"] == split and row["fruit"] == fruit]
        if len(candidates) > max_per_fruit:
            candidates = rng.sample(candidates, max_per_fruit)
        kept.extend(candidates)
    return kept


def count_by_fruit_and_split(rows: list[dict]) -> dict[str, dict[str, int]]:
    counter = Counter((row["fruit"], row["split"]) for row in rows)
    return {
        fruit: {split: counter[(fruit, split)] for split in ("train", "val", "test")}
        for fruit in FRUIT_PREFIXES
    }


def build_manifest(dataset_dir: Path, seed: int = SEED) -> tuple[list[dict], dict]:
    """Return the manifest rows and the metadata describing how they were built."""
    training_varieties = find_varieties(dataset_dir / "Training")
    test_varieties = find_varieties(dataset_dir / "Test")
    rows: list[dict] = []
    for fruit, varieties in training_varieties.items():
        if not varieties:
            raise ValueError(f"No variety folders found for fruit '{fruit}'")
        for variety in varieties:
            rows.extend(rows_for_training_variety(dataset_dir, fruit, variety))
        for variety in test_varieties[fruit]:
            rows.extend(rows_for_test_variety(dataset_dir, fruit, variety))

    before_subsampling = count_by_fruit_and_split(rows)
    rng = random.Random(seed)
    rows = subsample(rows, "train", MAX_TRAIN_PER_FRUIT, rng)
    rows = subsample(rows, "val", MAX_VAL_PER_FRUIT, rng)
    rows.sort(key=lambda row: (row["split"], row["fruit"], row["variety"], row["index"], row["path"]))

    info = {
        "dataset": "Fruits-360 (100x100), Mihai Oltean, CC BY-SA 4.0",
        "labels": sorted(FRUIT_PREFIXES),
        "fruit_prefixes": FRUIT_PREFIXES,
        "excluded_varieties": sorted(EXCLUDED_VARIETIES),
        "varieties": {"Training": training_varieties, "Test": test_varieties},
        "split_rule": {
            "description": (
                "Per Training/ variety: sort unique frame indices N; the last val_fraction "
                "of them is validation; training keeps only N < min(val N) - gap. All files "
                "with the same N (N_100, r_N_100, r2_N_100...) share a split. Test/ is the "
                "official test split."
            ),
            "val_fraction": VAL_FRACTION,
            "gap": GAP,
        },
        "balance": {
            "max_train_per_fruit": MAX_TRAIN_PER_FRUIT,
            "max_val_per_fruit": MAX_VAL_PER_FRUIT,
            "seed": seed,
            "note": "Test is not subsampled. Remaining imbalance is handled by WeightedRandomSampler.",
        },
        "counts_before_subsampling": before_subsampling,
        "counts": count_by_fruit_and_split(rows),
    }
    return rows, info


def write_outputs(rows: list[dict], info: dict) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    MANIFEST_INFO_PATH.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")


def log_counts(counts: dict[str, dict[str, int]]) -> None:
    logger.info("%-10s %7s %7s %7s", "fruit", "train", "val", "test")
    for fruit, by_split in counts.items():
        logger.info("%-10s %7d %7d %7d", fruit, by_split["train"], by_split["val"], by_split["test"])


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset-dir", type=Path, default=Path(os.environ.get("DATASET_DIR", DEFAULT_DATASET_DIR)))
    args = parser.parse_args()

    rows, info = build_manifest(args.dataset_dir)
    write_outputs(rows, info)
    log_counts(info["counts"])
    logger.info("Manifest written to %s (%d rows)", MANIFEST_PATH, len(rows))


if __name__ == "__main__":
    main()
