# Arquitectura

## Datos, entrenamiento y evaluación

| Componente | Responsabilidad |
| --- | --- |
| `ml_training/prepare_subset.py` | Agrupa variedades por fruta, separa los fotogramas y escribe el manifiesto y sus metadatos en `data/processed/`. |
| `ml_training/common.py` | Comparte rutas, semillas y carga de imágenes entre entrenamiento y evaluación. |
| `ml_training/train.py` | Lee las particiones `train` y `val`, entrena en dos etapas y guarda el mejor artefacto y el historial. |
| `ml_training/evaluate.py` | Carga el artefacto, evalúa la partición `test` y las fotos propias por separado, y escribe los reportes en `ml_training/reports/`. |

## Inferencia local

| Componente | Responsabilidad |
| --- | --- |
| `app/ml/model_factory.py` | Construye MobileNetV3-Small con una capa final de ocho salidas para el modelo del proyecto. El entrenamiento inicializa los pesos de ImageNet y la inferencia carga los pesos locales. |
| `app/ml/preprocessing.py` | Define las transformaciones compartidas. La de evaluación se usa también en validación e inferencia. |
| `app/ml/predictor.py` | Carga el modelo en CPU y clasifica imágenes de Pillow con el modelo en modo evaluación. |
| `app/ml/artifacts/` | Contiene los pesos en `model.pt` (6,2 MB), el orden de clases en `labels.json` y los metadatos de preprocesamiento y entrenamiento en `preprocessing.json`. |

`Predictor.from_artifacts()` carga los archivos una vez por instancia. Luego `predict(image)` aplica el preprocesamiento compartido, convierte las salidas del modelo a probabilidades con *softmax* y devuelve `{label, confidence, top3}`. Cada entrada de `top3` tiene `label` y `confidence`, en orden descendente de confianza. La implementación de las transformaciones vive en `preprocessing.py` y el JSON registra sus parámetros.

## Persistencia

| Componente | Responsabilidad |
| --- | --- |
| `app/config.py` | Lee `DATABASE_URL`, `SECRET_KEY` y `LOG_LEVEL` desde el entorno (`.env`) y convierte las URL `postgresql://` y `postgres://` al dialecto `postgresql+psycopg://` de psycopg 3. |
| `app/extensions.py` | Expone las instancias compartidas `db = SQLAlchemy()` y `migrate = Migrate()`. |
| `app/models/` | Declara `Prediction`, `ModelVersion` y `AppLog` con sus restricciones, índices y relaciones. |
| `app/repositories/` | Centraliza las altas, búsquedas, consultas paginadas y agregados con SQLAlchemy. |
| `app/__init__.py` | `create_app()` configura la aplicación, inicializa `db` y `migrate`, y registra los modelos. |
| `migrations/` | La revisión inicial `6bfedced69da` crea las tres tablas, sus restricciones y sus índices. Alembic usa `db.engine` y mantiene habilitados los loggers existentes. |

`uv run flask --app wsgi db upgrade` aplica las migraciones versionadas con Flask-Migrate y Alembic. Las pruebas de repositorios preparan su SQLite temporal con `db.create_all()` y una prueba aparte aplica la migración y compara el esquema con los modelos.

| Tabla | Campos principales |
| --- | --- |
| `model_versions` | `name` único, `architecture`, `artifact_path`, `labels` (JSON), `is_active`, `created_at`. |
| `predictions` | `source` (`camera`, `upload` o `video`), `original_filename`, `file_size_bytes` (entero opcional), `predicted_label`, `confidence` (entre 0 y 1, inclusive), `top3` (JSON), `inference_ms` (flotante opcional, en milisegundos), `model_version_id` (FK opcional con `ON DELETE SET NULL`), `created_at`. |
| `app_logs` | `level`, `logger`, `message`, `context` (JSON), `created_at`. |

`prediction_repository.create()` acepta el tamaño del archivo en bytes y el tiempo de inferencia. `Prediction.as_dict()` incluye ambos campos. La imagen queda fuera de la base de datos. La restricción `ck_predictions_confidence` aplica el rango de confianza en la base. Los tres modelos serializan `created_at` en ISO 8601 con `+00:00` y tratan las fechas sin zona de SQLite como UTC.

`prediction_repository.list_paginated()` combina filtros opcionales por `label`, `source` y `created_at`. Los límites de fecha se pasan en UTC como `date_from` (inclusivo) y `date_to` (exclusivo). Las consultas paginadas devuelven `items`, `total`, `page`, `per_page` y `pages`, con un máximo de 100 elementos por página.
