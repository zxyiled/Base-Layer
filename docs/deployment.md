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

Aplica la revisión con `db upgrade` y comprueba con `db check` si quedan diferencias detectables entre el esquema y los modelos. En M6, `entrypoint.sh` ejecutará `flask db upgrade` antes de arrancar la aplicación.

> La cámara del navegador solo funciona en `localhost` o con HTTPS.

## Logs de aplicación

La aplicación escribe en `stderr` y en `logs/app.log` por defecto. La carpeta `logs/` se crea automáticamente al arrancar. La rotación conserva hasta cinco respaldos, de `app.log.1` a `app.log.5`, con la configuración predeterminada.

En M6 queda pendiente definir cómo rotar el archivo con Gunicorn. Si varios workers comparten el archivo, cada proceso puede intentar rotarlo por su cuenta. Una opción es usar un solo worker con hilos.
