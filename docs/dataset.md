# Dataset y preparación

El proyecto usa **Fruits-360**, de Mihai Oltean (2017–), versión `2026.10.27.0` de la rama **100x100**, bajo licencia **CC BY-SA 4.0**. Las imágenes de 100 × 100 píxeles provienen de videos cortos con rotación controlada y fondo blanco. [Fuente oficial de Fruits-360 100x100](https://github.com/fruits-360/fruits-360-100x100/blob/main/README.md)

## Clases y balance

Cada carpeta de variedad se asigna a una fruta si empieza por el prefijo seguido de un espacio, sin distinguir mayúsculas. Esto deja fuera las carpetas de `Grapefruit` de la clase `uva`. Por decisión del responsable del proyecto, se excluyeron `Orange peeled 1` y `Strawberry Wedge 1` porque contienen fruta pelada o cortada.

| Etiqueta | Prefijo | Variedades | Entrenamiento | Validación | Prueba oficial |
| --- | --- | ---: | ---: | ---: | ---: |
| `banano` | Banana | 6 | 1 200 | 300 | 719 |
| `fresa` | Strawberry | 3 | 1 180 | 214 | 479 |
| `limon` | Lemon | 2 | 783 | 159 | 330 |
| `manzana` | Apple | 30 | 1 200 | 300 | 5 506 |
| `naranja` | Orange | 5 | 1 200 | 300 | 1 180 |
| `pera` | Pear | 20 | 1 200 | 300 | 4 164 |
| `tomate` | Tomato | 19 | 1 200 | 300 | 3 413 |
| `uva` | Grape | 9 | 1 200 | 300 | 1 696 |
| **Total** | | **94** | **9 163** | **2 173** | **17 487** |

El limón es la clase más pequeña y contiene solo `Lemon 1` y `Lemon Meyer 1`. El submuestreo aplica un tope por fruta de 1 200 imágenes de entrenamiento y 300 de validación con semilla 42. Durante el entrenamiento, `WeightedRandomSampler` compensa el desbalance residual mediante pesos inversos al tamaño de cada clase. La prueba oficial conserva las 17 487 imágenes de las variedades incluidas. [Lista exacta de variedades y conteos antes y después del submuestreo](../data/processed/manifest_info.json)

## Partición por índice de fotograma

Los fotogramas vecinos son casi idénticos. Separarlos al azar podría inflar las métricas de validación. En cada variedad de `Training/` se extrae el índice `N` de nombres como `N_100.jpg`, `r_N_100.jpg`, `r0_N_100.jpg`, `r1_N_100.jpg` y `r2_N_100.jpg`.

1. Se ordenan los índices únicos y se reserva el último 15 %, redondeado hacia arriba, para validación.
2. Se conservan para entrenamiento solo los índices que cumplen `N < min(val) - 10`. Se descartan los diez valores de índice inmediatamente anteriores al primero de validación.
3. Todos los archivos de una misma variedad que comparten `N` se asignan juntos antes del submuestreo. Las filas de `Test/` se reservan para evaluación y quedan fuera del entrenamiento y la validación.

La prueba automática comprueba sobre el manifiesto versionado el origen de las filas, la ausencia de índices compartidos entre entrenamiento y validación y el hueco por variedad. [Pruebas de partición](../tests/test_ml/test_split.py)

El manifiesto contiene una fila por imagen seleccionada con las columnas `path` (ruta relativa a la raíz del dataset), `fruit`, `variety`, `split` (`train`, `val` o `test`) e `index`. [Manifiesto CSV](../data/processed/manifest.csv)

## Preprocesamiento y cambio de dominio

Las transformaciones compartidas corrigen la orientación EXIF, convierten a RGB y recortan un cuadrado centrado para preservar las proporciones en fotos rectangulares. Validación, prueba e inferencia redimensionan a 224 × 224 con interpolación bilineal. Entrenamiento aplica recorte aleatorio redimensionado a 224 × 224, volteo horizontal, rotación de hasta 20° y variación leve de color. Ambas transformaciones usan la media RGB `(0.485, 0.456, 0.406)` y la desviación estándar `(0.229, 0.224, 0.225)` de ImageNet para mantener la escala de entrada de los pesos preentrenados. [Preprocesamiento compartido](../app/ml/preprocessing.py)

La prueba oficial mide el rendimiento en el entorno controlado de Fruits-360. La prueba real obtuvo 53,7 % de exactitud sobre 54 imágenes descargadas de internet con fondos, iluminación y encuadres variados. La muestra cubre seis de las ocho clases y queda pendiente medir el rendimiento con fotos propias tomadas con cámara. [Informe del modelo](ml-report.md#prueba-real)
