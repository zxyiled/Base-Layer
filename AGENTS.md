# AGENTS.md — Reglas del proyecto para todos los agentes

Proyecto académico: aplicación Flask que clasifica frutas en imágenes (cámara o archivo) con un modelo ajustado por **transfer learning sobre Fruits-360 (100×100)** y guarda cada predicción en PostgreSQL. Stack: Flask + PostgreSQL + PyTorch (CPU) + Docker, con `uv`. Entrega el lunes 23 de noviembre de 2026. Mantén todo **simple**: no es un proyecto empresarial.

**Cómo leer este archivo:** las "Reglas comunes" aplican a todos. Después, aplica **solo la sección de tu rol** (Backend y API, Documentación o Frontend). Si tu herramienta no carga este archivo sola, léelo completo antes de empezar. Para saber qué hay ya hecho, lee `docs/progress.md` y `docs/api.md`.

---

## Reglas comunes

### Alcance cerrado

- Sin autenticación, usuarios ni microservicios. Sin consumir modelos o datos de APIs de terceros.
- Sin funcionalidades fuera del plan aprobado. Si dudas, pregunta.
- No modifiques el `.dockerignore` existente.
- No registres los bytes de las imágenes en logs. Nunca subas datos ni imágenes del dataset a Git.
- **No recorras ni escanees `data/raw/` completo** (decenas de miles de imágenes). Trabaja con carpetas de clase, el manifiesto de `data/processed/` y contadores por carpeta.

### Comandos (siempre con `uv`; nunca `pip` ni `requirements.txt`)

```
uv sync                                       # instalar dependencias
uv add <paquete>                              # agregar dependencia (actualiza pyproject.toml y uv.lock)
uv run flask --app wsgi run --debug           # servidor de desarrollo
uv run pytest                                 # pruebas
uv run python ml_training/prepare_subset.py   # construir el subconjunto y el manifiesto
uv run python ml_training/train.py            # entrenar
uv run python ml_training/evaluate.py         # métricas y gráficas
docker compose up -d --build                  # levantar app y base de datos
```

### Arquitectura: monolito por capas

```
routes (api / web)  →  services  →  repositories  →  models (SQLAlchemy)
                          ↓
              ml/predictor + ml/preprocessing (modelo local, cargado una vez al arrancar)
```

- **Rutas**: solo validan la entrada, llaman a un servicio y serializan la respuesta. Sin lógica de negocio.
- **Services**: orquestan (validar → decodificar imagen → preprocesar → predecir → guardar → loguear). No consultan la BD directamente.
- **Repositories**: los únicos que acceden a la base de datos, con SQLAlchemy (nunca SQL armado con strings).
- **ML**: el modelo se carga una vez en `create_app()`. El preprocesamiento vive en un único lugar (`app/ml/preprocessing.py`) y se usa igual en entrenamiento e inferencia.
- **Configuración**: variables de entorno leídas en `config.py` (desde `.env`). Ninguna credencial en el código. Logs con `logging`, nunca `print`.

### Convenciones

- Código e identificadores en inglés; textos de la interfaz, documentación y descripción de commits en español.
- Type hints en funciones públicas. Funciones cortas, con una sola responsabilidad.
- **API REST** (prefijo `/api/v1`): recursos como sustantivos en plural y kebab-case; métodos HTTP según la acción; códigos correctos (`200`, `201`, `400`, `404`, `413` archivo demasiado grande, `415` tipo no soportado, `422` entrada inválida, `500`); listas paginadas con `page` y `per_page` y metadatos de paginación; filtros por parámetros de consulta; errores siempre con el formato `{"error": {"code": ..., "message": ..., "details": ...}}`.
- Subidas de imagen: valida el tipo **decodificando con Pillow** (no confíes en la extensión ni en el `Content-Type`), limita el tamaño (`MAX_CONTENT_LENGTH`) y rechaza archivos corruptos.

### ML (Fruits-360)

- Tarea: clasificación de imágenes con transfer learning (pesos pre-entrenados + fine-tuning en dos etapas: cabeza y últimos bloques). Entre 5 y 10 **frutas** (variedades agrupadas por fruta), según el plan aprobado.
- Dataset local en `data/raw/fruits-360/` (o la ruta de la variable `DATASET_DIR`). El subconjunto se describe en un manifiesto pequeño en `data/processed/`.
- **Riesgo de fugas:** las imágenes son fotogramas casi idénticos de videos cortos. No mezcles fotogramas vecinos entre entrenamiento y validación; usa la partición definida en el plan.
- **Cambio de dominio:** se evalúa también con fotos propias en `data/real_test/<clase>/`. Reporta por separado la prueba oficial y la prueba real, y explica la diferencia.
- Semillas fijas. Clases balanceadas por muestreo. Métricas: accuracy, precisión, recall y F1 por clase, matriz de confusión y curvas de pérdida y precisión, con interpretación honesta.
- El artefacto va en `app/ml/artifacts/` con `labels.json` y los parámetros de preprocesamiento.

### Git y versionado

- **Rama base de integración: `ML-projects`** (debe mantenerse estable: con pruebas pasando). **Una rama por módulo**, creada desde la rama base (`git switch -c modulo-<n>-<nombre>`). Un commit por módulo cerrado. Al cerrar, una persona fusiona el módulo en `ML-projects` (`git merge --no-ff`) y el resto actualiza su rama desde ahí. Antes de la entrega, la rama que se entrega (la predeterminada del repositorio remoto) debe contener todo el trabajo.
- **Los agentes no hacen `git push` ni mergean a `ML-projects`**: lo hace una persona al cerrar el módulo.
- Mensaje: `<tipo>(<módulo>): descripción en español`. Tipos: `feat`, `fix`, `docs`, `test`, `build`, `chore`. Ejemplo: `feat(ml): entrenamiento y evaluación del clasificador`.
- Agrega archivos **por ruta explícita**; nunca `git add -A` ni `git add .`. Antes de commitear, revisa `git status` y confirma que no entran `.env`, `data/raw/`, `logs/`, `uploads/`, caches ni carpetas de herramientas.
- **Se versiona solo lo necesario:** código (`app/`, `ml_training/`, `tests/`), `docs/`, `README.md`, `pyproject.toml`, `uv.lock`, `.python-version`, `pytest.ini`, archivos de Docker, `.env.example`, `.dockerignore`, `data/processed/`, `data/real_test/`, el artefacto del modelo, `AGENTS.md` y `CLAUDE.md`.
- **No se versiona** (lo cubre `.gitignore`): `.env`, `.venv/`, `data/raw/`, `logs/`, `uploads/`, caches, checkpoints, zips, bases de datos locales, archivos de editor y `.agents/`, `.claude/`, `.codex/` (configuración local de herramientas).
- **No se usan `.gitkeep`.** Las carpetas que solo contienen archivos ignorados o generados (`data/raw/`, `logs/`, `uploads/`) no se versionan y se documentan en el README. El código crea las carpetas de salida que necesita (`logs/`, `app/ml/artifacts/`, `ml_training/reports/`, `data/processed/`) con `mkdir(parents=True, exist_ok=True)`; no dependas de que existan.
- Si cambias dependencias (`uv add`), commitea `pyproject.toml` y `uv.lock` juntos. Tras un merge con cambios de dependencias, regenera con `uv lock`.

### Docker

- El `Dockerfile` usa **`COPY` selectivo** (`app/`, `wsgi.py`, `pyproject.toml`, `uv.lock`, `entrypoint.sh`, `README.md` y el artefacto del modelo), **no `COPY . .`**: el contexto de build es la carpeta local, que puede contener carpetas de herramientas y datos.
- Imágenes con versión fija (nada de `latest`). PyTorch solo en su variante de CPU, u ONNX Runtime si el plan lo decide. El dataset nunca entra en la imagen.

### Módulos y trabajo en paralelo

Orden y dependencias: **M0** setup → **M1** datos y ML, **M2** persistencia y **M3** logs (independientes entre sí) → **M4** servicios e inferencia (necesita M1, M2 y M3) → **M5** API (necesita M4) → **M6** Docker (necesita M2; puede avanzar antes) → **M7** frontend (necesita el contrato de M5) → **M8** README, docs finales y diapositivas.

- Cada persona o agente **cierra su módulo antes de empezar otro**. Módulos independientes pueden hacerse en paralelo por personas distintas, cada uno en su rama.
- No edites carpetas de otro rol sin avisar. Archivos compartidos (`pyproject.toml`, `uv.lock`, `app/__init__.py`, `config.py`): cambios mínimos y avisa.
- **Puerta de cierre** (todos los roles): (1) las pruebas del módulo pasan con `uv run pytest` y la app arranca; (2) la documentación del módulo queda actualizada (ver "Rol: Documentación"); (3) revisión de `git status` y un commit en la rama del módulo; (4) una persona hace el push y el merge.

---

## Rol: Backend y API (cualquier agente de código)

Carpetas: **Backend** = `app/models`, `app/repositories`, `app/services`, `app/ml`, `app/core`, `ml_training`, `scripts`, Docker. **API** = `app/api/v1` y sus schemas.

Cómo trabajar:

1. Lee `docs/progress.md`, `docs/architecture.md` y `docs/api.md` antes de tocar código, y trabaja solo en tu módulo.
2. No inventes: antes de usar una librería o función, verifica que existe en la versión instalada (`uv run python -c "..."`, o el código fuente en `.venv`) y que `pyproject.toml` la incluye.
3. Cambios mínimos y legibles; no reescribas archivos enteros sin necesidad. Escribe pruebas junto con el código.
4. Ejecuta `uv run pytest` y arranca la app antes de dar un módulo por terminado.
5. Al terminar, reporta: qué hiciste, qué archivos tocaste, cómo lo verificaste y qué queda pendiente.
6. **Documentación del módulo:** si el entorno tiene el plugin de Codex, delégala con `Cierre del módulo <N>: actualiza docs/ según AGENTS.md. No uses git.` y revisa que solo cambien `docs/` y `README.md`. Si no tienes el plugin, actualiza tú los archivos de `docs/` de tu módulo siguiendo el rol de documentación.
7. Haz el commit tú, en la rama del módulo, siguiendo "Git y versionado".

---

## Rol: Documentación (Codex u otro agente)

Eres el agente de **documentación**. No modificas el código de la aplicación y **no usas git** (el sandbox de Codex no escribe en `.git`; los commits los hace el agente de backend/API). Te invocan al cerrar un módulo.

1. **Lee el estado real**: el código, los tests y los reportes (por ejemplo `ml_training/reports/`). El código y los tests son la fuente de verdad, no el plan. No necesitas ejecutar la app ni las pruebas: quien te invoca te dice el resultado. Si falta información, escríbelo como "pendiente" y avísalo.
2. **Actualiza solo `docs/` y `README.md`:**
   - `docs/architecture.md`: capas, componentes, flujo de una predicción de extremo a extremo, estructura de carpetas.
   - `docs/dataset.md`: Fruits-360 (autor Mihai Oltean, licencia), clases elegidas y agrupación por fruta, particiones, riesgo de fugas, prueba oficial frente a prueba real, preprocesamiento y justificación.
   - `docs/ml-report.md`: modelo y estrategia de transfer learning (etapas), hiperparámetros, métricas por clase, matriz de confusión, curvas, interpretación y limitaciones.
   - `docs/api.md`: contrato de cada endpoint (ruta, método, entrada, salida, errores). Es el contrato del frontend: debe coincidir con la API real.
   - `docs/deployment.md`: variables de `.env`, `docker compose`, migraciones, cómo levantar y verificar, y la nota de que la cámara requiere `localhost` o HTTPS.
   - `docs/progress.md`: estado y responsable de cada módulo (pendiente, en curso, cerrado), rama, y "Diferencias con el plan".
   - `README.md`: instalación paso a paso (con `uv sync`, crear el `.env` desde `.env.example`, descargar Fruits-360 y colocarlo en `data/raw/fruits-360/` (carpeta que no se versiona y se crea a mano), preparar el subconjunto, `docker compose`; indica también que `logs/` se crea sola).
3. **Documenta solo lo que existe.** No inventes endpoints, tablas ni métricas.
4. Límites: no toques `app/`, `ml_training/`, `scripts/`, `migrations/`, `tests/`, archivos de Docker, `pyproject.toml` ni `.env*`. Si encuentras un error en el código, repórtalo; no lo arregles. No ejecutes comandos de git. No recorras `data/raw/`. Estilo: español, breve, con tablas para endpoints, variables y métricas.

---

## Rol: Frontend y diapositivas (módulos 7 y 8)

- Usa las skills `ui-ux-pro-max` (interfaz) y `frontend-slides` (diapositivas), en `.agents/skills/` si existen en tu entorno. **Antes de usarlas**, verifica que existan su `SKILL.md` y todos los archivos que referencian. Si falta alguno, **avisa cuál y detente**. Si tu herramienta no carga skills, lee el `SKILL.md` y sigue sus instrucciones.
- Interfaz en Jinja + Chart.js, servida por Flask. Consume la API **solo** según `docs/api.md`; no cambies el backend (si necesitas un cambio, pídelo).
- Entrypoint `/`: vista previa de la cámara (`getUserMedia`), botón de captura, alternativa de subir archivo, resultado (etiqueta, barra de confianza, top-3), historial, estadísticas, información del modelo y logs. Contempla permiso de cámara denegado o sin cámara. La cámara solo funciona en `localhost` o con HTTPS.
- Textos de la interfaz en español. Las diapositivas se guardan en `docs/presentacion/`.