# Despliegue

## Base de datos

La aplicación usa PostgreSQL y Flask-SQLAlchemy. Configura la conexión mediante `DATABASE_URL` en el entorno.

| Variable | Uso |
| --- | --- |
| `DATABASE_URL` | URL de conexión. Las variantes `postgresql://` y `postgres://` se convierten a `postgresql+psycopg://` para usar psycopg 3. |
| `SECRET_KEY` | Clave de Flask. |
| `LOG_LEVEL` | Nivel de registro (`INFO` por defecto). |

Para crear el entorno local, copia `.env.example` a `.env` y ajusta los valores.

```sh
cp .env.example .env
```

Con PostgreSQL en ejecución, aplica las migraciones versionadas con Flask-Migrate 4.1.0 y Alembic 1.20.1. La revisión inicial crea las tablas en un esquema vacío.

```sh
uv run flask --app wsgi db upgrade
uv run flask --app wsgi db check
```

Si la base conserva tablas creadas por el M2 original con `db.create_all()`, la revisión inicial intentará crearlas de nuevo. Usa una base vacía para aplicar esa revisión. La migración de los datos de una instalación anterior queda pendiente si se necesita conservarlos.

Tras cambiar los modelos, genera una revisión y examina el archivo en `migrations/versions/` antes de aplicarla.

```sh
uv run flask --app wsgi db migrate -m "describe el cambio"
```

Aplica la revisión con `db upgrade` y comprueba con `db check` si quedan diferencias detectables entre el esquema y los modelos. En M6, `entrypoint.sh` ejecutará `flask db upgrade` antes de arrancar la aplicación.

> La cámara del navegador solo funciona en `localhost` o con HTTPS.
