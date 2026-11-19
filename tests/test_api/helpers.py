import io


def post_image(client, image_bytes, source=None, filename="fruta.png", content_type="image/png"):
    """POST one multipart image to the prediction endpoint."""
    data = {"image": (io.BytesIO(image_bytes), filename, content_type)}
    if source is not None:
        data["source"] = source
    return client.post("/api/v1/predictions", data=data, content_type="multipart/form-data")
