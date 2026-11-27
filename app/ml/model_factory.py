"""Builds the MobileNetV3-Small classifier used for training and inference."""

from torch import nn
from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

ARCHITECTURE = "mobilenet_v3_small"


def build_model(num_classes: int, pretrained: bool = False) -> nn.Module:
    """Return MobileNetV3-Small with a new final layer for ``num_classes``.

    ``pretrained=True`` loads the ImageNet weights (used for training).
    Inference builds the architecture without weights and loads the artifact.
    """
    weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
    model = mobilenet_v3_small(weights=weights)
    in_features = model.classifier[-1].in_features
    model.classifier[-1] = nn.Linear(in_features, num_classes)
    return model
