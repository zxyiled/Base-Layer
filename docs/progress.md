# Estado de los módulos

La rama base de integración es `ML-project`.

| Módulo | Estado | Responsable | Rama |
| --- | --- | --- | --- |
| M0 · Configuración inicial | Cerrado | Sin registrar | Sin registrar |
| M1 · Datos y ML | Cerrado y fusionado en `ML-project` (PR #7) | Agente de ML | `modulo-1-datos-ml` |
| M2 · Persistencia | Cerrado y fusionado en `ML-project` (PR #8) | Santiago Goez | `modulo-2` |
| M3 · Logs | Cerrado por el agente. Apertura del PR y fusión en `ML-project` a cargo de una persona. | Agente de backend | `modulo-3-logs` |
| M4 · Servicios e inferencia | Pendiente | Por registrar | Por registrar |
| M5 · API | Pendiente | Por registrar | Por registrar |
| M6 · Docker | Pendiente | Por registrar | Por registrar |
| M7 · Frontend | Pendiente | Por registrar | Por registrar |
| M8 · README, documentación final y diapositivas | Pendiente | Por registrar | Por registrar |

El cierre de M1 reportó **25 pruebas aprobadas** con `uv run pytest`. La cobertura de ML incluye preprocesamiento, partición con datos sintéticos y con el manifiesto versionado, predictor con un artefacto mínimo y evaluación con la prueba real pendiente. [Pruebas de ML](../tests/test_ml/)

La corrección de M2 de `fix/modulo-2-persistencia` se fusionó en `ML-project` en el PR #9.

La verificación de la corrección de M2 registró **55 pruebas aprobadas sin advertencias** con `uv run pytest`. Las cinco nuevas cubren los campos de predicción, `created_at` en UTC, el filtro por fechas, el rechazo de confianza fuera de rango y la comparación del esquema que crea Alembic con los modelos en SQLite. Se verificaron `db upgrade` y `db check` en SQLite y PostgreSQL 17.6, sin diferencias detectadas. En PostgreSQL también se verificaron la inserción con todos los campos, el filtro por fechas, las estadísticas y el rechazo de una confianza de `2` con `IntegrityError`. La aplicación arrancó correctamente. [Pruebas de persistencia](../tests/test_repositories/)

La verificación de M3 reportó **67 pruebas aprobadas** con `uv run pytest`. Cubren la configuración desde `create_app()`, la creación de la carpeta, el formato UTC, el filtrado por nivel, la rotación, la reconfiguración sin duplicados, la eliminación de colores ANSI del archivo y la lectura de logs. Se añadieron dos casos para el lector, sobre la cabecera de un traceback largo y las entradas devueltas después de un traceback, y uno que comprueba que las migraciones conservan los handlers de la aplicación. Las pruebas de migraciones también verifican la eliminación de la tabla de logs. El arranque con `uv run flask --app wsgi run` escribió en el archivo con fecha y hora UTC. En PostgreSQL 17.6 se verificó el ciclo `upgrade`, `check`, `downgrade` a `6bfedced69da` y un segundo `upgrade` y `check`. El `downgrade` recreó la tabla y ambas comprobaciones de esquema pasaron sin diferencias. [Pruebas de logs](../tests/test_logging/)

## Diferencias con el plan

- **Selección del artefacto.** La mayor exactitud de validación eligió la época 3, al final de la etapa de cabeza, cuyo artefacto dio **0,9915** en `Test/`. Después de ver ese resultado, se adoptó la menor pérdida de validación con la exactitud como desempate. Al repetir el entrenamiento con la misma semilla y las mismas métricas por época, el nuevo criterio eligió la época 5, de ajuste fino, con pérdida de validación **0,0096**, exactitud de validación **0,9963** y exactitud oficial **0,9938**. [Informe del modelo](ml-report.md#cambio-del-criterio-de-selección)
- **Prueba con fotos propias.** La evaluación está implementada y sigue pendiente de la captura de unas 10 fotos por fruta.
- **Versiones del modelo (M2).** Se conserva `ModelVersion`, incorporado fuera del plan, para identificar qué artefacto generó cada predicción. En M4 se registrará la versión del artefacto cargado y se enlazará cada predicción con `model_version_id`. El repositorio conserva `activate()` y `get_active()`. La aplicación cargará un único modelo.
- **Esquema y filtros (M2).** El M2 original creaba las tablas con `db.create_all()`. La corrección introduce migraciones con Flask-Migrate y Alembic, y completa los campos `file_size_bytes` e `inference_ms` y el filtro por fechas previstos en el plan.
- **Registros de aplicación (M3).** Los logs se escriben solo en consola y en un archivo rotativo, según la decisión aprobada. La migración `7e4b0e45cdaf` elimina la tabla `app_logs`. Su `downgrade` recrea la tabla vacía con los tipos de la revisión inicial. Así se mantiene la escritura de logs durante fallos de la base de datos y se evita la recursión con los logs de SQLAlchemy.
- **Rotación con Gunicorn (M6).** Queda pendiente definir la configuración. Varios workers que comparten el archivo pueden intentar rotarlo al mismo tiempo. Una opción es usar un solo worker con hilos.
