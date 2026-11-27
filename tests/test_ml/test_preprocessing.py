import torch
from PIL import Image

from app.ml.preprocessing import (
    IMAGE_SIZE,
    IMAGENET_MEAN,
    IMAGENET_STD,
    build_train_transform,
    get_preprocessing_params,
    preprocess_image,
    to_model_input_image,
)


def _channel_bounds() -> tuple[torch.Tensor, torch.Tensor]:
    mean, std = torch.tensor(IMAGENET_MEAN), torch.tensor(IMAGENET_STD)
    return ((0 - mean) / std).view(1, 3, 1, 1), ((1 - mean) / std).view(1, 3, 1, 1)


def test_preprocess_image_shape_and_dtype():
    tensor = preprocess_image(Image.new("RGB", (100, 100), (200, 30, 30)))
    assert tensor.shape == (1, 3, IMAGE_SIZE, IMAGE_SIZE)
    assert tensor.dtype == torch.float32


def test_preprocess_image_range_is_imagenet_normalized():
    image = Image.effect_noise((100, 100), 80).convert("RGB")
    tensor = preprocess_image(image)
    low, high = _channel_bounds()
    assert torch.all(tensor >= low - 1e-5)
    assert torch.all(tensor <= high + 1e-5)


def test_white_pixel_maps_to_upper_bound():
    tensor = preprocess_image(Image.new("RGB", (100, 100), (255, 255, 255)))
    _, high = _channel_bounds()
    assert torch.allclose(tensor[:, :, 0, 0], high.view(1, 3), atol=1e-5)


def test_inference_preprocessing_is_deterministic():
    image = Image.effect_noise((100, 100), 60).convert("RGB")
    assert torch.equal(preprocess_image(image), preprocess_image(image))


def test_non_square_and_non_rgb_images_are_accepted():
    for image in (Image.new("L", (640, 480)), Image.new("RGBA", (300, 500))):
        assert preprocess_image(image).shape == (1, 3, IMAGE_SIZE, IMAGE_SIZE)


def test_center_square_crop():
    assert to_model_input_image(Image.new("RGB", (640, 480))).size == (480, 480)


def test_train_transform_shape():
    tensor = build_train_transform()(Image.new("RGB", (100, 100), (10, 200, 10)))
    assert tensor.shape == (3, IMAGE_SIZE, IMAGE_SIZE)


def test_preprocessing_params():
    params = get_preprocessing_params()
    assert params["image_size"] == IMAGE_SIZE
    assert params["mean"] == list(IMAGENET_MEAN)
    assert params["std"] == list(IMAGENET_STD)
