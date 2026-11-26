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

Estado: incompleta. Accuracy: **0.5370** sobre 54 fotos.

| Clase | Precisión | Recall | F1 | Soporte |
|---|---|---|---|---|
| banano | 0.889 | 0.800 | 0.842 | 10 |
| fresa | 0.818 | 0.900 | 0.857 | 10 |
| limon | 0.000 | 0.000 | 0.000 | 8 |
| manzana | 0.700 | 0.700 | 0.700 | 10 |
| naranja | 0.000 | 0.000 | 0.000 | 9 |
| pera | 0.000 | 0.000 | 0.000 | 0 |
| tomate | 0.833 | 0.714 | 0.769 | 7 |
| uva | 0.000 | 0.000 | 0.000 | 0 |
| **macro** | 0.405 | 0.389 | 0.396 | 54 |

Clases sin fotos: pera, uva.
