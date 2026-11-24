# Guía de estudio — Clasificador de frutas

Guía para entender la aplicación completa y, en especial, las **diapositivas 8 a 13** de `docs/presentacion/index.html`.

> Esta guía se apoya en el código y en los reportes reales del proyecto:
> `ml_training/reports/metrics.json`, `ml_training/reports/history.json`,
> `ml_training/train.py`, `ml_training/evaluate.py`, `app/ml/`, `app/api/v1/` y `docs/`.
> Si un número de una diapositiva no coincide con esta guía, manda el reporte.

---

## Cómo usar esta guía

| Si tienes… | Lee… |
| --- | --- |
| 10 minutos | Secciones 1, 2 y el resumen de las diapositivas 8–13 (sección 5). |
| 1 hora | Todo el documento, saltando el glosario si ya dominas los términos. |
| Repaso final | Tabla de las 8 épocas, matriz de confusión, autoevaluación y guion de defensa. |

**Objetivo:** poder explicar en voz alta, sin leer, qué hace la app, cómo viaja una imagen desde el navegador hasta PostgreSQL y por qué el 99,38 % debe interpretarse con cuidado.

---

## 1. La app en 60 segundos

Es una aplicación académica que clasifica **8 frutas** en imágenes:

`banano`, `fresa`, `limon`, `manzana`, `naranja`, `pera`, `tomate`, `uva`.

Flujo mínimo:

1. El usuario abre la interfaz web en `/`.
2. Envía una imagen desde la cámara, un archivo o un video (fotogramas).
3. El backend decodifica la imagen con Pillow, la preprocesa y la pasa por **MobileNetV3-Small**.
4. El modelo devuelve etiqueta, confianza y top-3.
5. La predicción se guarda en **PostgreSQL** y se registra metadata en el log.
6. La API responde `201` con JSON y la interfaz muestra el resultado, el historial y las estadísticas.

**Stack:** Flask + PostgreSQL + SQLAlchemy/Flask-Migrate + PyTorch CPU + Docker + `uv`.

**Idea central:** modelo local, solo CPU, una predicción se guarda y se muestra en el navegador.

---

## 2. Arquitectura y flujo end-to-end

### 2.1 Monolito por capas

```
routes (api / web)
      ↓
services (validan y orquestan)
      ↓
repositories (único acceso a la base de datos)
      ↓
models (SQLAlchemy)
```

En paralelo, los servicios usan el modelo de ML:

```
services → app/ml/predictor.py → app/ml/preprocessing.py → app/ml/artifacts/model.pt
```

Regla de oro: **las rutas no tienen lógica de negocio** y **los servicios no consultan la base de datos directamente**.

### 2.2 Arranque: `create_app()`

Archivo: `app/__init__.py:16`.

1. Carga la configuración desde `Config` (`app/config.py:34`), que lee `.env`.
2. Configura los logs (`RotatingFileHandler`, consola + archivo).
3. Exige `DATABASE_URL`; si falta, lanza `RuntimeError`.
4. Inicializa `db` y `migrate`.
5. Registra los manejadores de error y los blueprints `api_v1` y `web`.
6. Carga el modelo **una sola vez** con `Predictor.from_artifacts()` y lo guarda en `app.extensions["predictor"]` (`app/__init__.py:47-55`).
7. Si faltan los archivos del artefacto, deja `predictor = None` y la app arranca igual (las rutas del modelo responderán `503`).

### 2.3 Flujo de una predicción, paso a paso

```
Navegador
  │  POST /api/v1/predictions  (multipart/form-data: image + source)
  ▼
app/api/v1/predictions.py:13  create_prediction()
  │  - exige multipart/form-data (si no, 415)
  │  - exige el campo image y que no esté vacío (si no, 422)
  │  - source por defecto: upload
  │  - comprueba que el predictor exista (si no, 503)
  ▼
app/services/prediction_service.py:57  PredictionService.predict()
  │  - valida source: camera | upload | video
  │  - decode_image(): Pillow, formatos JPEG/PNG/WEBP
  │  - mide inference_ms
  │  - llama a predictor.predict(image)
  │  - guarda por el repositorio
  │  - loguea metadata (sin bytes de la imagen)
  ▼
app/ml/predictor.py:53  Predictor.predict()
  │  - preprocess_image(): EXIF, RGB, recorte central, 224x224, normalización ImageNet
  │  - softmax
  │  - top-3
  ▼
app/repositories/prediction_repository.py:12  create()
  │  - INSERT en predictions
  ▼
PostgreSQL
  │
  ▼
Respuesta 201 con el JSON de la predicción
```

### 2.4 Persistencia

Tablas principales:

| Tabla | Campos relevantes |
| --- | --- |
| `model_versions` | `name` único, `architecture`, `artifact_path`, `labels` JSON, `is_active`, `created_at`. |
| `predictions` | `source` (`camera`/`upload`/`video`), `original_filename`, `file_size_bytes`, `predicted_label`, `confidence` (0–1), `top3` JSON, `inference_ms`, `model_version_id`, `created_at`. |

Detalles que conviene recordar:

- La imagen **nunca** se guarda en la base de datos; solo el nombre, el tamaño y la predicción.
- `model_version_id` enlaza cada predicción con el artefacto que la produjo.
- `ModelVersion` se registra una vez por proceso en la primera predicción (`app/services/model_info_service.py:80`). El nombre incluye la fecha de modificación de `model.pt`, así un reentrenamiento crea otra versión.
- `confidence` tiene un `CHECK` en la base: entre 0 y 1.
- Las fechas se serializan en ISO 8601 UTC.

### 2.5 API REST

Prefijo `/api/v1`. Siete endpoints:

| Método | Ruta | Propósito |
| --- | --- | --- |
| `POST` | `/predictions` | Clasifica y guarda una imagen (`201`). |
| `GET` | `/predictions` | Historial paginado con filtros. |
| `GET` | `/predictions/{id}` | Detalle de una predicción. |
| `GET` | `/stats` | Totales, media de confianza y conteos. |
| `GET` | `/model` | Arquitectura, clases, preprocesamiento, entrenamiento y métricas. |
| `GET` | `/logs` | Últimas entradas del log. |
| `GET` | `/health` | Estado de app, base de datos y modelo. |

Errores siempre con el sobre:

```json
{"error": {"code": "validation_error", "message": "…", "details": {"field": "image"}}}
```

Códigos: `400`, `404`, `405`, `413`, `415`, `422`, `500`, `503`.

### 2.6 Frontend

Archivo: `app/static/js/app.js`.

- La ruta `/` solo sirve HTML; el navegador consume la API con `fetch`.
- Cámara: `getUserMedia` con `facingMode: { ideal: "environment" }`; si falla, muestra un mensaje en español y ofrece subir archivo.
- Captura: `sampleFrame()` dibuja el video en un `canvas` y devuelve un JPEG (`app.js:299`).
- Modo continuo: una predicción cada `1500 ms`; omite envíos mientras hay una petición en curso y se detiene al primer error (`app.js:324`).
- Video: hasta 8 fotogramas, enviados como imágenes con `source=video` (`app.js:455`).
- Agregación de video: confianza media por clase; si una clase no aparece en el top-3 de un fotograma, cuenta 0 en ese fotograma; se muestran las 3 medias más altas y en cuántos fotogramas ganó la clase final (`app.js:433`).
- Historial, estadísticas y logs se dibujan con Chart.js servido localmente (`app/static/vendor/chart.umd.min.js`).

### 2.7 Logs

- Formato: `<fecha y hora UTC> <NIVEL> <logger>: <mensaje>`.
- Archivo rotativo: `logs/app.log`, 1 MB por defecto, 5 respaldos.
- Nunca se registran los bytes de la imagen.
- `GET /logs?limit=` lee solo el archivo actual.

### 2.8 Docker

- Dos servicios: `db` (PostgreSQL 17.6 con healthcheck) y `app`.
- `entrypoint.sh` aplica las migraciones antes de arrancar Gunicorn.
- Gunicorn: **1 worker y 4 hilos** (el `RotatingFileHandler` y el registro diferido de la versión del modelo no son seguros con varios procesos).
- Imagen reducida a **1,72 GB**; código en `/app` de solo lectura para `appuser`; solo `/app/logs` es escribible.
- Copia selectiva: nunca el dataset ni `.env`.

---

## 3. Datos y partición (diapositivas 3–6)

### 3.1 Dataset

- **Fruits-360** de Mihai Oltean, rama **100×100**, versión `2026.10.27.0`, licencia **CC BY-SA 4.0**.
- Imágenes de 100×100 píxeles con **fondo blanco** y rotación controlada.
- **94 variedades** agrupadas en **8 frutas**.
- Se agrupa por prefijo de carpeta (`Banana `, `Apple `, etc.).
- Quedan fuera `Orange peeled 1` y `Strawberry Wedge 1` (fruta pelada o cortada).
- `Grapefruit` no entra en `uva` porque el prefijo es `Grape ` (con espacio).

| Etiqueta | Prefijo | Variedades | Train | Val | Test |
| --- | --- | ---: | ---: | ---: | ---: |
| banano | Banana | 6 | 1 200 | 300 | 719 |
| fresa | Strawberry | 3 | 1 180 | 214 | 479 |
| limon | Lemon | 2 | 783 | 159 | 330 |
| manzana | Apple | 30 | 1 200 | 300 | 5 506 |
| naranja | Orange | 5 | 1 200 | 300 | 1 180 |
| pera | Pear | 20 | 1 200 | 300 | 4 164 |
| tomate | Tomato | 19 | 1 200 | 300 | 3 413 |
| uva | Grape | 9 | 1 200 | 300 | 1 696 |
| **Total** | | **94** | **9 163** | **2 173** | **17 487** |

Nota: en el código y en la API la etiqueta es `limon` (sin tilde); en algunas diapositivas aparece «limón».

### 3.2 Riesgo de fuga de datos

Las imágenes de Fruits-360 son **fotogramas de videos cortos**. Los nombres siguen el patrón:

- `N_100.jpg` → toma con índice `N`.
- `r_N_100.jpg` → la misma toma girada.
- `r2_N_100.jpg` → otra rotación de la misma toma.

Si se mezclan al azar, el modelo podría ver casi la misma imagen en entrenamiento y en validación. Eso **inflaría** las métricas: la validación dejaría de medir generalización.

### 3.3 Regla de partición

En cada variedad de `Training/`:

1. Se extraen los índices únicos `N`.
2. Se ordenan y el **último 15 %** (redondeado hacia arriba) forma la validación.
3. Entrenamiento conserva solo `N < min(val) - 10`; se descartan 10 índices como hueco de seguridad.
4. Todas las variantes del mismo `N` viajan juntas.
5. `Test/` se reserva solo para la prueba oficial; no se usa para entrenar ni para ajustar pesos.

Implementación: `ml_training/prepare_subset.py:81` (`split_indices`) y `build_manifest` en `ml_training/prepare_subset.py:153`.

### 3.4 Preprocesamiento

Módulo único compartido por entrenamiento e inferencia: `app/ml/preprocessing.py`.

| Paso | Detalle |
| --- | --- |
| Orientación | `ImageOps.exif_transpose`. |
| Color | Conversión a RGB. |
| Recorte | Cuadrado centrado (no deforma fotos rectangulares). |
| Tamaño | 224×224 con interpolación bilineal. |
| Normalización | Media ImageNet `(0.485, 0.456, 0.406)` y desviación `(0.229, 0.224, 0.225)`. |

Entrenamiento añade aumentación:

- `RandomResizedCrop(224, scale=(0.8, 1.0), ratio=(0.9, 1.1))`.
- Volteo horizontal.
- Rotación de hasta 20°.
- `ColorJitter` leve (brillo, contraste, saturación 0.2; tono 0.02).

Validación, prueba e inferencia usan la transformación determinista. **La misma función** se usa en entrenamiento y en producción; eso evita diferencias silenciosas.

---

## 4. Diapositivas 8 a 13: núcleo de la presentación

Estas seis diapositivas son el corazón técnico. Se dividen en dos bloques:

- **02 · El modelo:** diapositivas 8 (Modelo) y 9 (Selección del artefacto).
- **03 · Resultados:** diapositivas 10 (Resultado oficial), 11 (Métricas por clase), 12 (Confusiones) y 13 (Prueba real).

---

### Diapositiva 8 — MobileNetV3-Small en dos etapas

**Lo que dice la diapositiva**

- MobileNetV3-Small con pesos preentrenados de ImageNet.
- La última capa se sustituye por 8 salidas.
- Etapa 01 (épocas 1–3): solo la cabeza, resto congelado, LR 0,001.
- Etapa 02 (épocas 4–8): últimos 4 bloques, LR 0,0001.
- Semilla 42, lotes de 64, `WeightedRandomSampler`, 63–143 s por época en CPU.

**Explicación**

Es **transfer learning** en dos etapas:

1. **Cabeza (`head`).** El backbone de MobileNetV3-Small conserva sus pesos de ImageNet y solo se entrena el clasificador final. Así la cabeza aprende a mapear características ya útiles a las 8 frutas sin destruir el backbone.
2. **Ajuste fino (`finetune`).** Se descongelan los **últimos 4 bloques** de `features` y el clasificador. Con una tasa de aprendizaje menor (0,0001) se adaptan las características de alto nivel sin desestabilizar el resto.

Detalles importantes del código (`ml_training/train.py`):

- `build_model()` reemplaza `classifier[-1]` por `Linear(in_features, 8)` (`app/ml/model_factory.py:17-18`).
- `configure_stage()` congela todo `features` y descongela la cabeza; en finetune descongela `features[-4:]` (`train.py:63`).
- `set_train_mode()` deja en **eval** los bloques congelados para que sus estadísticas de **BatchNorm** no cambien (`train.py:76`). Esto es clave: si se dejaran en modo entrenamiento, las medias y varianzas se actualizarían y se perdería parte del conocimiento preentrenado.
- `balanced_sampler()` usa peso `1 / frecuencia de la clase`, con reemplazo (`train.py:55`).
- Optimizador **AdamW** y pérdida **entropía cruzada**.
- Lote 64 en entrenamiento y 128 en validación.
- No se usa `shuffle`: el sampler ya decide el orden.

**Datos exactos**

| Elemento | Valor |
| --- | --- |
| Arquitectura | `mobilenet_v3_small` |
| Pesos | `IMAGENET1K_V1` |
| Clases | 8 |
| Etapa 1 | épocas 1–3, LR 0,001, solo cabeza |
| Etapa 2 | épocas 4–8, LR 0,0001, últimos 4 bloques + cabeza |
| Optimizador | AdamW |
| Pérdida | CrossEntropyLoss |
| Lote | 64 train / 128 val |
| Semilla | 42 |
| Muestreo | `WeightedRandomSampler` con reemplazo |
| Tiempo por época | 63,2 s a 142,7 s (CPU) |

**Por qué importa**

- Explica por qué un modelo pequeño puede rendir muy bien en un problema acotado: no aprende desde cero, reutiliza características de ImageNet.
- El ajuste fino en dos etapas es una decisión de compromiso: más rendimiento que solo la cabeza, menos riesgo que reentrenar todo.
- Mantener BatchNorm congelado en eval evita degradar el modelo al descongelar.

**Pregunta probable del jurado**

> «¿Por qué no entrenaron todo el modelo desde el principio?»

**Respuesta corta**

> Porque con pocos datos y CPU conviene preservar las características de ImageNet. Primero se adapta la cabeza con el backbone congelado; después se ajustan solo los últimos bloques con un LR menor. Entrenar todo desde el inicio arriesga sobreajuste, destruye estadísticas de BatchNorm y es más costoso.

---

### Diapositiva 9 — Elegir el artefacto no fue trivial

**Lo que dice la diapositiva**

- Primer criterio: exactitud. Eligió la **época 3** (solo cabeza), con exactitud de validación **0,9986** y **0,9915** en la prueba oficial.
- Criterio final: menor pérdida. Eligió la **época 5** (ajuste fino), con pérdida **0,0096**, exactitud de validación **0,9963** y **0,9938** en la prueba oficial.
- El primer resultado influyó en el cambio de criterio; haría falta un conjunto de prueba independiente para estimar la mejora con seguridad.

**Explicación**

- Con exactitud de validación saturada (0,994–0,999), muchas épocas empatan o casi empatan. La exactitud es una métrica **gruesa**: un cambio pequeño en los datos puede cambiar el ganador.
- La **pérdida** es una señal más fina: mide qué tan seguras y bien ordenadas son las probabilidades, no solo cuántas aciertan.
- Por eso el criterio final es: **menor pérdida de validación**, con **mayor exactitud como desempate**. En código: `(val_loss, -val_acc) < (best["val_loss"], -best["val_accuracy"])` (`train.py:148`).
- El artefacto se guarda cada vez que una época mejora el criterio (`save_artifacts`).

**Historia real (y honesta)**

1. La primera corrida eligió la época 3 por mayor exactitud de validación (0,9986). Ese artefacto solo había entrenado la cabeza.
2. En `Test/` obtuvo **0,9915**.
3. Al ver ese resultado se cambió el criterio a menor pérdida de validación.
4. Se repitió el entrenamiento con la misma semilla y se reprodujeron las métricas por época.
5. El nuevo criterio eligió la **época 5**, ya en ajuste fino, con pérdida 0,0096 y exactitud de validación 0,9963.
6. El artefacto final obtuvo **0,9938** en `Test/`.

**Datos exactos de las 8 épocas**

| Época | Etapa | LR | Pérdida train | Exactitud train | Pérdida val | Exactitud val | Segundos |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | head | 0,001 | 0,2229 | 0,9338 | 0,0532 | 0,9844 | 63,2 |
| 2 | head | 0,001 | 0,0496 | 0,9859 | 0,0420 | 0,9871 | 84,5 |
| 3 | head | 0,001 | 0,0286 | 0,9920 | 0,0140 | **0,9986** | 77,7 |
| 4 | finetune | 0,0001 | 0,2231 | 0,9476 | 0,0152 | 0,9931 | 110,4 |
| **5** | **finetune** | **0,0001** | **0,0194** | **0,9955** | **0,0096** | **0,9963** | **114,4** |
| 6 | finetune | 0,0001 | 0,0141 | 0,9971 | 0,0098 | 0,9977 | 134,0 |
| 7 | finetune | 0,0001 | 0,0091 | 0,9978 | 0,0105 | 0,9945 | 142,7 |
| 8 | finetune | 0,0001 | 0,0069 | 0,9983 | 0,0098 | 0,9959 | 128,6 |

Observaciones que conviene saber explicar:

- **Época 4:** la pérdida de entrenamiento sube de 0,0286 a 0,2231. No es un error: al descongelar los últimos bloques, sus capas BatchNorm vuelven a actualizar estadísticas en modo entrenamiento. En la época 5 la pérdida baja a 0,0194.
- **Época 6:** tiene mayor exactitud de validación (0,9977) que la 5, pero **mayor pérdida** (0,0098 > 0,0096). Con el criterio final gana la 5.
- **Época 8:** la pérdida de entrenamiento baja, pero la de validación no mejora; señal de que el ajuste adicional no aporta.

**Por qué importa**

- Es una lección de metodología: elegir el artefacto por exactitud cuando está saturada es frágil.
- También es una lección de honestidad: el cambio de criterio se hizo **después de ver `Test/`**. Eso introduce un sesgo de selección. La afirmación defendible es «el artefacto final obtiene 0,9938 en la prueba oficial», no «mejoramos el modelo en 0,23 puntos de forma demostrada».

**Pregunta probable del jurado**

> «Si `Test/` no se usó para entrenar, ¿por qué dicen que el cambio de criterio es un problema?»

**Respuesta corta**

> Porque `Test/` sí se usó para **decidir** entre dos artefactos. Aunque los pesos no se ajustaron con `Test/`, la elección del criterio se hizo tras observar su resultado. Para estimar la mejora con seguridad haría falta un conjunto de prueba independiente que no haya intervenido en ninguna decisión.

---

### Diapositiva 10 — 99,38 % en la prueba oficial

**Lo que dice la diapositiva**

- Exactitud **99,38 %** sobre **17 487 imágenes** de `Test/`.
- Promedio macro: precisión **0,995**, recall **0,997**, F1 **0,996**.
- `Test/` quedó fuera del entrenamiento y de la elección de hiperparámetros.

**Explicación**

- **Exactitud (accuracy):** proporción de imágenes clasificadas correctamente.
  `accuracy = aciertos / total = 17 378 / 17 487 = 0,99377`.
- **Precisión:** de las veces que el modelo dijo «clase X», cuántas eran realmente X.
  `precisión = TP / (TP + FP)`.
- **Recall (sensibilidad):** de las imágenes que eran X, cuántas detectó.
  `recall = TP / (TP + FN)`.
- **F1:** media armónica de precisión y recall; castiga que una de las dos sea baja.
- **Promedio macro:** se calcula la métrica por clase y se promedian **sin ponderar por número de imágenes**. Así una clase pequeña (limón, 330) pesa lo mismo que una grande (manzana, 5 506).

**Datos exactos**

| Métrica | Valor |
| --- | ---: |
| Imágenes evaluadas | 17 487 |
| Aciertos | 17 378 |
| Errores | 109 |
| Exactitud | 0,9937668 (99,38 %) |
| Precisión macro | 0,9952326 |
| Recall macro | 0,9970461 |
| F1 macro | 0,9961240 |

**Por qué importa**

- Es el resultado principal del proyecto.
- El promedio macro es más justo que la exactitud sola cuando hay desbalance (manzana tiene 5 506 imágenes y limón 330).
- `Test/` no se usó para ajustar pesos, pero **sí** para cambiar el criterio de selección (ver diapositiva 9). Hay que decirlo así de claro.

**Pregunta probable del jurado**

> «¿Por qué reportan macro y no solo accuracy?»

**Respuesta corta**

> Porque las clases están desbalanceadas. La exactitud está dominada por manzana, pera y tomate, que suman la mayoría de `Test/`. El promedio macro da el mismo peso a cada fruta y revela mejor si alguna clase pequeña falla.

---

### Diapositiva 11 — Métricas por clase

**Lo que dice la diapositiva**

Tabla de precisión, recall, F1 e imágenes por clase:

| Clase | Precisión | Recall | F1 | Imágenes |
| --- | ---: | ---: | ---: | ---: |
| banano | 1,000 | 1,000 | 1,000 | 719 |
| fresa | 1,000 | 1,000 | 1,000 | 479 |
| limón | 1,000 | 1,000 | 1,000 | 330 |
| manzana | 0,991 | 0,991 | 0,991 | 5 506 |
| naranja | 0,995 | 1,000 | 0,997 | 1 180 |
| pera | 0,997 | 0,987 | 0,992 | 4 164 |
| tomate | 0,997 | 0,999 | 0,998 | 3 413 |
| uva | 0,981 | 1,000 | 0,991 | 1 696 |

**Explicación**

- **Banano, fresa y limón:** perfectos en esta prueba. Son clases visualmente muy distintas y con menos variedades.
- **Manzana:** la clase más grande y con 30 variedades. Precisión y recall de 0,991: falla poco, pero concentra la mayoría de los errores absolutos por volumen.
- **Pera:** precisión alta (0,997) pero recall más bajo (0,987). Traducción: cuando dice «pera», casi siempre acierta; pero **se le escapan peras** que clasifica como otra fruta (sobre todo manzana).
- **Uva:** precisión 0,981, la más baja. Traducción: algunas imágenes que no son uva se clasifican como uva. Su recall es 1,000: no se le escapa ninguna uva.
- **Naranja y tomate:** casi perfectos.

**Cómo leer precisión vs recall**

| Métrica | Pregunta que responde | Baja cuando… |
| --- | --- | --- |
| Precisión | «Cuando predice X, ¿acierta?» | predice X en cosas que no son X (falsos positivos). |
| Recall | «De todas las X, ¿cuántas encuentra?» | deja pasar X como otra clase (falsos negativos). |
| F1 | «Equilibrio entre las dos» | cualquiera de las dos es baja. |

**Por qué importa**

- El promedio alto no borra los casos débiles: la diapositiva 12 muestra exactamente dónde falla.
- Permite explicar que «99,38 %» no significa «perfecto en todas las clases».

**Pregunta probable del jurado**

> «¿Por qué uva tiene la precisión más baja si su F1 es 0,991?»

**Respuesta corta**

> Porque su recall es perfecto (1,000) y su precisión es 0,981: no deja escapar uvas, pero algunas imágenes de otras frutas, sobre todo manzanas, terminan clasificadas como uva. El F1 queda alto porque compensa con el recall.

---

### Diapositiva 12 — Donde aparece la confusión

**Lo que dice la diapositiva**

- 51 peras clasificadas como manzanas.
- 27 manzanas clasificadas como uvas.
- 9 manzanas clasificadas como tomates.
- 5 tomates clasificados como uvas.
- Variedades más débiles: **Pear Red 1 (0,811)** y **Apple 6 (0,879)**.

**Matriz de confusión completa**

Filas = clase real; columnas = predicción. Orden:
`banano, fresa, limon, manzana, naranja, pera, tomate, uva`.

| Real \ Pred | banano | fresa | limon | manzana | naranja | pera | tomate | uva |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| banano | **719** | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| fresa | 0 | **479** | 0 | 0 | 0 | 0 | 0 | 0 |
| limon | 0 | 0 | **330** | 0 | 0 | 0 | 0 | 0 |
| manzana | 0 | 0 | 0 | **5 458** | 1 | 11 | 9 | 27 |
| naranja | 0 | 0 | 0 | 0 | **1 180** | 0 | 0 | 0 |
| pera | 0 | 0 | 0 | 51 | 5 | **4 108** | 0 | 0 |
| tomate | 0 | 0 | 0 | 0 | 0 | 0 | **3 408** | 5 |
| uva | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **1 696** |

**Desglose de los 109 errores**

| Error | Cantidad |
| --- | ---: |
| pera → manzana | 51 |
| manzana → uva | 27 |
| manzana → pera | 11 |
| manzana → tomate | 9 |
| pera → naranja | 5 |
| tomate → uva | 5 |
| manzana → naranja | 1 |
| **Total** | **109** |

**Explicación**

- La confusión dominante es **pera → manzana** (51). Tiene sentido: formas y colores similares; además la manzana tiene 30 variedades y mucha presencia.
- **Manzana** concentra errores hacia uva (27), pera (11) y tomate (9). Es la clase con más variedades y más imágenes; también la más difícil de separar internamente.
- **Uva** no pierde recall (no hay uvas mal clasificadas), pero atrae falsos positivos de manzana y tomate.
- **Pear Red 1** (0,811 sobre 222 imágenes) y **Apple 6** (0,879 sobre 157) son las variedades más débiles. El promedio por fruta las oculta; el análisis por variedad las revela.

**Otras variedades débiles (reporte)**

| Variedad | Exactitud | Imágenes |
| --- | ---: | ---: |
| Pear Red 1 | 0,811 | 222 |
| Apple 6 | 0,879 | 157 |
| Tomato Cherry Yellow 1 | 0,950 | 100 |
| Apple 9 | 0,952 | 231 |
| Pear 1 | 0,957 | 164 |

**Por qué importa**

- Demuestra que el modelo no es «perfecto»: tiene un patrón de error coherente.
- Permite proponer mejoras concretas: más datos de Pear Red 1 y Apple 6, o un ajuste específico para pera/manzana.

**Pregunta probable del jurado**

> «¿Cuál es el error más frecuente y por qué?»

**Respuesta corta**

> Pera clasificada como manzana, 51 casos. Son frutas con forma y color parecidos, y la manzana aporta 30 variedades y más de 5 500 imágenes de prueba. Además, la variedad Pear Red 1 baja a 0,811, así que el error se concentra en casos concretos.

---

### Diapositiva 13 — Cambio de dominio

**Lo que dice la diapositiva**

- Prueba oficial: 99,38 %, con fondo blanco, rotación controlada y recorte limpio.
- Prueba real: **pendiente**; fondos, luz y encuadres distintos cambian el problema.
- El plan prevé unas 10 fotos propias por clase en `data/real_test/<clase>/`.
- El evaluador ya funciona sin esa carpeta y reporta «pendiente».

**Explicación**

- **Cambio de dominio (domain shift):** el modelo se entrenó con imágenes de Fruits-360 (fondo blanco, encuadre controlado). Una foto real tiene fondo, iluminación, sombras, perspectiva y encuadre distintos. El 99,38 % **no** garantiza buen rendimiento en fotos reales.
- Por eso el proyecto reporta **dos pruebas separadas**:
  1. **Prueba oficial:** `Test/` de Fruits-360.
  2. **Prueba real:** fotos propias en `data/real_test/<clase>/`.
- El evaluador (`ml_training/evaluate.py:130`) devuelve:
  - `pendiente`: no hay fotos.
  - `incompleta`: hay fotos, pero falta alguna clase; incluye `missing_classes`.
  - `ok`: hay fotos de las 8 clases.
- La interfaz muestra «Pendiente» si el estado es `pendiente` o no hay exactitud; si es `incompleta`, muestra la exactitud seguida de «(faltan clases)»; si es `ok`, solo la exactitud.

**Qué falta exactamente**

1. Tomar unas 10 fotos por clase (8 clases).
2. Variar fondo, iluminación y encuadre; incluir la fruta entera y centrada.
3. Redimensionar a unos 1024 px en el lado más largo.
4. Guardar en JPG, JPEG, PNG, WebP o BMP (convertir HEIC).
5. Poner cada foto en `data/real_test/<clase>/`, con el nombre exacto de la clase.
6. Ejecutar `uv run python ml_training/evaluate.py`.
7. Actualizar `metrics.json`, `summary.md`, el informe y las diapositivas.

**Por qué importa**

- Es la limitación más importante del proyecto y la conclusión más honesta.
- El jurado probablemente pregunte por generalización; hay que responder que **está pendiente de medir**, no afirmar que el modelo funciona en fotos reales.

**Pregunta probable del jurado**

> «¿El modelo sirve para fotos tomadas con un celular?»

**Respuesta corta**

> No lo sabemos todavía con datos. El 99,38 % corresponde al entorno controlado de Fruits-360. La prueba con fotos propias está implementada pero pendiente porque `data/real_test/<clase>/` está vacía. Hasta medirla, no podemos afirmar que generalice a fotos reales.

---

## 5. Resumen de las diapositivas 8–13 en una tabla

| # | Título | Idea que debes poder decir | Dato ancla |
| --- | --- | --- | --- |
| 8 | Modelo | MobileNetV3-Small con transfer learning en dos etapas | Épocas 1–3 cabeza (LR 0,001); 4–8 últimos 4 bloques (LR 0,0001) |
| 9 | Selección del artefacto | Se cambió de exactitud a menor pérdida | Época 3: val 0,9986 → test 0,9915; época 5: loss 0,0096 → test 0,9938 |
| 10 | Resultado oficial | 99,38 % en 17 487 imágenes | Macro P 0,995 / R 0,997 / F1 0,996 |
| 11 | Métricas por clase | El promedio alto esconde diferencias | Uva precisión 0,981; pera recall 0,987 |
| 12 | Confusiones | El error se concentra en pera/manzana | 51 pera→manzana; 109 errores totales |
| 13 | Prueba real | El 99,38 % no prueba generalización | Prueba real pendiente en `data/real_test/<clase>/` |

---

## 6. Las otras diapositivas (para contexto)

| # | Tema | Resumen |
| --- | --- | --- |
| 1 | Portada | Prueba oficial 99,38 %, 17 487 imágenes, prueba real pendiente. |
| 2 | Idea central | Una fruta entra, una etiqueta sale; modelo local, CPU, PostgreSQL. |
| 3 | Dataset | Fruits-360 100×100, Mihai Oltean, CC BY-SA 4.0, 94 variedades en 8 frutas. |
| 4 | Clases | Las 8 frutas con su número de variedades. |
| 5 | Riesgo de fuga | `N`, `r_N`, `r2_N` son la misma toma; mezclar infla la validación. |
| 6 | Partición | Último 15 % a validación, hueco de 10, Test reservado. |
| 7 | Preprocesamiento | EXIF, RGB, recorte central, 224×224, normalización ImageNet. |
| 14 | Arquitectura | Rutas → servicios → repositorios → modelos; predictor cargado una vez. |
| 15 | Flujo | Bytes → Pillow → preprocesamiento → modelo → repositorio/log → 201. |
| 16 | Persistencia | Etiqueta, confianza, top-3, source, nombre/tamaño, ms, fecha UTC, versión. |
| 17 | API | Siete endpoints bajo `/api/v1` y sobre de error. |
| 18 | Interfaz | Cámara, archivo, video, modo continuo, historial, Chart.js. |
| 19 | Docker | PostgreSQL 17.6 + app, migraciones al arrancar, 1,72 GB, 1 worker/4 hilos. |
| 20 | Conclusiones | Funciona en entorno controlado; la partición evitó una validación engañosa; falta medir fotos reales. |

---

## 7. Mapa de código

| Concepto | Archivo:línea |
| --- | --- |
| Fábrica de la app y carga del modelo | `app/__init__.py:16` y `app/__init__.py:47` |
| Configuración desde `.env` | `app/config.py:34` |
| Construcción de MobileNetV3-Small | `app/ml/model_factory.py:9` |
| Carga del artefacto | `app/ml/predictor.py:31` |
| Predicción y top-3 | `app/ml/predictor.py:53` |
| Preprocesamiento compartido | `app/ml/preprocessing.py:32`, `:47`, `:59`, `:77` |
| Servicio de predicción | `app/services/prediction_service.py:57` |
| Decodificación con Pillow | `app/services/prediction_service.py:24` |
| Repositorio: crear, listar, stats | `app/repositories/prediction_repository.py:12`, `:46`, `:71` |
| Ruta POST de predicción | `app/api/v1/predictions.py:13` |
| Versión activa del modelo | `app/services/model_info_service.py:80` |
| Modelo `Prediction` | `app/models/prediction.py:11` |
| Modelo `ModelVersion` | `app/models/model_version.py:26` |
| Partición por índice | `ml_training/prepare_subset.py:81` |
| Manifiesto | `ml_training/prepare_subset.py:153` |
| Sampler balanceado | `ml_training/train.py:55` |
| Congelar/descongelar etapas | `ml_training/train.py:63` |
| BatchNorm congelado en eval | `ml_training/train.py:76` |
| Selección del mejor artefacto | `ml_training/train.py:148` |
| Métricas oficiales | `ml_training/evaluate.py:119` |
| Prueba real (pendiente/incompleta/ok) | `ml_training/evaluate.py:130` |
| `sampleFrame()` cámara/video | `app/static/js/app.js:299` |
| Modo continuo | `app/static/js/app.js:324` |
| Agregación de video | `app/static/js/app.js:433` |
| Análisis de video | `app/static/js/app.js:455` |
| Ruta web `/` | `app/web/routes.py:8` |

---

## 8. Glosario

| Término | Definición breve |
| --- | --- |
| **Transfer learning** | Reutilizar un modelo entrenado en otro problema (ImageNet) y adaptarlo al propio. |
| **Fine-tuning** | Descongelar parte del modelo preentrenado y entrenarla con una tasa de aprendizaje baja. |
| **Backbone** | Parte del modelo que extrae características; en MobileNetV3, `features`. |
| **Cabeza (head)** | Clasificador final; en este proyecto, una capa lineal de 8 salidas. |
| **BatchNorm** | Normaliza activaciones usando medias/varianzas; en modo eval usa estadísticas fijas. |
| **Softmax** | Convierte logits en probabilidades que suman 1. |
| **Entropía cruzada** | Pérdida que castiga asignar poca probabilidad a la clase correcta. |
| **AdamW** | Optimizador con momento y decaimiento de peso desacoplado. |
| **WeightedRandomSampler** | Muestreador que da más peso a las clases poco frecuentes. |
| **Accuracy** | Proporción de aciertos. |
| **Precisión** | De lo que predijo como X, cuánto era X. |
| **Recall** | De todo lo que era X, cuánto encontró. |
| **F1** | Media armónica de precisión y recall. |
| **Macro** | Promedio sin ponderar por el tamaño de cada clase. |
| **Matriz de confusión** | Tabla real vs predicho; muestra dónde se confunde el modelo. |
| **Fuga de datos (leakage)** | Información de validación/prueba que se filtra al entrenamiento y infla las métricas. |
| **Cambio de dominio** | Diferencia entre los datos de entrenamiento y los de uso real. |
| **Soporte** | Número de imágenes reales de una clase en el conjunto evaluado. |
| **Artefacto** | Archivos del modelo entrenado: `model.pt`, `labels.json`, `preprocessing.json`. |
| **Latencia de inferencia** | Tiempo que tarda el modelo en predecir una imagen (`inference_ms`). |

---

## 9. Autoevaluación

### 9.1 Preguntas rápidas

1. ¿Cuántas clases tiene el modelo y cuántas variedades agrupa?
2. ¿Qué contiene `app/ml/artifacts/`?
3. ¿Dónde y cuándo se carga el modelo?
4. ¿Qué formatos de imagen acepta la API?
5. ¿Qué códigos HTTP usa para archivo corrupto, formato no soportado y archivo demasiado grande?
6. ¿Qué valores puede tomar `source`?
7. ¿Qué se guarda en `predictions` y qué **no** se guarda?
8. ¿Por qué se usa un hueco de 10 índices en la partición?
9. ¿Qué etapas tiene el entrenamiento y qué se entrena en cada una?
10. ¿Por qué las capas congeladas se dejan en modo eval?
11. ¿Cuál fue el criterio final de selección del artefacto?
12. ¿Qué época se eligió y con qué métricas?
13. ¿Cuál es la exactitud oficial y sobre cuántas imágenes?
14. ¿Cuál es la confusión más frecuente?
15. ¿Por qué la prueba real está pendiente?
16. ¿Qué diferencia hay entre `precisión` y `recall`?
17. ¿Qué significa `macro` y por qué se reporta?
18. ¿Qué pasa si falta el artefacto del modelo al arrancar?
19. ¿Por qué Gunicorn usa un solo worker?
20. ¿Por qué el 99,38 % no demuestra generalización?

### 9.2 Respuestas

1. 8 clases; 94 variedades.
2. `model.pt` (pesos), `labels.json` (orden de clases) y `preprocessing.json` (metadatos).
3. En `create_app()`, una sola vez al arrancar; se guarda en `app.extensions["predictor"]`.
4. JPEG, PNG y WEBP; se valida decodificando con Pillow, no por extensión ni `Content-Type`.
5. `422` (corrupto), `415` (formato no soportado), `413` (demasiado grande).
6. `camera`, `upload`, `video`.
7. Etiqueta, confianza, top-3, fuente, nombre y tamaño del archivo, `inference_ms`, fecha UTC y `model_version_id`. No se guardan los bytes de la imagen.
8. Para separar los bloques de entrenamiento y validación y evitar que fotogramas casi idénticos queden en ambos lados.
9. Etapa 1: solo la cabeza (backbone congelado, LR 0,001). Etapa 2: últimos 4 bloques + cabeza (LR 0,0001).
10. Para que sus estadísticas de BatchNorm no se actualicen y se conserve el conocimiento preentrenado.
11. Menor pérdida de validación, con mayor exactitud como desempate.
12. Época 5 (finetune): pérdida 0,0096, exactitud de validación 0,9963; prueba oficial 0,9938.
13. 99,38 % (0,9938) sobre 17 487 imágenes.
14. Pera clasificada como manzana: 51 casos.
15. Porque `data/real_test/<clase>/` está vacía; el evaluador reporta `pendiente`.
16. Precisión mide aciertos cuando predice una clase; recall mide cuántos casos reales de esa clase encuentra.
17. Promedio sin ponderar por tamaño de clase; evita que las clases grandes dominen la métrica.
18. Registra una advertencia, deja `predictor = None` y la app arranca; `/model` y `/predictions` responden `503`.
19. Porque `RotatingFileHandler` y el registro diferido de la versión del modelo no son seguros entre varios procesos.
20. Porque el 99,38 % se midió en el entorno controlado de Fruits-360; falta la prueba con fotos propias.

### 9.3 Preguntas de defensa (con respuesta modelo)

**«¿Por qué MobileNetV3-Small y no un modelo más grande?»**

> Porque el problema es acotado (8 clases), el entorno es CPU y el objetivo es un proyecto académico simple. MobileNetV3-Small ofrece buena relación precisión/coste computacional y pesa solo 6,2 MB. Un modelo más grande no aportaría una mejora clara en este dataset y complicaría el despliegue.

**«¿Por qué dos etapas y no una sola?»**

> Porque primero conviene adaptar la cabeza sin destruir las características de ImageNet; después se ajustan los últimos bloques con un LR menor. Es un compromiso entre rendimiento y riesgo de sobreajuste.

**«¿Cómo evitaron que la validación fuera engañosa?»**

> Agrupando todos los fotogramas del mismo índice `N` (incluidas las rotaciones `r` y `r2`) y separando entrenamiento y validación con un hueco de 10 índices. Así no hay imágenes casi idénticas en ambos lados.

**«¿Por qué cambiaron el criterio de selección?»**

> Porque la exactitud de validación estaba saturada y elegía una época de solo cabeza que rindió peor en `Test/` (0,9915). La pérdida es más fina para desempatar épocas con exactitud similar. El nuevo criterio eligió la época 5, con 0,9938 en `Test/`. Reconocemos que el cambio se hizo tras ver `Test/`, así que no podemos afirmar una mejora demostrada sin un conjunto independiente.

**«¿Cuál es el error más frecuente y qué harían para mejorarlo?»**

> Pera → manzana, 51 casos; también manzana → uva (27) y manzana → tomate (9). Recolectaría más imágenes de las variedades débiles (Pear Red 1, Apple 6) y probaría un ajuste específico o más aumentación para pera/manzana.

**«¿El modelo funciona con fotos reales?»**

> No lo sabemos todavía con datos. La prueba real está implementada pero pendiente porque no hay fotos en `data/real_test/<clase>/`. El 99,38 % corresponde a Fruits-360. Hasta medir fotos propias, no afirmamos generalización.

**«¿Qué pasa si la base de datos se cae?»**

> `GET /health` devuelve `503` con `{"status": "degraded", "database": "error", "model": "loaded"}`. Las predicciones dependen de la base para guardar, así que fallarían; los logs se escriben a archivo y consola, no a la base.

**«¿Por qué no se guarda la imagen en la base?»**

> Porque el objetivo es trazabilidad de la predicción, no almacenar datos personales ni binarios grandes. Se guardan metadatos (nombre, tamaño, etiqueta, confianza, top-3, tiempo y versión). Además, el enunciado pide no registrar bytes de imágenes.

---

## 10. Trampas y confusiones frecuentes

1. **«El modelo tiene 94 clases».** No: tiene **8 salidas**; 94 son las variedades agrupadas.
2. **«La prueba oficial fue del 100 %».** No: 99,38 %, con 109 errores.
3. **«El artefacto se eligió por exactitud».** El criterio **final** fue menor pérdida; la exactitud solo desempata.
4. **«La época 6 es la mejor porque tiene más exactitud de validación».** No con el criterio final: su pérdida (0,0098) es mayor que la de la época 5 (0,0096).
5. **«El salto de pérdida en la época 4 es un bug».** No: es el efecto de descongelar bloques y actualizar BatchNorm.
6. **«Test/ no se usó, así que no hay ningún sesgo».** Los pesos no se ajustaron con `Test/`, pero el criterio de selección se cambió después de verlo.
7. **«El 99,38 % demuestra que funciona en fotos reales».** No: mide el entorno controlado de Fruits-360.
8. **«La etiqueta es `limón`».** En código y API es `limon`, sin tilde.
9. **«La confusión principal es manzana → pera».** La principal es **pera → manzana** (51).
10. **«Macro y accuracy son lo mismo».** No: macro promedia por clase sin ponderar; accuracy pondera por número de imágenes.
11. **«El modelo se carga por cada petición».** No: se carga una vez en `create_app()`.
12. **«El video se procesa en el backend».** No: el navegador muestrea hasta 8 fotogramas y los envía como imágenes con `source=video`.

---

## 11. Rutina de repaso recomendada

1. **Día 1:** secciones 1–3. Dibuja de memoria el flujo `navegador → API → servicio → modelo → repositorio → PostgreSQL`.
2. **Día 2:** diapositivas 8 y 9. Explica en voz alta las dos etapas y la historia del cambio de criterio.
3. **Día 3:** diapositivas 10–12. Copia la tabla de métricas y la matriz de confusión; explica los 109 errores.
4. **Día 4:** diapositiva 13 y conclusiones. Practica la respuesta honesta sobre generalización.
5. **Día 5:** autoevaluación completa y preguntas de defensa. Si fallas una, vuelve a la sección correspondiente.

---

## 12. Cierre en una frase

> La app demuestra un pipeline completo —datos, transfer learning, API, PostgreSQL, interfaz y Docker— con un resultado excelente en el entorno controlado de Fruits-360; su principal límite, dicho con honestidad, es que la generalización a fotos reales aún no se ha medido.
