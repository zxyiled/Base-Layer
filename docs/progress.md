# Estado de los módulos

La rama base de integración es `ML-project`.

| Módulo | Estado | Responsable | Rama |
| --- | --- | --- | --- |
| M0 · Configuración inicial | Cerrado | Sin registrar | Sin registrar |
| M1 · Datos y ML | Cerrado por el agente, pendiente de fusión a cargo de una persona | Agente de ML | `modulo-1-datos-ml` |
| M2 · Persistencia | Pendiente | Por registrar | Por registrar |
| M3 · Logs | Pendiente | Por registrar | Por registrar |
| M4 · Servicios e inferencia | Pendiente | Por registrar | Por registrar |
| M5 · API | Pendiente | Por registrar | Por registrar |
| M6 · Docker | Pendiente | Por registrar | Por registrar |
| M7 · Frontend | Pendiente | Por registrar | Por registrar |
| M8 · README, documentación final y diapositivas | Pendiente | Por registrar | Por registrar |

El cierre de M1 reportó **25 pruebas aprobadas** con `uv run pytest`. La cobertura de ML incluye preprocesamiento, partición con datos sintéticos y con el manifiesto versionado, predictor con un artefacto mínimo y evaluación con la prueba real pendiente. El arranque de Flask queda fuera de la verificación de M1 porque `create_app()` todavía está pendiente. [Pruebas de ML](../tests/test_ml/)

## Diferencias con el plan

- **Selección del artefacto.** La mayor exactitud de validación eligió la época 3, al final de la etapa de cabeza, cuyo artefacto dio **0,9915** en `Test/`. Después de ver ese resultado, se adoptó la menor pérdida de validación con la exactitud como desempate. Al repetir el entrenamiento con la misma semilla y las mismas métricas por época, el nuevo criterio eligió la época 5, de ajuste fino, con pérdida de validación **0,0096**, exactitud de validación **0,9963** y exactitud oficial **0,9938**. [Informe del modelo](ml-report.md#cambio-del-criterio-de-selección)
- **Prueba con fotos propias.** La evaluación está implementada y sigue pendiente de la captura de unas 10 fotos por fruta.
