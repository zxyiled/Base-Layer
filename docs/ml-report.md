# Informe del modelo

## Modelo y entrenamiento

Se usó **MobileNetV3-Small** de torchvision con pesos preentrenados `IMAGENET1K_V1`. La última capa lineal se sustituyó por una de ocho salidas, una por fruta.

El entorno de entrenamiento usó `torch 2.15.0+cpu` y `torchvision 0.29.2+cpu` del índice `pytorch-cpu`. Pillow carga imágenes, scikit-learn calcula las métricas y Matplotlib genera las gráficas.

| Etapa | Épocas | Parámetros entrenados | Tasa de aprendizaje |
| --- | --- | --- | ---: |
| Cabeza | 1–3 | Clasificador | 0,001 |
| Ajuste fino | 4–8 | Últimos cuatro bloques de `features` y clasificador | 0,0001 |

| Parámetro | Valor |
| --- | --- |
| Optimizador y pérdida | AdamW y entropía cruzada |
| Tamaño de lote | 64 en entrenamiento y 128 en validación |
| Semilla | 42 |
| Muestreo de entrenamiento | `WeightedRandomSampler` con reemplazo y pesos inversos a la frecuencia de cada clase |
| Bloques congelados | En modo evaluación para mantener fijas sus estadísticas de BatchNorm |
| Selección del artefacto | Menor pérdida de validación, con mayor exactitud (*accuracy*) en caso de empate |

Las ocho épocas en CPU tomaron entre 63,2 y 142,7 segundos cada una (aproximadamente de 1 min a 2 min 23 s), según `logs/train_run.log` y el historial. [Historial de entrenamiento](../ml_training/reports/history.json)

Al descongelar los últimos bloques en la época 4, sus capas BatchNorm empezaron a actualizar sus estadísticas en modo entrenamiento. La pérdida de entrenamiento subió transitoriamente de 0,0286 a 0,2231 y bajó a 0,0194 en la época 5. [Curvas de pérdida y exactitud de entrenamiento y validación](../ml_training/reports/training_curves.png)

## Cambio del criterio de selección

La primera corrida eligió la época 3 por su exactitud de validación de **0,9986**. En ese tramo del entrenamiento la métrica ya rondaba 0,994–0,999 (con 0,9931 al inicio del ajuste fino). El artefacto de la época 3 solo incorporaba el entrenamiento de la cabeza y obtuvo **0,9915** en la prueba oficial.

Después de ver ese resultado de `Test/`, se cambió el criterio a menor pérdida de validación para distinguir épocas con exactitud similar. Se repitió el entrenamiento con la misma semilla y se reprodujeron las métricas por época. El criterio eligió la **época 5**, ya en ajuste fino, con pérdida de validación **0,0096** y exactitud de validación **0,9963**. El artefacto final obtuvo **0,9938** en la prueba oficial. Las imágenes de `Test/` quedaron fuera del ajuste de pesos. Como el primer resultado influyó en el cambio de criterio, haría falta un conjunto de prueba independiente para estimar la mejora.

## Prueba oficial

La exactitud global fue **0,9938 (99,38 %)** sobre **17 487 imágenes** de `Test/`. El promedio macro da el mismo peso a cada clase. [Métricas completas](../ml_training/reports/metrics.json)

| Clase | Precisión | Recall | F1 | Soporte |
| --- | ---: | ---: | ---: | ---: |
| banano | 1,000 | 1,000 | 1,000 | 719 |
| fresa | 1,000 | 1,000 | 1,000 | 479 |
| limon | 1,000 | 1,000 | 1,000 | 330 |
| manzana | 0,991 | 0,991 | 0,991 | 5 506 |
| naranja | 0,995 | 1,000 | 0,997 | 1 180 |
| pera | 0,997 | 0,987 | 0,992 | 4 164 |
| tomate | 0,997 | 0,999 | 0,998 | 3 413 |
| uva | 0,981 | 1,000 | 0,991 | 1 696 |
| **Promedio macro** | **0,995** | **0,997** | **0,996** | **17 487** |

La confusión más frecuente fue pera clasificada como manzana (51 imágenes). También se clasificaron 27 manzanas como uvas y 9 como tomates. Los cinco tomates mal clasificados se predijeron como uvas. [Matriz de confusión oficial](../ml_training/reports/confusion_matrix_official.png)

| Variedades con menor exactitud | Exactitud | Imágenes |
| --- | ---: | ---: |
| Pear Red 1 | 0,811 | 222 |
| Apple 6 | 0,879 | 157 |
| Tomato Cherry Yellow 1 | 0,950 | 100 |
| Apple 9 | 0,952 | 231 |
| Pear 1 | 0,957 | 164 |

[Resumen de evaluación](../ml_training/reports/summary.md)

## Prueba real

La prueba real obtuvo **0,5370 (53,7 %), con 29 aciertos en 54 imágenes**. La prueba oficial se mantuvo en **0,9938 (99,38 %)** sobre **17 487 imágenes** de Fruits-360. [Métricas de ambas pruebas](../ml_training/reports/metrics.json)

El equipo descargó las imágenes de `data/real_test/` de internet. Hay imágenes de stock y de otros sitios web, y algunas parecen generadas o retocadas. La evaluación con fotos propias tomadas con cámara, prevista en el plan, queda por medir. [Resumen de evaluación](../ml_training/reports/summary.md)

La prueba quedó **incompleta**. Hay 60 archivos, 10 por cada una de las seis clases presentes. Pera y uva carecen de imágenes. El evaluador solo admite JPG, JPEG, PNG, WebP y BMP, por lo que quedaron fuera seis archivos AVIF (dos de limón, uno de naranja y tres de tomate).

| Clase | Aciertos / evaluadas | Precisión | Recall | F1 | Predicciones erróneas |
| --- | ---: | ---: | ---: | ---: | --- |
| banano | 8/10 | 0,889 | 0,800 | 0,842 | 2 como pera |
| fresa | 9/10 | 0,818 | 0,900 | 0,857 | 1 como manzana |
| limon | 0/8 | 0,000 | 0,000 | 0,000 | 6 como pera, 1 como manzana y 1 como tomate |
| manzana | 7/10 | 0,700 | 0,700 | 0,700 | 3 como pera |
| naranja | 0/9 | 0,000 | 0,000 | 0,000 | 4 como pera, 3 como limón, 1 como banano y 1 como manzana |
| pera | Sin imágenes | — | — | — | — |
| tomate | 5/7 | 0,833 | 0,714 | 0,769 | 2 como fresa |
| uva | Sin imágenes | — | — | — | — |

El resumen automático promedia las ocho clases e incluye pera y uva con ceros. Su precisión, recall y F1 macro son **0,405**, **0,389** y **0,396**. Sobre las seis clases con imágenes evaluadas, los promedios son **0,540**, **0,519** y **0,528**, respectivamente.

La etiqueta «pera» concentró 15 de los 25 errores. Casi todos los limones de la muestra eran verdes (limas), mientras que Fruits-360 contiene limones amarillos de las variedades `Lemon 1` y `Lemon Meyer 1`. Las seis predicciones de limón como pera tuvieron confianzas de 0,91 a 1,00, incluido el único limón amarillo, con 0,91. Las naranjas de la muestra se confundieron principalmente con pera y limón. [Matriz de confusión de la prueba real](../ml_training/reports/confusion_matrix_real.png)

La confianza media fue 0,91 en los aciertos y 0,77 en los errores. Varios errores alcanzaron una confianza de al menos 0,99, por lo que un umbral simple de confianza resulta insuficiente para detectarlos. El cambio de dominio ayuda a explicar la caída de exactitud. Las imágenes web varían en iluminación y fondo, a veces oscuro, y algunas muestran varias frutas. Fruits-360 usa fondo blanco y rotación controlada.
