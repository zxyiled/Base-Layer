# Estado de los módulos

La rama base de integración es `ML-project`.

| Módulo | Estado | Responsable | Rama |
| --- | --- | --- | --- |
| M0 · Configuración inicial | Cerrado | Sin registrar | Sin registrar |
| M1 · Datos y ML | Cerrado y fusionado en `ML-project` (PR #7). La prueba con fotos reales sigue **pendiente**. | Agente de ML | `modulo-1-datos-ml` |
| M2 · Persistencia | Cerrado y fusionado en `ML-project` (PR #8) | Santiago Goez | `modulo-2` |
| M3 · Logs | Cerrado y fusionado en `ML-project` (PR #10) | Agente de backend | `modulo-3-logs` |
| M4 · Servicios e inferencia | Cerrado y fusionado en `ML-project` (PR #11) | Agente de backend | `modulo-4-servicios` |
| M5 · API | Cerrado y fusionado en `ML-project` (PR #12) | Agente de backend | `modulo-5-api` |
| M6 · Docker | Versión inicial fusionada en `ML-project` (PR #13). Corrección verificada, pendiente de PR y merge por una persona. | Agente de backend | `modulo-6-docker`, `fix/modulo-6-docker` |
| M7 · Frontend | Cerrado en la rama `modulo-7-Frontend` (pendiente de merge por una persona) | Agente de frontend | `modulo-7-Frontend` |
| M8 · README, documentación final y diapositivas | Pendiente | Por registrar | Por registrar |

El cierre de M1 reportó **25 pruebas aprobadas** con `uv run pytest`. La cobertura de ML incluye preprocesamiento, partición con datos sintéticos y con el manifiesto versionado, predictor con un artefacto mínimo y evaluación con la prueba real pendiente. [Pruebas de ML](../tests/test_ml/)

La corrección de M2 de `fix/modulo-2-persistencia` se fusionó en `ML-project` en el PR #9.

La verificación de la corrección de M2 registró **55 pruebas aprobadas sin advertencias** con `uv run pytest`. Las cinco nuevas cubren los campos de predicción, `created_at` en UTC, el filtro por fechas, el rechazo de confianza fuera de rango y la comparación del esquema que crea Alembic con los modelos en SQLite. Se verificaron `db upgrade` y `db check` en SQLite y PostgreSQL 17.6, sin diferencias detectadas. En PostgreSQL también se verificaron la inserción con todos los campos, el filtro por fechas, las estadísticas y el rechazo de una confianza de `2` con `IntegrityError`. La aplicación arrancó correctamente. [Pruebas de persistencia](../tests/test_repositories/)

La verificación de M3 reportó **67 pruebas aprobadas** con `uv run pytest`. Cubren la configuración desde `create_app()`, la creación de la carpeta, el formato UTC, el filtrado por nivel, la rotación, la reconfiguración sin duplicados, la eliminación de colores ANSI del archivo y la lectura de logs. Se añadieron dos casos para el lector, sobre la cabecera de un traceback largo y las entradas devueltas después de un traceback, y uno que comprueba que las migraciones conservan los handlers de la aplicación. Las pruebas de migraciones también verifican la eliminación de la tabla de logs. El arranque con `uv run flask --app wsgi run` escribió en el archivo con fecha y hora UTC. En PostgreSQL 17.6 se verificó el ciclo `upgrade`, `check`, `downgrade` a `6bfedced69da` y un segundo `upgrade` y `check`. El `downgrade` recreó la tabla y ambas comprobaciones de esquema pasaron sin diferencias. [Pruebas de logs](../tests/test_logging/)

La verificación de M4 reportó **91 pruebas aprobadas** con `uv run pytest` (24 nuevas). Cubren la decodificación con Pillow (bytes vacíos, corruptos y contenido no-imagen), las tres fuentes permitidas, la persistencia de etiqueta, confianza, top-3, tamaño y tiempo de inferencia, el enlace con la versión del modelo, el historial paginado con filtros, el detalle ausente, las estadísticas, la información del modelo con y sin métricas y la lectura del log. También se comprobó el flujo completo con el artefacto real y SQLite (predicción guardada, versión activa y métricas oficiales) y el arranque de la app con `flask --app wsgi routes`. [Pruebas de servicios](../tests/test_services/)

La verificación de M5 reportó **127 pruebas aprobadas** con `uv run pytest` (36 nuevas). Cubren los siete endpoints, los códigos `404`, `413`, `415`, `422`, `503`, el sobre de error, la paginación y los filtros por etiqueta, fuente y fechas, el enlace con la versión del modelo, la salud con la base de datos caída y el contrato de `docs/api.md`. También se probó el flujo completo con el artefacto real y SQLite (predicción `201`, listado, estadísticas, modelo con métricas oficiales, logs y salud) y `flask --app wsgi routes` mostró las siete rutas. [Pruebas de API](../tests/test_api/)

La verificación inicial de M6 se hizo con Docker 29.7.2 y `docker compose up -d --build`. El contenedor esperó a PostgreSQL 17.6 (`pg_isready`), aplicó las dos migraciones y arrancó Gunicorn. `GET /api/v1/health` respondió `200` con base de datos y modelo cargados; `POST /api/v1/predictions` respondió `201` y la fila quedó en PostgreSQL (`id=1`, `limon`, `camera`, `inference_ms=32.478`, `model_version_id=1`). `GET /api/v1/predictions`, `/stats` y `/model` (accuracy 0.9938) respondieron `200`, y el log del contenedor registró los metadatos de la inferencia. Pasaron **127 pruebas** con `uv run pytest`.

La corrección de M6 reportó **130 pruebas aprobadas** con `uv run pytest` (3 nuevas). Se retiró `app/api/v1/classes.py`, que estaba vacío. La verificación con Docker y PostgreSQL 17.6 registró los siguientes resultados.

| Comprobación | Resultado |
| --- | --- |
| Tamaño de imagen | De 5,7 GB a 1,72 GB. |
| API | `/api/v1/health` y `/api/v1/model` respondieron `200`. Una predicción real respondió `201` con etiqueta `fresa` y confianza de 0,99999. |
| Errores | Imagen corrupta `422`, GIF `415`, subida de 11 MB `413` en español, `404` y `405` de la API en español y `404` fuera de `/api/` en HTML. |
| Contenedor | uid 1000, `/app/app` de `root` en solo lectura para `appuser`, `/app/logs` escribible por `appuser` y `sklearn` ausente. |

La verificación de M7 reportó **133 pruebas aprobadas** con `uv run pytest` (3 nuevas). Cubren el registro del blueprint web, el HTML en español con cámara, subida, resultado, historial, estadísticas, modelo y registros, y el servicio de los archivos estáticos. `node --check` validó el JavaScript y `flask --app wsgi routes` mostró `web.index` en `/` junto a las siete rutas de la API. La interfaz consume solo `docs/api.md`; no se añadieron endpoints ni se modificó la lógica de negocio. [Pruebas web](../tests/test_web/)

## Diferencias con el plan

- **Selección del artefacto.** La mayor exactitud de validación eligió la época 3, al final de la etapa de cabeza, cuyo artefacto dio **0,9915** en `Test/`. Después de ver ese resultado, se adoptó la menor pérdida de validación con la exactitud como desempate. Al repetir el entrenamiento con la misma semilla y las mismas métricas por época, el nuevo criterio eligió la época 5, de ajuste fino, con pérdida de validación **0,0096**, exactitud de validación **0,9963** y exactitud oficial **0,9938**. [Informe del modelo](ml-report.md#cambio-del-criterio-de-selección)
- **Prueba con fotos propias (pendiente).** La evaluación está implementada, pero `data/real_test/` no existe todavía: falta la captura de unas 10 fotos por fruta y volver a ejecutar `evaluate.py`. Mientras tanto, `metrics.json` y `summary.md` reportan la prueba real como `pendiente`.
- **Versiones del modelo (M2).** Se conserva `ModelVersion`, incorporado fuera del plan, para identificar qué artefacto generó cada predicción. En M4 se registrará la versión del artefacto cargado y se enlazará cada predicción con `model_version_id`. El repositorio conserva `activate()` y `get_active()`. La aplicación cargará un único modelo.
- **Esquema y filtros (M2).** El M2 original creaba las tablas con `db.create_all()`. La corrección introduce migraciones con Flask-Migrate y Alembic, y completa los campos `file_size_bytes` e `inference_ms` y el filtro por fechas previstos en el plan.
- **Registros de aplicación (M3).** Los logs se escriben solo en consola y en un archivo rotativo, según la decisión aprobada. La migración `7e4b0e45cdaf` elimina la tabla `app_logs`. Su `downgrade` recrea la tabla vacía con los tipos de la revisión inicial. Así se mantiene la escritura de logs durante fallos de la base de datos y se evita la recursión con los logs de SQLAlchemy.
- **Versión del modelo (M4).** `ModelInfoService.ensure_active_version()` registra el artefacto cargado y reutiliza la versión por nombre. Las predicciones aceptan `model_version_id`, pero la API (M5) es quien lo resuelve y lo pasa al servicio.
- **Métricas en la imagen (M4/M6).** La imagen copia `ml_training/reports/metrics.json`, así que `/api/v1/model` muestra las métricas también en Docker.
- **Versión del modelo (M5).** La API resuelve la versión activa en la primera predicción y la reutiliza en `app.extensions["model_version_id"]` mientras dura el proceso.
- **Salud (M5).** `GET /health` responde con un objeto propio (`status`, `database`, `model`), no con el sobre de error, porque es un chequeo de estado y no un error de la API.
- **Gunicorn (M6).** Se usa un solo worker con cuatro hilos porque `RotatingFileHandler` y el registro diferido de la versión del modelo requieren revisión antes de usar varios procesos.
- **Dependencias (corrección de M6).** Se retiraron `pandas` y `requests` por falta de uso. `scikit-learn` y `matplotlib` pasaron al grupo `train`. En local, `uv` incluye `dev` y `train` por defecto. Docker instala solo las dependencias de ejecución.
- **Copia adicional (M6).** Además de lo previsto, la imagen copia `migrations/` (necesario para `entrypoint.sh`) y `ml_training/reports/metrics.json` (para la información del modelo). El resto del `COPY` sigue siendo selectivo.
