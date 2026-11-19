# Despliegue

## Base de datos

La aplicación usa PostgreSQL y Flask-SQLAlchemy. Configura la conexión mediante `DATABASE_URL` en el entorno.

| Variable | Uso |
| --- | --- |
| `DATABASE_URL` | URL de conexión. Las variantes `postgresql://` y `postgres://` se convierten a `postgresql+psycopg://` para usar psycopg 3. |
| `SECRET_KEY` | Clave de Flask. |
| `MAX_CONTENT_LENGTH` | Tamaño máximo de una subida en bytes (`10485760`, 10 MB, por defecto). |
| `MODEL_ARTIFACTS_DIR` | Carpeta alternativa del artefacto (`app/ml/artifacts/` por defecto). |
| `MODEL_METRICS_FILE` | Reporte de métricas para la información del modelo (`ml_training/reports/metrics.json` por defecto). |
| `LOG_LEVEL` | Nivel de registro (`INFO` por defecto). |
| `LOG_FILE` | Ruta del archivo de logs (`<raíz del proyecto>/logs/app.log` por defecto). |
| `LOG_MAX_BYTES` | Umbral de rotación en bytes (`1000000` por defecto). |
| `LOG_BACKUP_COUNT` | Cantidad de respaldos (`5` por defecto). |

Para crear el entorno local, copia `.env.example` a `.env` y ajusta los valores.

```sh
cp .env.example .env
```

Con PostgreSQL en ejecución, aplica las migraciones versionadas con Flask-Migrate 4.1.0 y Alembic 1.20.1. La revisión inicial crea las tablas en un esquema vacío.

```sh
uv run flask --app wsgi db upgrade
uv run flask --app wsgi db check
```

Cuando `flask db upgrade` o `upgrade()` desde las pruebas se ejecutan con los logs de la aplicación ya configurados, Alembic conserva esos handlers. Los mensajes de migración salen por `stderr` y también se escriben en `LOG_FILE` (`logs/app.log` por defecto), según el nivel configurado. Alembic aplica `fileConfig` con `alembic.ini` solo si el logger raíz carece de handlers.

Si la base conserva tablas creadas por el M2 original con `db.create_all()`, la revisión inicial intentará crearlas de nuevo. Usa una base vacía para aplicar esa revisión. La migración de los datos de una instalación anterior queda pendiente si se necesita conservarlos.

Tras cambiar los modelos, genera una revisión y examina el archivo en `migrations/versions/` antes de aplicarla.

```sh
uv run flask --app wsgi db migrate -m "describe el cambio"
```

Aplica la revisión con `db upgrade` y comprueba con `db check` si quedan diferencias detectables entre el esquema y los modelos. En Docker, `entrypoint.sh` ejecuta `flask --app wsgi db upgrade` antes de arrancar Gunicorn.

> La cámara del navegador solo funciona en `localhost` o con HTTPS.

## Docker

`docker-compose.yml` levanta dos servicios: `db` (PostgreSQL 17.6) y `app` (la imagen construida desde el `Dockerfile`).

1. Crea el `.env` a partir del ejemplo y ajusta las credenciales. El archivo no se versiona.

   ```sh
   cp .env.example .env
   ```

2. Construye y levanta los servicios.

   ```sh
   docker compose up -d --build
   ```

   El contenedor `app` espera a que `db` esté sana (`pg_isready`), aplica las migraciones y arranca `gunicorn` en el puerto `8000`.

3. Comprueba el estado y una predicción real.

   ```sh
   curl http://localhost:8000/api/v1/health
   curl -F "image=@foto.png" -F "source=upload" http://localhost:8000/api/v1/predictions
   ```

4. Para ver los logs de la aplicación y detener el entorno.

   ```sh
   docker compose logs -f app
   docker compose down
   ```

`docker compose down -v` elimina además el volumen `db_data` con las predicciones.

Detalles de la imagen:

| Aspecto | Implementación |
| --- | --- |
| Base | `python:3.12.11-slim-bookworm` con `uv` `0.12.13` (versiones fijas). |
| Dependencias | `uv sync --locked --no-dev` con PyTorch CPU desde el índice de `pyproject.toml`. |
| Copia | Selectiva: `app/`, `migrations/`, `ml_training/reports/metrics.json`, `wsgi.py`, `entrypoint.sh`, `README.md`, `pyproject.toml` y `uv.lock`. El dataset y `.env` nunca entran en la imagen. |
| Usuario | `appuser` (uid 1000), sin root. `logs/` se crea dentro de `/app`. |
| Servidor | Gunicorn con **un worker y cuatro hilos** en el puerto `8000`; así se evita que varios procesos roten el mismo log y se carga el modelo una sola vez. |
| Migraciones | `entrypoint.sh` ejecuta `flask --app wsgi db upgrade` al arrancar. |
| Métricas | `ml_training/reports/metrics.json` se copia a la imagen para que `/api/v1/model` las muestre. |

## Logs de aplicación

La aplicación escribe en `stderr` y en `logs/app.log` por defecto. La carpeta `logs/` se crea automáticamente al arrancar. La rotación conserva hasta cinco respaldos, de `app.log.1` a `app.log.5`, con la configuración predeterminada.

En Docker, Gunicorn usa un solo worker con cuatro hilos, de modo que un único proceso escribe y rota `logs/app.log`. Si se aumentan los workers, varios procesos podrían intentar rotar el archivo a la vez; en ese caso convendría escribir los logs solo a `stderr` y dejarlos al gestor de contenedores.
