# Arquitectura

## Datos, entrenamiento y evaluación

| Componente | Responsabilidad |
| --- | --- |
| `ml_training/prepare_subset.py` | Agrupa variedades por fruta, separa los fotogramas y escribe el manifiesto y sus metadatos en `data/processed/`. |
| `ml_training/common.py` | Comparte rutas, semillas y carga de imágenes entre entrenamiento y evaluación. |
| `ml_training/train.py` | Lee las particiones `train` y `val`, entrena en dos etapas y guarda el mejor artefacto y el historial. |
| `ml_training/evaluate.py` | Carga el artefacto, evalúa la partición `test` y las fotos propias por separado, y escribe los reportes en `ml_training/reports/`. |

## Inferencia local

| Componente | Responsabilidad |
| --- | --- |
| `app/ml/model_factory.py` | Construye MobileNetV3-Small con una capa final de ocho salidas para el modelo del proyecto. El entrenamiento inicializa los pesos de ImageNet y la inferencia carga los pesos locales. |
| `app/ml/preprocessing.py` | Define las transformaciones compartidas. La de evaluación se usa también en validación e inferencia. |
| `app/ml/predictor.py` | Carga el modelo en CPU y clasifica imágenes de Pillow con el modelo en modo evaluación. |
| `app/ml/artifacts/` | Contiene los pesos en `model.pt` (6,2 MB), el orden de clases en `labels.json` y los metadatos de preprocesamiento y entrenamiento en `preprocessing.json`. |

`Predictor.from_artifacts()` carga los archivos una vez por instancia. Luego `predict(image)` aplica el preprocesamiento compartido, convierte las salidas del modelo a probabilidades con *softmax* y devuelve `{label, confidence, top3}`. Cada entrada de `top3` tiene `label` y `confidence`, en orden descendente de confianza. La implementación de las transformaciones vive en `preprocessing.py` y el JSON registra sus parámetros.
