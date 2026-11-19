"""Single source of image preprocessing, shared by training and inference.

Fruits-360 images are 100x100. MobileNetV3 was pre-trained on ImageNet at
224x224, so images are resized to 224x224 and normalized with the ImageNet
mean and standard deviation.
"""

from typing import Any

import torch
from PIL import Image, ImageOps
from torchvision import transforms

IMAGE_SIZE = 224
SOURCE_IMAGE_SIZE = 100
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def get_preprocessing_params() -> dict[str, Any]:
    """Return the preprocessing parameters stored next to the model artifact."""
    return {
        "source_image_size": SOURCE_IMAGE_SIZE,
        "image_size": IMAGE_SIZE,
        "resize": "center square crop, then bilinear resize to image_size x image_size",
        "mean": list(IMAGENET_MEAN),
        "std": list(IMAGENET_STD),
        "color_mode": "RGB",
    }


def to_model_input_image(image: Image.Image) -> Image.Image:
    """Fix EXIF orientation, convert to RGB and center-crop to a square.

    Fruits-360 images are already square, so the crop only matters for real
    photos (camera or uploads), which would otherwise be distorted.
    """
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side))


def build_eval_transform() -> transforms.Compose:
    """Deterministic transform used for validation, test and inference."""
    return transforms.Compose(
        [
            transforms.Lambda(to_model_input_image),
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )


def build_train_transform() -> transforms.Compose:
    """Training transform with light data augmentation."""
    return transforms.Compose(
        [
            transforms.Lambda(to_model_input_image),
            transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.8, 1.0), ratio=(0.9, 1.1)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(20, fill=255),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.02),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )


_EVAL_TRANSFORM = build_eval_transform()


def preprocess_image(image: Image.Image) -> torch.Tensor:
    """Turn one PIL image into a model-ready batch of shape (1, 3, 224, 224)."""
    return _EVAL_TRANSFORM(image).unsqueeze(0)
