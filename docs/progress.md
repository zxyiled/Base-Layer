# Estado de los módulos

La rama base de integración es `ML-project`.

| Módulo | Estado | Responsable | Rama |
| --- | --- | --- | --- |
| M0 · Configuración inicial | Cerrado | Sin registrar | Sin registrar |
| M1 · Datos y ML | Cerrado y fusionado en `ML-project` (PR #7) | Agente de ML | `modulo-1-datos-ml` |
| M2 · Persistencia | Cerrado por el agente, pendiente de fusión a cargo de una persona | Agente de persistencia | `modulo-2` |
| M3 · Logs | Pendiente | Por registrar | Por registrar |
| M4 · Servicios e inferencia | Pendiente | Por registrar | Por registrar |
| M5 · API | Pendiente | Por registrar | Por registrar |
| M6 · Docker | Pendiente | Por registrar | Por registrar |
| M7 · Frontend | Pendiente | Por registrar | Por registrar |
| M8 · README, documentación final y diapositivas | Pendiente | Por registrar | Por registrar |

El cierre de M1 reportó **25 pruebas aprobadas** con `uv run pytest`. La cobertura de ML incluye preprocesamiento, partición con datos sintéticos y con el manifiesto versionado, predictor con un artefacto mínimo y evaluación con la prueba real pendiente. [Pruebas de ML](../tests/test_ml/)

El cierre de M2 dejó **50 pruebas aprobadas** en total: las 25 de M1 y 25 nuevas. La cobertura de persistencia incluye los tres modelos (`Prediction`, `ModelVersion` y `AppLog`), restricciones de la base de datos, serialización JSON, paginación, filtros, agregados para estadísticas, activación de una sola versión del modelo y normalización de `DATABASE_URL`. También se verificaron `flask --app wsgi init-db` y el arranque de la aplicación con SQLite. El esquema se crea con `db.create_all()`; no se usa Alembic. [Pruebas de persistencia](../tests/test_repositories/)

## Diferencias con el plan

- **Selección del artefacto.** La mayor exactitud de validación eligió la época 3, al final de la etapa de cabeza, cuyo artefacto dio **0,9915** en `Test/`. Después de ver ese resultado, se adoptó la menor pérdida de validación con la exactitud como desempate. Al repetir el entrenamiento con la misma semilla y las mismas métricas por época, el nuevo criterio eligió la época 5, de ajuste fino, con pérdida de validación **0,0096**, exactitud de validación **0,9963** y exactitud oficial **0,9938**. [Informe del modelo](ml-report.md#cambio-del-criterio-de-selección)
- **Prueba con fotos propias.** La evaluación está implementada y sigue pendiente de la captura de unas 10 fotos por fruta.
