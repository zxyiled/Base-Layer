# Guía de estudio para la presentación

Guía personal para la exposición del clasificador de frutas. Tu parte son las **diapositivas 14 a 20** (arquitectura, flujo, persistencia, API, interfaz, Docker y conclusiones), que están en detalle en la sección 2. La sección 3 repasa las diapositivas 1 a 13 por si te preguntan por ellas. Las cifras vienen del código y de los reportes de `origin/ML-project` (commit `154ce03`, PR #17).

---

## 0. Antes de presentar (revísalo hoy)

1. **Tu copia local está atrasada.** La rama local `ML-project` está en `f6b3997` (PR #14), pero el remoto ya tiene los PR #15, #16 y #17. Esa copia no tiene la interfaz web (`app/web/`), el `LICENSE` ni los arreglos de la auditoría. Haz `git pull` de `ML-project` desde el IDE antes de la demo.
2. **`main` todavía no tiene el proyecto.** Es la rama predeterminada del repositorio y la que se entrega. Fusiona `ML-project` en `main`. Habrá dos conflictos:
   - `.gitignore`: usa la versión de `ML-project` y añade lo que solo tenga `main`.
   - `LICENSE`: conserva el de `ML-project`.
3. **Las diapositivas están en `docs/presentation/index.html`.** Se movieron desde `docs/presentacion/`, y los enlaces del README y los docs ya apuntan a la nueva ruta.
4. **La diapositiva 18 quedó desactualizada en un punto.** El punto 04 dice «votación mayoritaria y confianza media». Desde la auditoría, el resumen del video ordena las clases por **confianza media sobre todos los fotogramas** y además informa en cuántos fotogramas ganó la clase final. Dilo así al exponer o corrige el texto.
5. **La prueba real ya tiene resultado: 53,7 % (29 de 54), en estado `incompleta`.** Las imágenes son de internet, no fotos propias, y faltan pera y uva. Está en las diapositivas 1, 13 y 20; prepara la respuesta de la sección 4.

### Comandos para la demo

```sh
cp .env.example .env              # si no existe
docker compose up -d --build      # app en http://localhost:8000
curl localhost:8000/api/v1/health # {"database":"ok","model":"loaded","status":"ok"}
docker compose logs -f app        # ver migraciones y peticiones
docker compose down               # al terminar (-v borra la base)
```

Sin Docker: `uv sync`, define `DATABASE_URL`, corre `uv run flask --app wsgi db upgrade` y luego `uv run flask --app wsgi run --debug`. La app queda en `http://127.0.0.1:5000`.

La cámara solo funciona en `localhost` o con HTTPS. Si usas la IP de la red, el navegador la bloquea.

---

## 1. El proyecto en 30 segundos

Una aplicación Flask clasifica una imagen en **8 frutas**: banano, fresa, limón, manzana, naranja, pera, tomate y uva. El modelo es **MobileNetV3-Small** ajustado por transfer learning sobre **Fruits-360** (100 × 100 px). La imagen llega por cámara, por archivo o como fotograma de un video. Cada predicción se guarda en **PostgreSQL** y se consulta en una interfaz web con historial, estadísticas, información del modelo y logs. Todo corre en CPU y se levanta con `docker compose`.

**Prueba oficial: 99,38 %** sobre 17 487 imágenes. **Imágenes de internet: 53,7 %** (29 de 54, sin pera ni uva).

---

## 2. Tu parte: diapositivas 14 a 20

### Diapositiva 14 · Monolito por capas

**Qué decir:** «Es un monolito organizado por capas. Cada capa tiene una sola responsabilidad y solo habla con la de abajo.»

```
Rutas (api/v1 y web)  →  Servicios  →  Repositorios  →  Modelos SQLAlchemy  →  PostgreSQL
                             ↓
                ml/predictor + ml/preprocessing (cargados una vez)
```

| Capa | Carpeta | Hace | No hace |
| --- | --- | --- | --- |
| Rutas | `app/api/v1/`, `app/web/` | Validan la entrada HTTP, llaman a un servicio y serializan a JSON | Lógica de negocio ni consultas a la BD |
| Servicios | `app/services/` | Orquestan: validar → decodificar → predecir → guardar → loguear | Consultar la BD directamente |
| Repositorios | `app/repositories/` | Único acceso a la BD, con SQLAlchemy (nunca SQL armado con texto) | Lógica de negocio |
| Modelos | `app/models/` | Definen las tablas `predictions` y `model_versions` | — |
| ML | `app/ml/` | `Predictor` y el preprocesamiento compartido con el entrenamiento | — |
| Núcleo | `app/core/` | Errores de dominio, configuración de logs y lector de logs | — |

**Puntos clave:**
- `create_app()` en `app/__init__.py` es la *application factory*. Configura los logs, conecta la BD y Flask-Migrate, registra los manejadores de error y los blueprints (`api_v1_bp` y `web_bp`) y **carga el modelo una sola vez**. Lo guarda en `app.extensions["predictor"]`.
- Si faltan los artefactos (`model.pt`, `labels.json`, `preprocessing.json`), la app **arranca igual**. El predictor queda en `None`, `/health` informa `"model": "unavailable"` y `POST /predictions` responde **503**.
- La configuración sale de variables de entorno (`app/config.py`, que lee `.env`). No hay credenciales en el código.

**Preguntas probables:**
- *¿Por qué un monolito y no microservicios?* Es un proyecto académico de alcance cerrado. Un solo proceso es más simple de desplegar, probar y explicar, y las capas dan la separación de responsabilidades sin el costo de la red ni de varios despliegues.
- *¿Por qué cargar el modelo una sola vez?* Cargar los pesos en cada petición costaría tiempo y memoria. Se carga al arrancar y lo comparten todas las peticiones.
- *¿Qué ganan con los repositorios?* Las pruebas pueden sustituir el repositorio por uno falso, y si cambia la BD (en las pruebas se usa SQLite) solo cambia esa capa.

### Diapositiva 15 · Una predicción de extremo a extremo

**Qué decir:** recorre los seis pasos con los nombres reales de las funciones.

1. **Ruta** (`app/api/v1/predictions.py::create_prediction`): exige `multipart/form-data`; si no lo es, responde **415**. Lee el campo `image`: si falta o está vacío, responde **422**. Lee `source`, que por defecto es `upload`.
2. **Límite de tamaño:** Flask corta antes con **413** si el cuerpo supera `MAX_CONTENT_LENGTH`, que son 10 MB.
3. **Servicio** (`PredictionService.predict`):
   - valida `source` contra `camera`, `upload` y `video`; si no es ninguno, responde **422 `unsupported_source`**;
   - comprueba que haya modelo; si no, **503**.
4. **Decodificación con Pillow** (`decode_image`): **no confía en la extensión ni en el `Content-Type`**.
   - Abre los bytes y acepta solo `JPEG`, `PNG` y `WEBP`; otro formato, como GIF, da **415**.
   - Llama a `load()`: si el archivo está corrupto, da **422 `invalid_image`**. También captura `DecompressionBombError` (imágenes gigantes hechas para agotar la memoria).
5. **Preprocesamiento e inferencia** (`Predictor.predict`):
   - el mismo `preprocessing.py` del entrenamiento: orientación EXIF, RGB, recorte cuadrado central, 224 × 224 y normalización ImageNet;
   - devuelve `label`, `confidence` y `top3`;
   - el servicio mide `inference_ms` con `time.perf_counter()`, unos 19 ms por imagen en nuestra prueba en CPU.
6. **Persistencia y log:** `prediction_repository.create(...)` guarda la fila; `logger.info` registra id, etiqueta, confianza, fuente, nombre, tamaño y tiempo, **nunca los bytes**. La ruta responde **201** con el JSON de la predicción.

**Preguntas probables:**
- *¿Cómo saben que es una imagen de verdad?* Porque Pillow logra decodificarla. Un `.exe` renombrado a `.jpg` falla en `Image.open` y da 422.
- *¿Dónde se garantiza que el preprocesamiento sea igual en entrenamiento e inferencia?* En `app/ml/preprocessing.py`, el único lugar donde está definido. `train.py`, `evaluate.py` y el `Predictor` lo importan, y los parámetros quedan guardados en `preprocessing.json` junto al modelo.
- *¿Por qué el recorte central?* Las fotos reales son rectangulares; estirarlas a un cuadrado deformaría la fruta. Por eso hay que encuadrarla centrada.

### Diapositiva 16 · Persistencia con trazabilidad

**Tabla `predictions`:**

| Columna | Tipo / regla | Para qué |
| --- | --- | --- |
| `id` | PK | — |
| `source` | texto, **CHECK** en `camera`, `upload`, `video`, con índice | Filtro por fuente |
| `original_filename` | texto opcional | Nombre del archivo, nunca su contenido |
| `file_size_bytes` | entero | Tamaño subido |
| `predicted_label` | texto, con índice | Filtro y estadísticas por etiqueta |
| `confidence` | float, **CHECK** entre 0 y 1 | — |
| `top3` | **JSON** | Las tres clases más probables con su confianza |
| `inference_ms` | float | Tiempo de inferencia |
| `model_version_id` | FK a `model_versions`, `ON DELETE SET NULL`, con índice | Qué artefacto hizo la predicción |
| `created_at` | fecha con zona horaria, **UTC**, con índice | Orden y filtro por fechas |

**Tabla `model_versions`:** `name` (único), `architecture`, `artifact_path`, `labels` (JSON), `is_active`, `created_at`.
- El nombre se construye como `arquitectura-Nclases-mtime`, por ejemplo `mobilenet_v3_small-8cls-<marca de tiempo del model.pt>`. Así, al reentrenar se crea una versión nueva en vez de reutilizar la anterior.
- Se registra **en la primera predicción de cada proceso** (`get_model_version_id`) y queda en memoria.

**Migraciones:** el esquema se maneja con **Flask-Migrate y Alembic**, no con `create_all()`. Hay dos revisiones:
- `6bfedced69da`: esquema inicial.
- `7e4b0e45cdaf`: elimina la tabla `app_logs`, porque los logs pasaron a archivo.

`entrypoint.sh` ejecuta `flask db upgrade` antes de arrancar Gunicorn.

**Consultas del repositorio:**
- **Historial:** filtros por `label` (exacto), `source`, `date_from` (inclusivo) y `date_to` (exclusivo). Orden por `created_at` descendente y luego `id` descendente. Paginación con `page` y `per_page` (máximo 100) que devuelve `items`, `total`, `page`, `per_page` y `pages`.
- **Estadísticas:** las calcula **la BD** con `COUNT`, `AVG(confidence)` y `GROUP BY` por etiqueta y por fuente, no Python recorriendo filas.

**Preguntas probables:**
- *¿Por qué no guardan la imagen?* Por privacidad y tamaño. Basta con los metadatos para el historial y las estadísticas, y el plan no pide almacenar imágenes.
- *¿Por qué `top3` en JSON y no en otra tabla?* Siempre se lee completo junto a la predicción y nunca se consulta por separado. Una tabla aparte solo añadiría un JOIN sin beneficio.
- *¿Para qué sirve `ON DELETE SET NULL`?* Si se borra una versión del modelo, sus predicciones se conservan sin versión en lugar de borrarse en cascada.
- *¿Por qué los logs no van a la BD?* Si la BD falla, justo ahí necesitas los logs. Además, loguear en la BD a través de SQLAlchemy podía generar recursión con los propios logs de SQLAlchemy. Por eso van a consola y a un archivo rotativo: `logs/app.log`, 1 MB, 5 respaldos, en UTC y sin colores ANSI.
- *¿Por qué UTC?* Para evitar ambigüedades de zona horaria; la interfaz convierte a la hora local al mostrar.

### Diapositiva 17 · Siete endpoints y una interfaz

Todos los endpoints viven bajo `/api/v1`; la interfaz web es `GET /` y queda **fuera** de ese prefijo.

| Método | Ruta | Respuesta | Errores típicos |
| --- | --- | --- | --- |
| `POST` | `/predictions` | **201** con la predicción | 413, 415, 422, 503 |
| `GET` | `/predictions` | Página con `items`, `total`, `page`, `per_page` y `pages` | 422 (página, fecha o fuente inválida, o `date_from` > `date_to`) |
| `GET` | `/predictions/{id}` | Detalle | 404 |
| `GET` | `/stats` | `total`, `mean_confidence`, `by_label`, `by_source` | — |
| `GET` | `/model` | Arquitectura, clases, preprocesamiento, entrenamiento y métricas de `metrics.json` | — |
| `GET` | `/logs?limit=N` | Últimas N entradas del log (1 a 500) | 422 |
| `GET` | `/health` | `status`, `database`, `model` | **503** si la BD no responde a `SELECT 1` |

**Sobre de error**, igual en toda la API:

```json
{"error": {"code": "invalid_image", "message": "El archivo no es una imagen válida o está dañado.", "details": null}}
```

**Puntos clave:**
- Recursos en plural, verbos HTTP según la acción, códigos correctos (201 al crear, 422 para entrada inválida, 503 sin modelo).
- Mensajes en español: las descripciones en inglés de Werkzeug se traducen y las propias se conservan.
- El sobre JSON se aplica solo bajo `/api/`. Fuera de ese prefijo, Flask devuelve sus páginas HTML de error.
- Un error inesperado se registra en el log con su traza y el cliente recibe solo «Error interno del servidor.», sin detalles internos.

**Preguntas probables:**
- *¿Por qué 422 y no 400?* 400 es una petición mal formada; 422 es una petición bien formada con datos inválidos, como un `source` desconocido o una imagen corrupta.
- *¿Por qué 415 para un GIF?* Es un tipo de contenido que el servidor no admite.
- *¿Hay autenticación?* No, por alcance: el plan la excluye. En producción haría falta.
- *¿Cómo se versiona la API?* Con el prefijo `/v1`. Un cambio incompatible iría a `/v2` sin romper a los clientes de `/v1`.

### Diapositiva 18 · Cámara, archivo y video

Es una sola página en Jinja (`app/templates/index.html`) con JavaScript sin frameworks (`app/static/js/app.js`). **Solo consume la API** documentada en `docs/api.md`; la ruta `/` no toca servicios ni la BD.

- **Cámara:** usa `getUserMedia` con `facingMode: { ideal: "environment" }`, es decir, la cámara trasera en móviles y la única disponible en portátiles. La captura dibuja el fotograma en un `<canvas>` (hasta 1280 px de ancho, JPEG de calidad 0,9) y lo envía con `source=camera`. Avisa en español si se niega el permiso, si no hay cámara, si está ocupada o si la página no es segura, y ofrece la subida como alternativa.
- **Modo continuo:**
  - envía una predicción cada **1,5 s**;
  - no envía si todavía hay una petición en curso;
  - se detiene al primer error y si cambias de pestaña.
- **Subida:** la validación del navegador (JPEG, PNG o WEBP, máximo 10 MB, no vacío) solo sirve para avisar rápido. **La validación que cuenta es la del servidor con Pillow.**
- **Video:**
  - el navegador toma hasta **8 fotogramas** repartidos en el video (uno por segundo en videos cortos), los reduce a 640 px y los envía uno a uno con `source=video`;
  - **el backend no procesa video**: recibe imágenes sueltas por el mismo endpoint;
  - el resumen promedia la confianza de cada clase sobre todos los fotogramas (cuenta 0 si la clase no aparece en el top-3 de uno de ellos), y el top-3 final sale de esas medias;
  - la nota dice en cuántos fotogramas ganó la clase final.
- **Paneles:**
  - historial paginado con filtros; el filtro de etiqueta es una lista con las 8 clases del modelo porque la API compara la etiqueta exacta;
  - estadísticas con **Chart.js 4.6.1 servido desde `app/static/vendor/`**, sin CDN, con tablas equivalentes para accesibilidad y la paleta Okabe-Ito, apta para daltonismo;
  - información del modelo y últimos logs.
- **Seguridad:** todo el texto que viene de la API se inserta con `textContent`, nunca con `innerHTML`, así que no hay riesgo de inyección de HTML (XSS).

**Preguntas probables:**
- *¿Por qué el video se procesa en el navegador?* Evita subir el archivo entero, no necesita `ffmpeg` en el servidor y reutiliza el endpoint de imagen sin cambios en el backend.
- *¿Cada fotograma se guarda?* Sí: un video genera hasta 8 filas con `source=video`, y aparecen en el historial y en las estadísticas.
- *¿Por qué la cámara no funciona con la IP del equipo?* Los navegadores solo permiten `getUserMedia` en contextos seguros: HTTPS o `localhost`.
- *¿Por qué sin React?* Es una sola vista; JavaScript simple basta y no añade un paso de compilación.

### Diapositiva 19 · Docker: app + PostgreSQL

**`docker-compose.yml`, dos servicios:**
- **`db`:**
  - imagen `postgres:17.6-alpine`, con los datos en el volumen `db_data`;
  - **healthcheck** con `pg_isready` cada 5 s.
- **`app`:**
  - se construye desde el `Dockerfile` y lee el `.env`; puerto 8000;
  - `depends_on: condition: service_healthy`, es decir, espera a que Postgres esté listo y no solo a que el contenedor exista;
  - su propio healthcheck llama a `/api/v1/health`; ambos servicios tienen `restart: unless-stopped`.

**`Dockerfile`:**
- **Versiones fijas:** `python:3.12.11-slim-bookworm` y `uv 0.12.13`. Nunca `latest`.
- **Solo dependencias de ejecución:** `uv sync --locked --no-default-groups` deja fuera `pytest`, `scikit-learn` y `matplotlib`. PyTorch se instala en su variante **solo CPU**.
- **COPY selectivo**, nunca `COPY . .`: `app/`, `migrations/`, `metrics.json`, `wsgi.py`, `entrypoint.sh` y `README.md`. El `.dockerignore` excluye `.env`, `data/raw`, `tests`, `docs` y `logs`. El dataset nunca entra en la imagen.
- **Usuario no root** `appuser` (uid 1000). El código queda en propiedad de root y en solo lectura para la app; solo `logs/` es escribible.
- **Arranque:** `entrypoint.sh` aplica las migraciones y luego Gunicorn sirve con `--workers 1 --threads 4 --timeout 120`.
- **Tamaño:** la imagen pasó de **5,7 GB a 1,72 GB**. Casi todo lo que queda es PyTorch.

**Preguntas probables:**
- *¿Por qué un solo worker?* `RotatingFileHandler` no es seguro con varios procesos escribiendo y rotando el mismo archivo. Además, cada proceso registraría la versión del modelo por su cuenta. Cuatro hilos dan concurrencia suficiente para la demo. Para escalar habría que registrar la versión al arrancar y loguear a `stdout` o con un manejador apto para varios procesos.
- *¿Por qué Gunicorn y no `flask run`?* El servidor de Flask es solo para desarrollo; Gunicorn es un servidor WSGI de producción.
- *¿Dónde están las credenciales?* Solo en `.env`, que no se versiona ni entra en la imagen. El repositorio trae `.env.example` con valores de ejemplo.
- *¿Por qué `uv` y no `pip`?* `uv.lock` fija versiones exactas y `--locked` falla si el lock no coincide con `pyproject.toml`, así que la instalación es reproducible. Además es mucho más rápido.

### Diapositiva 20 · Conclusiones honestas

Explica cada punto en una frase:

1. **99,38 % demuestra que funciona en el entorno controlado**: fondo blanco y rotación controlada. No es una promesa para cualquier foto.
2. **La partición por índice evitó una validación engañosa:** separar los fotogramas al azar habría puesto casi la misma imagen en entrenamiento y validación.
3. **El cambio de criterio de selección pudo influir:** se cambió después de ver el resultado de `Test/`. Para medir la mejora sin sesgo haría falta otro conjunto de prueba independiente.
4. **Con imágenes de internet baja a 53,7 %:** el modelo todavía no generaliza fuera de Fruits-360. Por eso hablamos de cambio de dominio.

**Limitaciones que conviene decir tú antes de que te las pregunten:**
- **Conjunto cerrado:** el modelo siempre elige una de las 8 clases; no puede decir «no es una fruta». Una mejora sería un umbral de confianza que responda «no estoy seguro».
- **Cambio de dominio:** fondos, luz y encuadres reales difieren de Fruits-360.
- **Un solo worker**, sin autenticación, y el modelo no se recarga sin reiniciar la app.

**Trabajo futuro, si preguntan:**
- ajuste fino con fotos reales y aumentos de datos más agresivos (fondos variados);
- umbral de confianza para «desconocido»;
- exportar a ONNX para una imagen más liviana;
- varios workers una vez resuelto lo de los logs y la versión del modelo.

---

## 3. Repaso de las diapositivas 1 a 13

### Datos (diapositivas 3 a 6)

- **Fruits-360**, de Mihai Oltean, versión `2026.10.27.0`, rama 100x100, licencia **CC BY-SA 4.0**.
- Las 94 variedades se agrupan en 8 frutas por el prefijo de la carpeta (`Apple ` → manzana, etc.). El prefijo exige un espacio, así que `Grapefruit` (pomelo) **no** cae en uva.
- Se excluyeron `Orange peeled 1` y `Strawberry Wedge 1` porque son fruta pelada o cortada.

| Clase | Variedades | Entrenamiento | Validación | Prueba oficial |
| --- | ---: | ---: | ---: | ---: |
| banano | 6 | 1 200 | 300 | 719 |
| fresa | 3 | 1 180 | 214 | 479 |
| limón | 2 | 783 | 159 | 330 |
| manzana | 30 | 1 200 | 300 | 5 506 |
| naranja | 5 | 1 200 | 300 | 1 180 |
| pera | 20 | 1 200 | 300 | 4 164 |
| tomate | 19 | 1 200 | 300 | 3 413 |
| uva | 9 | 1 200 | 300 | 1 696 |
| **Total** | **94** | **9 163** | **2 173** | **17 487** |

- **Balance:** como máximo 1 200 imágenes de entrenamiento y 300 de validación por fruta, más `WeightedRandomSampler` con pesos inversos al tamaño de cada clase, que compensa a limón y fresa.
- **Riesgo de fuga:** las imágenes son fotogramas de videos, así que los índices vecinos son casi idénticos. `r_`, `r0_`, `r1_` y `r2_` son variantes de la misma toma.
- **Partición:**
  - por variedad, el último 15 % de los índices va a validación;
  - se descartan los 10 índices anteriores a ese bloque (el hueco);
  - todas las variantes de un mismo índice van juntas;
  - `Test/` se usa solo para la prueba oficial.
- **Verificación de la partición:** una prueba automática revisa el manifiesto versionado (`data/processed/manifest.csv`).

### Modelo (diapositivas 7 a 9)

- **Preprocesamiento:** orientación EXIF → RGB → recorte cuadrado central → 224 × 224 bilineal → normalización ImageNet. En entrenamiento se añaden recorte aleatorio, volteo, rotación de hasta 20° con relleno blanco y variación leve de color.
- *¿Por qué 224 si las imágenes son de 100?* Los pesos de ImageNet se entrenaron con 224 y con su media y desviación estándar. Mantener esa escala aprovecha mejor lo que el modelo ya aprendió.
- **MobileNetV3-Small** con pesos `IMAGENET1K_V1` y la última capa cambiada a 8 salidas. Se eligió por ser ligero (artefacto de 6,2 MB) y rápido en CPU.
- **Dos etapas:**
  - épocas 1 a 3: solo la cabeza, lr 0,001;
  - épocas 4 a 8: los últimos 4 bloques de `features` más la cabeza, lr 0,0001.
  - AdamW, entropía cruzada, lotes de 64 en entrenamiento y 128 en validación, semilla 42.
  - Las capas BatchNorm de los bloques congelados quedan en modo evaluación para no alterar sus estadísticas.
- *¿Por qué dos etapas?* Primero se entrena la cabeza nueva sin dañar las características preentrenadas; después se ajustan los bloques finales con una tasa de aprendizaje baja.
- **Salto de la pérdida en la época 4:** al descongelar, las BatchNorm de esos bloques empiezan a actualizarse. La pérdida de entrenamiento subió de 0,0286 a 0,2231 y bajó a 0,0194 en la época 5.
- **Selección del artefacto:**
  - el primer criterio, mayor exactitud de validación, eligió la época 3 (0,9986 en validación, 0,9915 en la prueba oficial);
  - después se cambió a menor pérdida de validación con la exactitud como desempate, y salió la época 5 (pérdida 0,0096, exactitud 0,9963, **0,9938 en la prueba oficial**);
  - el cambio se hizo después de ver `Test/`, así que la mejora no es una estimación limpia;
  - el criterio de pérdida tiene sentido porque, con la exactitud saturada cerca de 0,99, distingue mejor entre épocas.
- Cada época tardó entre 63 y 143 s en CPU.

### Resultados (diapositivas 10 a 13)

- **Exactitud oficial 99,38 %** sobre 17 487 imágenes. Promedio macro: precisión 0,995, recall 0,997 y F1 0,996.
- *¿Macro o global?* La exactitud global pesa más a la manzana, con 5 506 imágenes. El promedio macro da el mismo peso a cada clase.
- **Por clase:**
  - banano, fresa y limón: 1,000;
  - más bajos: uva con precisión 0,981 (le llegan manzanas y tomates mal clasificados) y pera con recall 0,987 (51 peras clasificadas como manzanas).
- **Confusiones:** 51 peras como manzanas, 27 manzanas como uvas, 9 manzanas como tomates y 5 tomates como uvas. Son frutas redondas o de colores parecidos.
- **Variedades más débiles:** Pear Red 1 (0,811) y Apple 6 (0,879). El promedio alto esconde estos casos.
- **Prueba real (cambio de dominio):** **53,7 %**, 29 de 54 imágenes de internet, en estado `incompleta`.
  - Faltan pera y uva, y 6 archivos `.avif` no se evalúan.
  - Por clase: banano 8/10, fresa 9/10, tomate 5/7, manzana 7/10, limón 0/8 y naranja 0/9.
  - «Pera» funciona como sumidero: recibe 15 de los 25 errores aunque no hay ninguna pera.
  - Los limones de las imágenes son verdes (limas), mientras que el limón de Fruits-360 es amarillo; salen como pera con confianza de 0,99 a 1,00.

---

## 4. Preguntas difíciles (de cualquier parte)

- **«99 % parece demasiado bueno, ¿hay fuga?»** La partición por índice con hueco lo evita, y una prueba lo verifica sobre el manifiesto. `Test/` son videos distintos de los de entrenamiento. El número es alto porque el dominio es fácil: fondo blanco, fruta centrada y sin ruido. Por eso insistimos en la prueba real.
- **«¿Y fuera de Fruits-360?»** Con 54 imágenes de internet baja a **53,7 %**. Dilo sin rodeos: **no son fotos propias**, sino imágenes descargadas, y faltan pera y uva, así que es una muestra pequeña e incompleta.
  - La lección es el cambio de dominio. El modelo aprendió fondo blanco y una sola fruta centrada; con fondos oscuros, varias frutas o limas verdes, falla.
  - **Tampoco avisa cuando falla**: la confianza media es 0,91 en los aciertos y 0,77 en los errores, y algunos errores llegan a 0,99. Un umbral de confianza no basta.
  - Para mejorar: entrenar con fondos variados o con fotos reales.
- **«¿Qué pasa si le muestro un kiwi?»** Devuelve una de las 8 clases, normalmente con menor confianza: es un clasificador de conjunto cerrado. Un umbral de confianza permitiría responder «no estoy seguro».
- **«¿Cómo lo probaron?»** Con 134 pruebas de `pytest`, que cubren el ML (preprocesamiento, partición, predictor, evaluación), la persistencia y las migraciones, los logs, los servicios, cada endpoint con sus errores y la ruta web. También probamos el contenedor con PostgreSQL 17.6: una predicción real guardada, errores en español, 404 en HTML fuera de la API y usuario no root.
- **«¿Qué pasa si se cae la base de datos?»** `/health` devuelve 503 con `"database": "error"`, y los logs siguen escribiéndose en el archivo porque no dependen de la BD.
- **«¿Usan alguna API externa o un modelo en la nube?»** No: el modelo es local, en CPU, y Chart.js también está en el repositorio. Lo único externo son las tipografías de Google Fonts, que son opcionales; si no cargan, se usan las del sistema.
- **«¿Cómo se trabajó en equipo?»**
  - una rama por módulo (`modulo-<n>-<nombre>`) creada desde `ML-project`, con un commit por módulo en formato `tipo(módulo): descripción`;
  - PR y merge hechos por una persona, y documentación actualizada al cerrar cada módulo;
  - módulos: M0 setup, M1 datos y ML, M2 persistencia, M3 logs, M4 servicios, M5 API, M6 Docker, M7 frontend y M8 entrega.
- **«¿Licencias?»** El código es MIT (`LICENSE`, Juan Cardona, Santiago Góez y Sebastián Mejía, 2026). El dataset es CC BY-SA 4.0 y conserva la atribución a Mihai Oltean.

---

## 5. Chuleta de cifras

| Dato | Valor |
| --- | --- |
| Clases / variedades | 8 / 94 |
| Imágenes de entrenamiento / validación / prueba oficial | 9 163 / 2 173 / 17 487 |
| Exactitud oficial | **99,38 %** |
| Promedio macro: precisión / recall / F1 | 0,995 / 0,997 / 0,996 |
| Época elegida | 5 (ajuste fino), pérdida de validación 0,0096, exactitud de validación 0,9963 |
| Primer criterio (época 3) | 0,9915 en la prueba oficial |
| Confusión principal | 51 peras clasificadas como manzanas |
| Entrada del modelo | 224 × 224, normalización ImageNet |
| Artefacto | `model.pt` de 6,2 MB, unos 19 ms por imagen en CPU |
| Tamaño máximo de subida | 10 MB (413) |
| Formatos aceptados | JPEG, PNG, WEBP |
| Modo continuo / video | cada 1,5 s / hasta 8 fotogramas |
| Paginación | `per_page` máximo 100; `limit` de logs de 1 a 500 |
| Logs | `logs/app.log`, 1 MB × 5 respaldos, UTC |
| Imagen Docker | 5,7 GB → 1,72 GB; Gunicorn con 1 worker y 4 hilos |
| PostgreSQL | 17.6-alpine con healthcheck |
| Imágenes de internet | 53,7 % (29 de 54), sin pera ni uva |
| Pruebas | 134 con `uv run pytest` |
