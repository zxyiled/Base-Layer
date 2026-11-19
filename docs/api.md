# API REST

Prefijo: `/api/v1`. El modelo se carga una vez al arrancar. Todas las respuestas son JSON, salvo la carga de archivos, que entra como `multipart/form-data`.

## Errores

Formato único:

```json
{"error": {"code": "validation_error", "message": "El archivo 'image' está vacío.", "details": {"field": "image"}}}
```

`details` puede ser `null` o un objeto. Códigos HTTP usados:

| HTTP | `code` | Cuándo |
| --- | --- | --- |
| `400` | `bad_request` | Petición mal formada. |
| `404` | `not_found` | Recurso o ruta inexistente (el cuerpo también es el sobre JSON). |
| `405` | `method_not_allowed` | Método no permitido para la ruta. |
| `413` | `payload_too_large` | El cuerpo supera `MAX_CONTENT_LENGTH` (10 MB por defecto). |
| `415` | `unsupported_media_type` | El cuerpo no es `multipart/form-data` o la imagen no es JPEG, PNG ni WEBP. |
| `422` | `validation_error` | Falta un campo, el valor está fuera de rango o una fecha no es ISO 8601. |
| `422` | `unsupported_source` | `source` no es `camera`, `upload` ni `video`. |
| `422` | `invalid_image` | Los bytes no se pueden decodificar como imagen (archivo corrupto). |
| `500` | `internal_error` | Error inesperado del servidor. |
| `503` | `model_unavailable` | El artefacto del modelo no está cargado. |

## Paginación

`GET /predictions` devuelve `page` y `per_page` en la consulta y estos metadatos en la respuesta:

```json
{"items": [], "total": 0, "page": 1, "per_page": 20, "pages": 0}
```

`per_page` máximo: `100`.

## Endpoints

| Método | Ruta | Propósito |
| --- | --- | --- |
| `POST` | `/api/v1/predictions` | Clasifica una imagen y guarda la predicción. |
| `GET` | `/api/v1/predictions` | Lista paginada con filtros. |
| `GET` | `/api/v1/predictions/{id}` | Detalle de una predicción. |
| `GET` | `/api/v1/stats` | Estadísticas agregadas. |
| `GET` | `/api/v1/model` | Información del modelo cargado. |
| `GET` | `/api/v1/logs` | Últimas entradas del log. |
| `GET` | `/api/v1/health` | Estado de la app, la base de datos y el modelo. |

### `POST /predictions`

Entrada `multipart/form-data`:

| Campo | Tipo | Obligatorio | Descripción |
| --- | --- | --- | --- |
| `image` | archivo | sí | Imagen JPEG, PNG o WEBP. Se valida decodificándola con Pillow, no por la extensión ni el `Content-Type`. |
| `source` | texto | no | `camera`, `upload` o `video`. Por defecto `upload`. |

Respuesta `201`:

```json
{
  "id": 12,
  "model_version_id": 1,
  "source": "camera",
  "original_filename": "manzana.png",
  "file_size_bytes": 20480,
  "label": "manzana",
  "confidence": 0.9931,
  "top3": [
    {"label": "manzana", "confidence": 0.9931},
    {"label": "pera", "confidence": 0.0042},
    {"label": "tomate", "confidence": 0.0011}
  ],
  "inference_ms": 24.7,
  "created_at": "2026-11-19T18:00:00+00:00"
}
```

Errores: `422` (falta `image`, archivo vacío, bytes corruptos, `source` inválido), `415` (cuerpo no multipart o formato de imagen no soportado), `413` (demasiado grande), `503` (modelo no cargado).

### `GET /predictions`

Parámetros de consulta:

| Parámetro | Tipo | Por defecto | Descripción |
| --- | --- | --- | --- |
| `page` | entero `>= 1` | `1` | Página. |
| `per_page` | entero `1..100` | `20` | Elementos por página. |
| `label` | texto | — | Filtra por etiqueta exacta (`manzana`, `pera`, ...). |
| `source` | texto | — | `camera`, `upload` o `video`. |
| `date_from` | ISO 8601 | — | Desde `created_at` (inclusivo), en UTC. |
| `date_to` | ISO 8601 | — | Hasta `created_at` (exclusivo), en UTC. |

Respuesta `200`: objeto de paginación con `items` (cada uno con el formato de la predicción). Orden: más reciente primero. Errores: `422`.

Ejemplo: `/api/v1/predictions?page=2&per_page=10&source=camera&date_from=2026-11-01T00:00:00Z`

### `GET /predictions/{id}`

Respuesta `200`: una predicción con el mismo formato que `POST`. Si no existe, `404` con `not_found`.

### `GET /stats`

Respuesta `200`:

```json
{
  "total": 3,
  "mean_confidence": 0.91,
  "by_label": [{"label": "manzana", "count": 2}, {"label": "pera", "count": 1}],
  "by_source": [{"source": "camera", "count": 2}, {"source": "upload", "count": 1}]
}
```

`mean_confidence` es `null` si no hay predicciones.

### `GET /model`

Respuesta `200`:

```json
{
  "architecture": "mobilenet_v3_small",
  "num_classes": 8,
  "labels": ["banano", "fresa", "limon", "manzana", "naranja", "pera", "tomate", "uva"],
  "preprocessing": {
    "source_image_size": 100,
    "image_size": 224,
    "resize": "center square crop, then bilinear resize to image_size x image_size",
    "mean": [0.485, 0.456, 0.406],
    "std": [0.229, 0.224, 0.225],
    "color_mode": "RGB"
  },
  "training": {"best": {"epoch": 5, "stage": "finetune"}, "seed": 42},
  "metrics": {
    "official_test": {
      "status": "ok",
      "samples": 17487,
      "accuracy": 0.9938,
      "macro_precision": 0.9952,
      "macro_recall": 0.997,
      "macro_f1": 0.9961,
      "per_class": {},
      "confusion_matrix": []
    },
    "real_test": {"status": "pendiente", "reason": "No hay fotos en data/real_test/<clase>/"}
  }
}
```

`training`, `metrics` y sus campos pueden ser `null` si no hay artefacto o reporte. Error `503` si el modelo no está cargado.

### `GET /logs`

Parámetro `limit` (entero `1..500`, por defecto `100`).

Respuesta `200`:

```json
{"entries": [{"timestamp": "2026-11-19T18:00:00Z", "level": "INFO", "logger": "app.ml.predictor", "message": "Model loaded"}]}
```

Entradas de la más antigua a la más reciente. Solo lee el archivo actual, no las rotaciones. Errores: `422` si `limit` no es válido.

### `GET /health`

Respuesta `200`:

```json
{"status": "ok", "database": "ok", "model": "loaded"}
```

Si la base de datos no responde, `503` con `{"status": "degraded", "database": "error", "model": "loaded"}`. `model` vale `loaded` o `unavailable`.
