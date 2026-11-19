"""Two-stage transfer learning of MobileNetV3-Small on the Fruits-360 subset (CPU).

Stage 1 trains only the classifier head (backbone frozen).
Stage 2 also unfreezes the last feature blocks with a lower learning rate.
The best model on validation loss (accuracy as tie-break) is saved to
app/ml/artifacts/. Validation accuracy saturates near 99.9% on Fruits-360,
so the loss is the more informative selection criterion.

Usage: uv run python ml_training/train.py [--epochs-head 3 --epochs-finetune 5]
"""

import argparse
import json
import logging
import time
from collections import Counter
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader, WeightedRandomSampler

from common import (
    ARTIFACTS_DIR,
    DEFAULT_DATASET_DIR,
    HISTORY_PATH,
    REPORTS_DIR,
    SEED,
    load_manifest,
    manifest_dataset,
    set_seed,
)
from app.ml.model_factory import ARCHITECTURE, build_model
from app.ml.predictor import LABELS_FILE, PREPROCESSING_FILE, WEIGHTS_FILE
from app.ml.preprocessing import build_eval_transform, build_train_transform, get_preprocessing_params

logger = logging.getLogger("train")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--epochs-head", type=int, default=3)
    parser.add_argument("--epochs-finetune", type=int, default=5)
    parser.add_argument("--lr-head", type=float, default=1e-3)
    parser.add_argument("--lr-finetune", type=float, default=1e-4)
    parser.add_argument("--unfreeze-blocks", type=int, default=4, help="last feature blocks trained in stage 2")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--max-batches", type=int, default=0, help="limit batches per epoch (0 = all); smoke tests only")
    parser.add_argument("--seed", type=int, default=SEED)
    return parser.parse_args()


def balanced_sampler(targets: list[int], seed: int) -> WeightedRandomSampler:
    """Sample every class with the same probability (weight = 1 / class count)."""
    counts = Counter(targets)
    weights = [1.0 / counts[target] for target in targets]
    generator = torch.Generator().manual_seed(seed)
    return WeightedRandomSampler(weights, num_samples=len(targets), replacement=True, generator=generator)


def configure_stage(model: nn.Module, stage: str, unfreeze_blocks: int) -> list[nn.Parameter]:
    """Freeze the backbone (head stage) or unfreeze its last blocks (finetune stage)."""
    for parameter in model.features.parameters():
        parameter.requires_grad = False
    if stage == "finetune":
        for block in model.features[-unfreeze_blocks:]:
            for parameter in block.parameters():
                parameter.requires_grad = True
    for parameter in model.classifier.parameters():
        parameter.requires_grad = True
    return [parameter for parameter in model.parameters() if parameter.requires_grad]


def set_train_mode(model: nn.Module) -> None:
    """Train mode, but keep frozen blocks in eval so their BatchNorm statistics stay fixed."""
    model.train()
    for block in model.features:
        if not any(parameter.requires_grad for parameter in block.parameters()):
            block.eval()


def run_epoch(model, loader, criterion, optimizer=None, max_batches: int = 0) -> tuple[float, float]:
    """One pass over ``loader``; trains when an optimizer is given. Returns (loss, accuracy)."""
    training = optimizer is not None
    total_loss, correct, seen = 0.0, 0, 0
    with torch.set_grad_enabled(training):
        for batch_number, (images, targets) in enumerate(loader, start=1):
            outputs = model(images)
            loss = criterion(outputs, targets)
            if training:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            total_loss += loss.item() * targets.size(0)
            correct += (outputs.argmax(dim=1) == targets).sum().item()
            seen += targets.size(0)
            if max_batches and batch_number >= max_batches:
                break
    return total_loss / seen, correct / seen


def save_artifacts(model: nn.Module, labels: list[str], training_info: dict) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), ARTIFACTS_DIR / WEIGHTS_FILE)
    (ARTIFACTS_DIR / LABELS_FILE).write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
    config = {"architecture": ARCHITECTURE, "num_classes": len(labels), **get_preprocessing_params(), "training": training_info}
    (ARTIFACTS_DIR / PREPROCESSING_FILE).write_text(json.dumps(config, indent=2), encoding="utf-8")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = parse_args()
    set_seed(args.seed)

    train_rows, val_rows = load_manifest("train"), load_manifest("val")
    labels = sorted({row["fruit"] for row in train_rows})
    train_set = manifest_dataset(train_rows, labels, args.dataset_dir, build_train_transform())
    val_set = manifest_dataset(val_rows, labels, args.dataset_dir, build_eval_transform())
    targets = [target for _, target in train_set.samples]
    train_loader = DataLoader(train_set, batch_size=args.batch_size, sampler=balanced_sampler(targets, args.seed), num_workers=args.num_workers)
    val_loader = DataLoader(val_set, batch_size=args.batch_size * 2, shuffle=False, num_workers=args.num_workers)
    logger.info("Labels: %s | train=%d val=%d | threads=%d", labels, len(train_set), len(val_set), torch.get_num_threads())

    model = build_model(num_classes=len(labels), pretrained=True)
    criterion = nn.CrossEntropyLoss()
    stages = [("head", args.epochs_head, args.lr_head), ("finetune", args.epochs_finetune, args.lr_finetune)]
    hyperparameters = {key: value for key, value in vars(args).items() if key != "dataset_dir"}
    history, best = [], {"val_loss": float("inf"), "val_accuracy": -1.0}
    epoch = 0
    for stage, epochs, lr in stages:
        params = configure_stage(model, stage, args.unfreeze_blocks)
        optimizer = torch.optim.AdamW(params, lr=lr)
        logger.info("Stage %s: %d epochs, lr=%g, trainable params=%d", stage, epochs, lr, sum(p.numel() for p in params))
        for _ in range(epochs):
            epoch += 1
            start = time.perf_counter()
            set_train_mode(model)
            train_loss, train_acc = run_epoch(model, train_loader, criterion, optimizer, args.max_batches)
            model.eval()
            val_loss, val_acc = run_epoch(model, val_loader, criterion, max_batches=args.max_batches)
            seconds = round(time.perf_counter() - start, 1)
            history.append({"epoch": epoch, "stage": stage, "lr": lr, "train_loss": train_loss, "train_accuracy": train_acc,
                            "val_loss": val_loss, "val_accuracy": val_acc, "seconds": seconds})
            logger.info("Epoch %d (%s): train loss %.4f acc %.4f | val loss %.4f acc %.4f | %.0fs",
                        epoch, stage, train_loss, train_acc, val_loss, val_acc, seconds)
            if (val_loss, -val_acc) < (best["val_loss"], -best["val_accuracy"]):
                best = {"epoch": epoch, "stage": stage, "val_accuracy": val_acc, "val_loss": val_loss}
                save_artifacts(model, labels, {"best": best, "selection": "min val_loss, val_accuracy tie-break",
                                                     "seed": args.seed, "hyperparameters": hyperparameters})
                logger.info("New best model saved (val loss %.4f, acc %.4f)", val_loss, val_acc)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps({"history": history, "best": best, "hyperparameters": hyperparameters}, indent=2), encoding="utf-8")
    logger.info("Best epoch %d (%s) val acc %.4f. History: %s", best["epoch"], best["stage"], best["val_accuracy"], HISTORY_PATH)


if __name__ == "__main__":
    main()
