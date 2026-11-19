# Clasificador de frutas con transfer learning (Fruits-360)

El módulo de ML clasifica ocho frutas con MobileNetV3-Small en CPU. Incluye la preparación del subconjunto, el entrenamiento, la evaluación y un predictor local.

## Preparar los datos y reproducir el entrenamiento

1. Desde la raíz del proyecto, instala las dependencias.

   ```sh
   uv sync
   ```

   En local, `uv sync` incluye los grupos `dev` (pruebas) y `train` (entrenamiento y evaluación). La imagen Docker instala solo las dependencias de ejecución.

2. Crea `data/raw/fruits-360/` y descarga **Fruits-360**, de Mihai Oltean (2017–), versión `2026.10.27.0` de la rama **100x100**, bajo licencia **CC BY-SA 4.0**. Coloca `Training/` y `Test/` directamente dentro de `data/raw/fruits-360/`. Esa carpeta se mantiene fuera del repositorio. Si el dataset ya está en otra ubicación, exporta `DATASET_DIR` con la ruta que contiene ambas carpetas. [Descarga y atribución oficial](https://github.com/fruits-360/fruits-360-100x100)

3. Genera el manifiesto, entrena y evalúa.

   ```sh
   uv run python ml_training/prepare_subset.py
   uv run python ml_training/train.py
   uv run python ml_training/evaluate.py
   ```

   Los scripts guardan el manifiesto en `data/processed/`, el modelo en `app/ml/artifacts/` y las métricas y gráficas en `ml_training/reports/`. Para incluir la prueba real, coloca fotos propias en `data/real_test/<clase>/` y vuelve a ejecutar la evaluación. Sin fotos, esa prueba figura como pendiente.

## Base de datos

El esquema de PostgreSQL incluye tablas para predicciones y versiones del modelo.

1. Copia `.env.example` a `.env` y ajusta `DATABASE_URL` con la conexión de tu PostgreSQL.

   ```sh
   cp .env.example .env
   ```

2. Con PostgreSQL en ejecución, aplica las migraciones y comprueba el esquema. La primera revisión parte de un esquema vacío.

   ```sh
   uv run flask --app wsgi db upgrade
   uv run flask --app wsgi db check
   ```

3. Si cambias los modelos, genera una migración y revisa el archivo en `migrations/versions/`. Luego ejecuta `db upgrade` y `db check` como en el paso anterior.

   ```sh
   uv run flask --app wsgi db migrate -m "describe el cambio"
   ```

Si ya tienes tablas del M2 original, consulta la nota sobre la revisión inicial. [Despliegue](docs/deployment.md#base-de-datos)

La aplicación escribe sus logs en la consola y en `logs/app.log` por defecto. La carpeta `logs/` se crea automáticamente al arrancar. [Configuración de logs](docs/deployment.md#logs-de-aplicación)

## Docker (app + PostgreSQL)

1. Crea el `.env` desde el ejemplo y ajusta las credenciales.

   ```sh
   cp .env.example .env
   ```

2. Construye y levanta la aplicación y la base de datos.

   ```sh
   docker compose up -d --build
   ```

   `entrypoint.sh` aplica las migraciones y arranca Gunicorn en `http://localhost:8000`. La API vive bajo `/api/v1` (por ejemplo, `GET /api/v1/health`). La cámara del navegador requiere `localhost` o HTTPS.

3. Para detener el entorno: `docker compose down` (añade `-v` para borrar también el volumen de la base de datos).

[Más detalles de despliegue](docs/deployment.md#docker)

## Interfaz web

Abre `http://localhost:8000/` tras levantar Docker (o `http://127.0.0.1:5000/` con `uv run flask --app wsgi run --debug`). La página sirve una única vista en Jinja que consume los endpoints de `docs/api.md` desde el navegador: clasificación por cámara o archivo, resultado con confianza y top-3, historial paginado, estadísticas con Chart.js, información del modelo y registros.

La cámara del navegador requiere `localhost` o HTTPS. Si el permiso se deniega, no hay cámara o el contexto no es seguro, la interfaz lo indica y permite subir una imagen. El modo continuo y el análisis de video funcionan en el navegador: envían fotogramas al mismo endpoint de predicción y no necesitan cambios en el backend. [Arquitectura de la interfaz](docs/architecture.md#interfaz-web-m7)

## Documentación

- [Dataset, clases y partición](docs/dataset.md)
- [Entrenamiento y resultados](docs/ml-report.md)
- [Arquitectura del módulo de ML](docs/architecture.md)
- [Estado de los módulos](docs/progress.md)
