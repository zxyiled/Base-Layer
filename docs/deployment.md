# Despliegue

## Base de datos

La aplicación usa PostgreSQL y Flask-SQLAlchemy. La conexión se toma de `DATABASE_URL`; las credenciales nunca se escriben en el código.

| Variable | Uso |
| --- | --- |
| `DATABASE_URL` | URL de conexión. Las variantes `postgresql://` y `postgres://` se convierten a `postgresql+psycopg://` para usar psycopg 3. |
| `SECRET_KEY` | Clave de Flask. |
| `LOG_LEVEL` | Nivel de registro (`INFO` por defecto). |

Para crear el entorno local, copia `.env.example` a `.env` y ajusta los valores:

```sh
cp .env.example .env
```

Las tablas se crean con el comando de Flask:

```sh
uv run flask --app wsgi init-db
```

El comando ejecuta `db.create_all()`, que crea las tablas que falten sin borrar datos existentes. No hay migraciones versionadas (Alembic): si cambia el esquema, hay que recrear las tablas o migrar los datos a mano.

`create_app()` en `app/__init__.py` inicializa la configuración y la base de datos. El arranque del servidor y los contenedores se documentarán al cerrar el módulo de Docker.

> La cámara del navegador solo funciona en `localhost` o con HTTPS.
