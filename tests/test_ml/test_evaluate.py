from PIL import Image

import evaluate
from common import collect_real_test

LABELS = ["fresa", "limon"]


class _UnusedPredictor:
    labels = LABELS


def test_real_test_is_pending_when_folder_is_missing(tmp_path):
    result = evaluate.evaluate_real(_UnusedPredictor(), tmp_path / "real_test", batch_size=4)
    assert result["status"] == evaluate.PENDING


def test_collect_real_test_ignores_unknown_folders_and_files(tmp_path):
    (tmp_path / "fresa").mkdir()
    (tmp_path / "kiwi").mkdir()
    Image.new("RGB", (20, 20)).save(tmp_path / "fresa" / "foto1.jpg")
    (tmp_path / "fresa" / "notas.txt").write_text("x")
    samples, ignored = collect_real_test(LABELS, tmp_path)
    assert samples == [(tmp_path / "fresa" / "foto1.jpg", 0)]
    assert ignored == ["kiwi"]


def test_compute_metrics_reports_per_class_values():
    metrics = evaluate.compute_metrics([0, 0, 1, 1], [0, 1, 1, 1], LABELS)
    assert metrics["accuracy"] == 0.75
    assert metrics["per_class"]["fresa"]["recall"] == 0.5
    assert metrics["confusion_matrix"] == [[1, 1], [0, 2]]
