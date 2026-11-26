# Resumen de evaluación

Modelo: `mobilenet_v3_small`. Clases: banano, fresa, limon, manzana, naranja, pera, tomate, uva.

Mejor época en validación: 5 (finetune), accuracy 0.9963.

## Prueba oficial (Fruits-360 `Test/`)

Accuracy: **0.9938** sobre 17487 imágenes.

| Clase | Precisión | Recall | F1 | Soporte |
|---|---|---|---|---|
| banano | 1.000 | 1.000 | 1.000 | 719 |
| fresa | 1.000 | 1.000 | 1.000 | 479 |
| limon | 1.000 | 1.000 | 1.000 | 330 |
| manzana | 0.991 | 0.991 | 0.991 | 5506 |
| naranja | 0.995 | 1.000 | 0.997 | 1180 |
| pera | 0.997 | 0.987 | 0.992 | 4164 |
| tomate | 0.997 | 0.999 | 0.998 | 3413 |
| uva | 0.981 | 1.000 | 0.991 | 1696 |
| **macro** | 0.995 | 0.997 | 0.996 | 17487 |

Variedades con menor accuracy:

- Pear Red 1: 0.811 (222 imágenes)
- Apple 6: 0.879 (157 imágenes)
- Tomato Cherry Yellow 1: 0.950 (100 imágenes)
- Apple 9: 0.952 (231 imágenes)
- Pear 1: 0.957 (164 imágenes)

## Prueba real (`data/real_test/`)

Estado: ok. Accuracy: **0.5375** sobre 80 fotos.

| Clase | Precisión | Recall | F1 | Soporte |
|---|---|---|---|---|
| banano | 0.727 | 0.800 | 0.762 | 10 |
| fresa | 0.750 | 0.900 | 0.818 | 10 |
| limon | 0.000 | 0.000 | 0.000 | 10 |
| manzana | 0.636 | 0.700 | 0.667 | 10 |
| naranja | 1.000 | 0.100 | 0.182 | 10 |
| pera | 0.303 | 1.000 | 0.465 | 10 |
| tomate | 0.889 | 0.800 | 0.842 | 10 |
| uva | 0.000 | 0.000 | 0.000 | 10 |
| **macro** | 0.538 | 0.538 | 0.467 | 80 |
