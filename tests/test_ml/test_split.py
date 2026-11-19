from collections import defaultdict

import pytest

import prepare_subset
from prepare_subset import GAP, MANIFEST_PATH, parse_index, split_indices


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("31_100.jpg", 31), ("r_31_100.jpg", 31), ("r2_31_100.jpg", 31), ("r0_7_100.jpg", 7), ("thumbs.db", None), ("31_50.jpg", None)],
)
def test_parse_index(filename, expected):
    assert parse_index(filename) == expected


def test_split_indices_blocks_are_disjoint_and_separated_by_gap():
    indices = list(range(0, 330, 1)) + list(range(400, 420))
    train, val = split_indices(indices, val_fraction=0.15, gap=GAP)
    assert train and val
    assert not train & val
    assert max(train) < min(val) - GAP
    assert all(index > max(train) + GAP for index in val)


def test_split_indices_handles_holes_in_indices():
    indices = [0, 1, 2, 50, 51, 52, 53, 54, 90, 91, 92, 95, 99]
    train, val = split_indices(indices, val_fraction=0.3, gap=5)
    assert max(train) < min(val) - 5


def test_rotated_variants_share_split(tmp_path):
    variety = tmp_path / "Training" / "Lemon 1"
    variety.mkdir(parents=True)
    for n in range(60):
        for prefix in ("", "r_", "r2_"):
            (variety / f"{prefix}{n}_100.jpg").touch()
    rows = prepare_subset.rows_for_training_variety(tmp_path, "limon", "Lemon 1")
    splits_by_index = defaultdict(set)
    for row in rows:
        splits_by_index[row["index"]].add(row["split"])
    assert all(len(splits) == 1 for splits in splits_by_index.values())
    assert {"train", "val"} == {split for splits in splits_by_index.values() for split in splits}


def test_find_varieties_excludes_grapefruit_and_non_whole_fruit(tmp_path):
    for name in ("Grape 1", "Grapefruit Pink 1", "grape pink 3", "Orange 1", "Orange peeled 1", "Strawberry Wedge 1"):
        (tmp_path / name).mkdir()
    varieties = prepare_subset.find_varieties(tmp_path)
    assert varieties["uva"] == ["Grape 1", "grape pink 3"]
    assert varieties["naranja"] == ["Orange 1"]
    assert varieties["fresa"] == []


@pytest.mark.skipif(not MANIFEST_PATH.is_file(), reason="manifest not built yet")
def test_versioned_manifest_has_no_leakage():
    import csv

    with MANIFEST_PATH.open(encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    indices = defaultdict(lambda: defaultdict(set))
    for row in rows:
        indices[row["variety"]][row["split"]].add(int(row["index"]))
        expected_root = "Test/" if row["split"] == "test" else "Training/"
        assert row["path"].startswith(expected_root)
    for variety, by_split in indices.items():
        train, val = by_split["train"], by_split["val"]
        assert not train & val, variety
        if train and val:
            assert max(train) < min(val) - GAP, variety
