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
| `app/config.py` | Lee `DATABASE_URL`, `SECRET_KEY` y `LOG_LEVEL` desde el entorno (`.env`) y convierte las URL `postgresql://` al dialecto `postgresql+psycopg://` de psycopg 3. |
| `app/extensions.py` | Expone la instancia compartida `db = SQLAlchemy()`. |
| `app/models/` | Declara `Prediction`, `ModelVersion` y `AppLog` con sus restricciones, índices y relaciones. |
| `app/repositories/` | Única capa que consulta la base de datos: alta, búsqueda, listados paginados y agregados con SQLAlchemy. |
| `app/__init__.py` | `create_app()` configura la aplicación, inicializa `db` y registra el comando `flask --app wsgi init-db`. |

Las rutas y los servicios no acceden a la base de datos directamente: llaman a un repositorio. Las tablas se crean con `init-db` mediante `db.create_all()`; no hay migraciones versionadas, así que un cambio de esquema requiere recrear las tablas. Las consultas paginadas devuelven `items`, `total`, `page`, `per_page` y `pages`, con un máximo de 100 elementos por página.

| Tabla | Campos principales |
| --- | --- |
| `model_versions` | `name` único, `architecture`, `artifact_path`, `labels` (JSON), `is_active`, `created_at`. |
| `predictions` | `source` (`camera`, `upload` o `video`), `original_filename`, `predicted_label`, `confidence`, `top3` (JSON), `model_version_id`, `created_at`. |
| `app_logs` | `level`, `logger`, `message`, `context` (JSON), `created_at`. |
