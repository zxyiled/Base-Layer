"""Evaluate the trained model on the official test (Fruits-360 Test/) and on real photos.

Real photos live in data/real_test/<label>/. If the folder is missing or empty,
the real test is reported as "pendiente". Both tests are reported separately.

Outputs (ml_training/reports/): metrics.json, summary.md,
confusion_matrix_official.png, confusion_matrix_real.png, training_curves.png.

Usage: uv run python ml_training/evaluate.py
"""

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import torch  # noqa: E402
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support  # noqa: E402
from torch.utils.data import DataLoader  # noqa: E402

from common import (  # noqa: E402
    ARTIFACTS_DIR,
    DEFAULT_DATASET_DIR,
    HISTORY_PATH,
    REAL_TEST_DIR,
    REPORTS_DIR,
    ROOT_DIR,
    ImageListDataset,
    collect_real_test,
    load_manifest,
    manifest_dataset,
)
from app.ml.predictor import Predictor  # noqa: E402
from app.ml.preprocessing import build_eval_transform  # noqa: E402

logger = logging.getLogger("evaluate")
PENDING = "pendiente"


def predict_dataset(predictor: Predictor, dataset: ImageListDataset, batch_size: int, num_workers: int) -> tuple[list[int], list[int]]:
    """Return (true labels, predicted labels) for every sample of ``dataset``."""
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    y_true, y_pred = [], []
    for images, targets in loader:
        y_pred.extend(predictor.predict_probabilities(images).argmax(dim=1).tolist())
        y_true.extend(targets.tolist())
    return y_true, y_pred


def compute_metrics(y_true: list[int], y_pred: list[int], labels: list[str]) -> dict:
    """Accuracy, per-class precision/recall/F1/support, macro averages and confusion matrix."""
    indices = list(range(len(labels)))
    precision, recall, f1, support = precision_recall_fscore_support(y_true, y_pred, labels=indices, zero_division=0)
    macro = precision_recall_fscore_support(y_true, y_pred, labels=indices, average="macro", zero_division=0)
    return {
        "samples": len(y_true),
        "accuracy": accuracy_score(y_true, y_pred),
        "macro_precision": macro[0],
        "macro_recall": macro[1],
        "macro_f1": macro[2],
        "per_class": {
            label: {"precision": float(precision[i]), "recall": float(recall[i]), "f1": float(f1[i]), "support": int(support[i])}
            for i, label in enumerate(labels)
        },
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=indices).tolist(),
    }


def accuracy_by_variety(rows: list[dict], y_true: list[int], y_pred: list[int]) -> dict[str, dict]:
    """Accuracy per Fruits-360 variety folder, sorted from worst to best."""
    hits: dict[str, list[int]] = defaultdict(list)
    for row, true, pred in zip(rows, y_true, y_pred):
        hits[row["variety"]].append(int(true == pred))
    result = {variety: {"accuracy": sum(v) / len(v), "samples": len(v)} for variety, v in hits.items()}
    return dict(sorted(result.items(), key=lambda item: item[1]["accuracy"]))


def plot_confusion_matrix(matrix: list[list[int]], labels: list[str], title: str, path: Path) -> None:
    figure, axis = plt.subplots(figsize=(7, 6))
    image = axis.imshow(matrix, cmap="Blues")
    axis.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
    axis.set_yticks(range(len(labels)), labels)
    axis.set_xlabel("Predicción")
    axis.set_ylabel("Real")
    axis.set_title(title)
    peak = max(max(row) for row in matrix) or 1
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            axis.text(j, i, value, ha="center", va="center", fontsize=8, color="white" if value > peak / 2 else "black")
    figure.colorbar(image, ax=axis)
    figure.tight_layout()
    figure.savefig(path, dpi=120)
    plt.close(figure)


def plot_training_curves(history: list[dict], path: Path) -> None:
    epochs = [entry["epoch"] for entry in history]
    figure, (loss_axis, acc_axis) = plt.subplots(1, 2, figsize=(11, 4))
    for axis, metric, title in ((loss_axis, "loss", "Pérdida"), (acc_axis, "accuracy", "Accuracy")):
        axis.plot(epochs, [e[f"train_{metric}"] for e in history], marker="o", label="entrenamiento")
        axis.plot(epochs, [e[f"val_{metric}"] for e in history], marker="o", label="validación")
        finetune = [e["epoch"] for e in history if e["stage"] == "finetune"]
        if finetune:
            axis.axvline(finetune[0] - 0.5, color="gray", linestyle="--", label="inicio fine-tuning")
        axis.set_xlabel("Época")
        axis.set_title(title)
        axis.legend()
        axis.grid(alpha=0.3)
    figure.tight_layout()
    figure.savefig(path, dpi=120)
    plt.close(figure)


def evaluate_official(predictor: Predictor, dataset_dir: Path, batch_size: int, num_workers: int) -> dict:
    rows = load_manifest("test")
    dataset = manifest_dataset(rows, predictor.labels, dataset_dir, build_eval_transform())
    y_true, y_pred = predict_dataset(predictor, dataset, batch_size, num_workers)
    metrics = compute_metrics(y_true, y_pred, predictor.labels)
    metrics["accuracy_by_variety"] = accuracy_by_variety(rows, y_true, y_pred)
    plot_confusion_matrix(metrics["confusion_matrix"], predictor.labels, "Prueba oficial (Fruits-360 Test)",
                          REPORTS_DIR / "confusion_matrix_official.png")
    return {"status": "ok", **metrics}


def evaluate_real(predictor: Predictor, real_test_dir: Path, batch_size: int) -> dict:
    samples, ignored = collect_real_test(predictor.labels, real_test_dir)
    if not samples:
        shown = real_test_dir.relative_to(ROOT_DIR) if real_test_dir.is_relative_to(ROOT_DIR) else real_test_dir
        return {"status": PENDING, "reason": f"No hay fotos en {shown}/<clase>/", "ignored_folders": ignored}
    dataset = ImageListDataset(samples, build_eval_transform())
    y_true, y_pred = predict_dataset(predictor, dataset, batch_size, num_workers=0)
    metrics = compute_metrics(y_true, y_pred, predictor.labels)
    missing = [label for label, values in metrics["per_class"].items() if values["support"] == 0]
    plot_confusion_matrix(metrics["confusion_matrix"], predictor.labels, "Prueba real (data/real_test)",
                          REPORTS_DIR / "confusion_matrix_real.png")
    status = "incompleta" if missing else "ok"
    return {"status": status, "missing_classes": missing, "ignored_folders": ignored, **metrics}


def metrics_table(metrics: dict) -> list[str]:
    lines = ["| Clase | Precisión | Recall | F1 | Soporte |", "|---|---|---|---|---|"]
    for label, values in metrics["per_class"].items():
        lines.append(f"| {label} | {values['precision']:.3f} | {values['recall']:.3f} | {values['f1']:.3f} | {values['support']} |")
    lines.append(f"| **macro** | {metrics['macro_precision']:.3f} | {metrics['macro_recall']:.3f} | {metrics['macro_f1']:.3f} | {metrics['samples']} |")
    return lines


def build_summary(report: dict) -> str:
    official, real = report["official_test"], report["real_test"]
    lines = ["# Resumen de evaluación", "", f"Modelo: `{report['architecture']}`. Clases: {', '.join(report['labels'])}.", ""]
    if report.get("best_validation"):
        best = report["best_validation"]
        lines += [f"Mejor época en validación: {best['epoch']} ({best['stage']}), accuracy {best['val_accuracy']:.4f}.", ""]
    lines += ["## Prueba oficial (Fruits-360 `Test/`)", "", f"Accuracy: **{official['accuracy']:.4f}** sobre {official['samples']} imágenes.", ""]
    lines += metrics_table(official)
    lines += ["", "Variedades con menor accuracy:", ""]
    for variety, values in list(official["accuracy_by_variety"].items())[:5]:
        lines.append(f"- {variety}: {values['accuracy']:.3f} ({values['samples']} imágenes)")
    lines += ["", "## Prueba real (`data/real_test/`)", ""]
    if real["status"] == PENDING:
        lines.append(f"**Pendiente.** {real['reason']}")
    else:
        lines += [f"Estado: {real['status']}. Accuracy: **{real['accuracy']:.4f}** sobre {real['samples']} fotos.", ""]
        lines += metrics_table(real)
        if real["missing_classes"]:
            lines += ["", f"Clases sin fotos: {', '.join(real['missing_classes'])}."]
    return "\n".join(lines) + "\n"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--real-test-dir", type=Path, default=REAL_TEST_DIR)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--num-workers", type=int, default=4)
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    predictor = Predictor.from_artifacts(ARTIFACTS_DIR)
    report = {"architecture": predictor.config.get("architecture"), "labels": predictor.labels,
              "best_validation": predictor.config.get("training", {}).get("best")}
    if HISTORY_PATH.is_file():
        plot_training_curves(json.loads(HISTORY_PATH.read_text(encoding="utf-8"))["history"], REPORTS_DIR / "training_curves.png")
    else:
        logger.warning("%s not found: training curves skipped", HISTORY_PATH)

    with torch.inference_mode():
        report["official_test"] = evaluate_official(predictor, args.dataset_dir, args.batch_size, args.num_workers)
        logger.info("Official test accuracy: %.4f", report["official_test"]["accuracy"])
        report["real_test"] = evaluate_real(predictor, args.real_test_dir, args.batch_size)
    real = report["real_test"]
    logger.info("Real test: %s", real["status"] if real["status"] == PENDING else f"{real['status']} accuracy {real['accuracy']:.4f}")

    (REPORTS_DIR / "metrics.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (REPORTS_DIR / "summary.md").write_text(build_summary(report), encoding="utf-8")
    logger.info("Reports written to %s", REPORTS_DIR)


if __name__ == "__main__":
    main()
