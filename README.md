# Clasificador de frutas con transfer learning (Fruits-360)

El módulo de ML clasifica ocho frutas con MobileNetV3-Small en CPU. Incluye la preparación del subconjunto, el entrenamiento, la evaluación y un predictor local.

## Preparar los datos y reproducir el entrenamiento

1. Desde la raíz del proyecto, instala las dependencias.

   ```sh
   uv sync
   ```

2. Crea `data/raw/fruits-360/` y descarga **Fruits-360**, de Mihai Oltean (2017–), versión `2026.10.27.0` de la rama **100x100**, bajo licencia **CC BY-SA 4.0**. Coloca `Training/` y `Test/` directamente dentro de `data/raw/fruits-360/`. Esa carpeta se mantiene fuera del repositorio. Si el dataset ya está en otra ubicación, exporta `DATASET_DIR` con la ruta que contiene ambas carpetas. [Descarga y atribución oficial](https://github.com/fruits-360/fruits-360-100x100)

3. Genera el manifiesto, entrena y evalúa.

   ```sh
   uv run python ml_training/prepare_subset.py
   uv run python ml_training/train.py
   uv run python ml_training/evaluate.py
   ```

   Los scripts guardan el manifiesto en `data/processed/`, el modelo en `app/ml/artifacts/` y las métricas y gráficas en `ml_training/reports/`. Para incluir la prueba real, coloca fotos propias en `data/real_test/<clase>/` y vuelve a ejecutar la evaluación. Sin fotos, esa prueba figura como pendiente.

## Base de datos

La aplicación guarda las predicciones y los registros en PostgreSQL mediante Flask-SQLAlchemy.

1. Copia `.env.example` a `.env` y ajusta `DATABASE_URL` con la conexión de tu PostgreSQL.

   ```sh
   cp .env.example .env
   ```

2. Crea las tablas.

   ```sh
   uv run flask --app wsgi init-db
   ```

   El comando usa `db.create_all()`. No hay migraciones versionadas: si cambia el esquema, recrea las tablas o migra los datos a mano.

## Documentación

- [Dataset, clases y partición](docs/dataset.md)
- [Entrenamiento y resultados](docs/ml-report.md)
- [Arquitectura del módulo de ML](docs/architecture.md)
- [Estado de los módulos](docs/progress.md)
