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

`create_app()` crea el `Predictor` una sola vez y lo deja en `app.extensions["predictor"]`; también guarda la carpeta del artefacto en `app.extensions["model_artifacts_dir"]`. Si faltan los archivos, registra una advertencia y deja el predictor en `None` para que la app arranque igual.

## Servicios

| Componente | Responsabilidad |
| --- | --- |
| `app/services/prediction_service.py` | Valida `source`, decodifica los bytes con Pillow, mide el tiempo de inferencia, guarda la predicción por el repositorio y loguea los metadatos. |
| `app/services/history_service.py` | Lista paginada con filtros y detalle de una predicción; lanza `NotFoundError` si el id no existe. |
| `app/services/stats_service.py` | Devuelve los agregados de `prediction_repository.stats()`. |
| `app/services/model_info_service.py` | Expone arquitectura, clases, preprocesamiento, entrenamiento y métricas; registra la versión activa del artefacto. |
| `app/services/log_service.py` | Devuelve las últimas entradas del log mediante `read_last_entries()`. |
| `app/core/errors.py` | Errores de dominio con un `code` (`validation_error`, `unsupported_source`, `invalid_image`, `not_found`, `model_unavailable`) que la API traduce a HTTP. |

Flujo de una predicción: la ruta llama a `PredictionService.predict(image_bytes, source, original_filename)`; el servicio comprueba la fuente contra `SOURCES`, decodifica con `Image.open`/`load` (nunca confía en la extensión ni en el `Content-Type`), llama a `predictor.predict()`, mide `inference_ms`, crea la fila con `file_size_bytes = len(image_bytes)` y devuelve `Prediction.as_dict()`. Los servicios no acceden a la base de datos: usan los repositorios.

`ModelInfoService.ensure_active_version()` registra el artefacto cargado con `model_version_repository.get_or_create_active()`. El nombre combina arquitectura, número de clases y la fecha de modificación de `model.pt`, de modo que un reentrenamiento crea otra versión. La vinculación de cada predicción con `model_version_id` se resuelve en la API (M5). Las métricas se leen de `ml_training/reports/metrics.json` (o `MODEL_METRICS_FILE`) y se resumen en accuracy, macro métricas, métricas por clase y matriz de confusión; si el archivo no existe, `metrics` es `null`.

## API REST

| Componente | Responsabilidad |
| --- | --- |
| `app/api/v1/__init__.py` | Crea el blueprint `api_v1` con prefijo `/api/v1` y registra los módulos de rutas. |
| `app/api/v1/predictions.py` | `POST /predictions` (201) y `GET /predictions` / `GET /predictions/<id>` con filtros y paginación. |
| `app/api/v1/stats.py` | `GET /stats`. |
| `app/api/v1/model.py` | `GET /model`. |
| `app/api/v1/logs.py` | `GET /logs?limit=`. |
| `app/api/v1/health.py` | `GET /health` con `SELECT 1` contra la base de datos. |
| `app/api/v1/schemas.py` | Validación de parámetros (`page`, `per_page`, fechas ISO 8601, `source`) y sobre de error. |
| `app/api/v1/dependencies.py` | Construye `ModelInfoService` y registra una sola vez la versión activa del modelo. |
| `app/api/v1/errors.py` | Devuelve el sobre `{"error": {...}}` para errores HTTP e inesperados bajo `/api/` y páginas HTML de Flask fuera de ese prefijo. El manejador de `ServiceError` devuelve JSON en toda la aplicación. |

`create_app()` registra el blueprint y los manejadores de error. Cada ruta solo valida la entrada, llama a un servicio y serializa la respuesta. `POST /predictions` exige `multipart/form-data`, lee `image`, acepta `source` opcional y devuelve `201`. Los formatos aceptados por Pillow son JPEG, PNG y WEBP; un formato válido distinto responde `415` y un archivo corrupto `422`. Flask aplica `MAX_CONTENT_LENGTH` (10 MB por defecto) y responde `413`.

La API no accede a la base de datos ni al modelo directamente: usa `PredictionService`, `HistoryService`, `StatsService`, `ModelInfoService` y `LogService`. El `model_version_id` se resuelve en la primera predicción con `ModelInfoService.ensure_active_version()` y se guarda en `app.extensions` para reutilizarlo. `docs/api.md` es el contrato que consume el frontend.

## Interfaz web (M7)

| Componente | Responsabilidad |
| --- | --- |
| `app/web/__init__.py` | Define el blueprint `web` e importa las vistas. |
| `app/web/routes.py` | `GET /` renderiza la plantilla única de la interfaz. |
| `app/templates/index.html` | Estructura Jinja: cámara, subida, video, resultado, historial, estadísticas, modelo y registros. |
| `app/static/css/styles.css` | Tokens de diseño, tema claro/oscuro, diseño responsive y `prefers-reduced-motion`. |
| `app/static/vendor/chart.umd.min.js` | Chart.js 4.6.1 servido localmente, sin dependencia de CDN. |
| `app/static/js/app.js` | Llamadas `fetch` a la API, `sampleFrame()` compartido por cámara y video, y gráficas con Chart.js. |

`create_app()` registra este blueprint junto al de la API. La ruta web solo sirve HTML: **no llama a servicios ni a la base de datos**. El navegador consume los siete endpoints bajo `/api/v1` con `fetch` y muestra el sobre de error en un resumen accesible y enfocable. Las imágenes nunca se registran en logs.

La vista previa usa `getUserMedia` con `facingMode: { ideal: 'environment' }` para dar preferencia a la cámara trasera en móviles. Si el equipo tiene una sola cámara, usa la disponible. Si falta la cámara, se deniega el permiso o el contexto no es seguro, la interfaz muestra un mensaje en español y ofrece la subida de archivos. La captura dibuja el fotograma en un `canvas` y envía un JPEG a `POST /api/v1/predictions` con `source=camera`. El modo continuo tiene controles de inicio y detención. Captura cada 1,5 s, omite envíos mientras hay una petición en curso y se detiene al primer error para evitar alertas repetidas.

El navegador selecciona hasta ocho fotogramas del video y los envía como imágenes con `source=video`. El resumen ordena las clases por su confianza media sobre todos los fotogramas. Si una clase queda fuera del top-3 de un fotograma, su confianza cuenta como cero en ese fotograma. Las tres medias más altas forman el top-3 del resumen. La nota indica en cuántos fotogramas ganó la clase con la media más alta.

El selector «Etiqueta» del historial se llena con las clases de `GET /api/v1/model` para enviar los valores exactos que compara la API. En «Información del modelo», la prueba real muestra «Pendiente» si no hay fotos, la exactitud seguida de «(faltan clases)» si el estado es `incompleta` y la exactitud si es `ok`.

Las estadísticas se dibujan con Chart.js a partir de `GET /api/v1/stats`, con tablas de datos equivalentes y una paleta que no depende solo del color. El estado de salud, la información del modelo y los registros se cargan al abrir la página y se pueden actualizar de forma independiente.

## Persistencia

| Componente | Responsabilidad |
| --- | --- |
| `app/config.py` | Lee `DATABASE_URL`, `SECRET_KEY` y las variables de logs desde el entorno (`.env`). Convierte las URL `postgresql://` y `postgres://` al dialecto `postgresql+psycopg://` de psycopg 3. |
| `app/extensions.py` | Expone las instancias compartidas `db = SQLAlchemy()` y `migrate = Migrate()`. |
| `app/models/` | Declara `Prediction` y `ModelVersion` con sus restricciones, índices y relaciones. |
| `app/repositories/` | Centraliza las altas, búsquedas, consultas paginadas y agregados con SQLAlchemy. |
| `app/__init__.py` | `create_app()` configura la aplicación, inicializa `db` y `migrate`, y registra los modelos. |
| `migrations/` | La revisión inicial `6bfedced69da` crea el esquema original. La revisión `7e4b0e45cdaf` deja como tablas de la aplicación `predictions` y `model_versions`. Alembic usa `db.engine` y conserva los handlers del logger raíz si ya están configurados. |

`uv run flask --app wsgi db upgrade` aplica las migraciones versionadas con Flask-Migrate y Alembic. Las pruebas de repositorios preparan su SQLite temporal con `db.create_all()` y una prueba aparte aplica la migración y compara el esquema con los modelos.

| Tabla | Campos principales |
| --- | --- |
| `model_versions` | `name` único, `architecture`, `artifact_path`, `labels` (JSON), `is_active`, `created_at`. |
| `predictions` | `source` (`camera`, `upload` o `video`), `original_filename`, `file_size_bytes` (entero opcional), `predicted_label`, `confidence` (entre 0 y 1, inclusive), `top3` (JSON), `inference_ms` (flotante opcional, en milisegundos), `model_version_id` (FK opcional con `ON DELETE SET NULL`), `created_at`. |

`prediction_repository.create()` acepta el tamaño del archivo en bytes y el tiempo de inferencia. `Prediction.as_dict()` incluye ambos campos. La imagen queda fuera de la base de datos. La restricción `ck_predictions_confidence` aplica el rango de confianza en la base. Ambos modelos serializan `created_at` en ISO 8601 con `+00:00` y tratan las fechas sin zona de SQLite como UTC.

`prediction_repository.list_paginated()` combina filtros opcionales por `label`, `source` y `created_at`. Los límites de fecha se pasan en UTC como `date_from` (inclusivo) y `date_to` (exclusivo). Las consultas paginadas devuelven `items`, `total`, `page`, `per_page` y `pages`, con un máximo de 100 elementos por página.

## Logs de aplicación

| Componente | Responsabilidad |
| --- | --- |
| `app/core/logging_config.py` | Configura el logger raíz con salida a `stderr` y a un archivo rotativo. Crea la carpeta de destino y reemplaza sus propios handlers al volver a configurarse. `PlainFormatter` elimina los colores ANSI del archivo. La consola los conserva. |
| `app/core/log_reader.py` | `tail_lines()` lee las últimas líneas por bloques desde el final. `read_last_entries()` lee solo el archivo actual y devuelve `timestamp`, `level`, `logger` y `message`, en orden de la entrada más antigua a la más reciente. |

`create_app()` configura los logs al arrancar. El formato es `<fecha y hora UTC> <NIVEL> <logger>: <mensaje>`, por ejemplo `2026-11-19T17:00:00Z INFO app.ml.predictor: Model loaded`.

`read_last_entries()` devuelve hasta 100 entradas por defecto, con un máximo de 500. Empieza con una ventana de `limit × 4` líneas al final del archivo y la cuadruplica hasta reunir las entradas solicitadas, abarcar el archivo o llegar al tope de 100 000 líneas. Así puede recuperar la cabecera de un traceback largo. Si la ventana empieza a mitad de una entrada, descarta el fragmento inicial. Solo puede devolver `timestamp`, `level` y `logger` en `null` cuando lee el archivo completo y este empieza con líneas sin el formato de log.

El lector sustituye los bytes UTF-8 inválidos y devuelve una lista vacía si el archivo no existe o el límite es cero o negativo. El servicio `LogService` de M4 expone estas entradas y `GET /api/v1/logs` las sirve en M5.

## Entrega (M8)

| Archivo | Contenido |
| --- | --- |
| `README.md` | Instalación con `uv`, datos, base de datos, Docker, interfaz y licencias. |
| `LICENSE` | Licencia MIT del código del proyecto (Juan Cardona, Santiago Góez, Sebastián Mejía · 2026). |
| `docs/` | Arquitectura, dataset, informe del modelo, API, despliegue y estado de los módulos. |
| `docs/presentacion/index.html` | 20 diapositivas de baja densidad con resultados ya documentados. |

Las diapositivas usan un escenario fijo de 1920 × 1080 escalado a la ventana, sin dependencias externas salvo las tipografías opcionales de Google Fonts. No introducen datos nuevos: la prueba con fotos reales permanece pendiente.
